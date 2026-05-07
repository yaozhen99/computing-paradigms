# 项目需求：StateKanban 第三轮 — 引擎调校 + 端到端验证

## 项目概述

前两轮完成了内核（3987行）和驱动引擎（+1553行），369项测试全部通过。但驱动循环从未真正跑通过——MockLLMAdapter 的返回格式与 ResponseParser 不对齐，真实 API 未验证。本轮目标：**让引擎真正能跑通一个完整任务，从意图注入到文件产出。**

## 当前状态

### MockLLMAdapter（`05_delivery/statekanban/adapters/mock_adapter.py`）

- `__init__(responses: dict[str, list[LLMResponse]] | None = None)`
- `set_response(role, responses: list[LLMResponse])` — 设置某角色的响应列表
- `complete()` — 循环取 `_responses[role]`，找不到角色时遍历任意有配置的角色
- **角色推断**：`_infer_role()` 方法存在，但实现是从 `messages` 中找 `"Role:"` 前缀。Engine 在 `_call_llm_for_role()` 中构建的上下文确实以 `"Role: {role}\n"` 开头，所以推断逻辑本身可用
- **无 structured_mode**：没有 `set_structured_response()`，没有 `structured_mode` 属性
- **无行为配置**：没有 always_approve / reject_then_approve 等预设行为

### ResponseParser（`05_delivery/statekanban/engine/response_parser.py`）

- `parse(raw_response: LLMResponse, author_role: str, round_number: int) -> list[ParsedResponse]`
- 三策略：structured JSON → fenced code block → error
- structured JSON 策略：对 `raw_response.content` 做 `json.loads()`，期望 `{"type": "intent"|"veto"|"artifact", "target_id": "...", ...}`
- ParsedResponseType: INTENT / VETO / ARTIFACT / ERROR

### Engine（`05_delivery/statekanban/engine/engine.py`）

- `drive(intent_text: str) -> DriveResult` — 主驱动循环
- `_seed_intent(intent_text)` — 注入初始 IntentSignal 到 FluidZone
- `_call_llm_for_role(role, slice_data)` — 构建上下文 `"Role: {role}\nSignals ({N}):\n  - [{type}] {author} -> {target}: ..."`，然后调 `self._adapter.complete()`
- `_process_role(role, round_number)` — 调 `_call_llm_for_role()` → `ResponseParser.parse()` → 将 ParsedResponse 转为 Signal/Artifact 注入 FluidZone/CrystalZone
- `_crystalize_and_write()` — 从 CrystalZone 取 artifact，通过 OutputValve 写文件
- **R2-CON-001**：`_call_llm_for_role()` 第267行直接调 `self._adapter.complete()`，绕过 ToolRegistry

### ConvergenceDetector（`05_delivery/statekanban/engine/convergence.py`）

- `check(current_round)` — 收敛条件：`intent_count > 0 and veto_count == 0`（同一轮内）
- `check_all_pending(current_round)` — 检查当前轮所有 target 是否收敛

### DriveResult（`05_delivery/statekanban/engine/result.py`）

- 字段：`converged: bool`, `forced_terminate: bool`, `total_rounds: int`, `artifact_files: list[str]`, `error: str | None`

### 错误码现状（`05_delivery/statekanban/core/errors.py`）

- 32 个错误码：SK_FZ_001~003, SK_CZ_001~002, SK_AZ_001, SK_VS_001~002, SK_OV_001~005, SK_TR_001~003, SK_PM_001~004, SK_MB_001~002, SK_LLM_001~003, SK_SN_001~002, SK_CX_001~002, SK_EN_001~003
- **缺失**：SK_CX_003（Codex timeout）、SK_EN_004（Valve rework loop）、SK_TR_004（null bytes in prompt）
- SnapshotIntegrityError（SK_SN_001）和 SnapshotWriteError（SK_SN_002）已存在

### snapshot.py

- **不存在**。`05_delivery/statekanban/snapshot.py` 不在代码库中
- **阻断性缺陷**：CLI（`cli/main.py`）第32行已 `from statekanban.snapshot import load_snapshot, save_snapshot`，引用了不存在的模块，导致 CLI 无法启动
- StateKanban 有 `to_json()` / `from_json()` 方法（含 SHA-256 checksum 校验）

### 现有测试

- 369 项测试全部通过，80% 覆盖率
- 无端到端测试（test_e2e.py 不存在）
- 无真实 API 测试

---

## 需求条目

### REQ-001：MockLLMAdapter 新增 structured_mode

**现在**：MockLLMAdapter 只有 legacy 模式（`set_response(role, [LLMResponse(...)])`），`complete()` 返回的 `LLMResponse.content` 是普通字符串，ResponseParser 走 fenced code block 策略而非 structured JSON 策略。

**改成**：新增 `set_structured_response()` 方法和 `structured_mode` 属性。调用 `set_structured_response()` 后，`complete()` 返回的 `LLMResponse.content` 是 JSON 字符串，ResponseParser 可走 structured JSON 策略直接解析。

**接口**：
```python
def set_structured_response(
    self,
    role: str,
    response_type: ParsedResponseType,
    target_id: str = "task_root",
    payload: dict[str, Any] | None = None,
    reason: str = "",           # veto 时必填
    artifact_path: str = "",    # artifact 时必填
    artifact_content: str = "", # artifact 时必填
) -> None:
    """配置某角色的结构化 JSON 响应。调用后自动启用 structured_mode。"""

@property
def structured_mode(self) -> bool:
    """是否启用结构化 JSON 模式。"""
```

**structured_mode 下的返回逻辑**：
1. 按 role 查 `_structured_responses[role]`，循环取（与 legacy 模式一致）
2. 找不到该 role 时，遍历任意有配置的 role
3. 都没有时，返回 `LLMResponse(content='{"type": "intent", "target_id": "task_root", "payload": {}}', finish_reason="end_turn")`

**向后兼容**：不调用 `set_structured_response()` 时，行为与当前完全一致。现有 369 项测试必须仍通过。

### REQ-002：MockLLMAdapter 新增行为模式

**现在**：测试需要手动为每个角色配置响应，无法快速模拟"审批通过"、"否决后通过"等常见场景。

**改成**：新增 `set_behavior_mode()` 方法和两个行为枚举，让测试可以一键配置预设行为。

**接口**：
```python
class MockReviewerBehavior(Enum):
    ALWAYS_APPROVE = "always_approve"
    ALWAYS_REJECT = "always_reject"
    REJECT_THEN_APPROVE = "reject_then_approve"

class MockCoderBehavior(Enum):
    GENERATE_SIMPLE = "generate_simple"
    GENERATE_WITH_BUG = "generate_with_bug"

def set_behavior_mode(
    self,
    reviewer_behavior: MockReviewerBehavior = MockReviewerBehavior.ALWAYS_APPROVE,
    coder_behavior: MockCoderBehavior = MockCoderBehavior.GENERATE_SIMPLE,
) -> None:
    """启用行为模式。自动启用 structured_mode。"""
```

**行为模式下各角色返回的 JSON**：

| 角色 | 行为 | 返回 |
|------|------|------|
| coder | GENERATE_SIMPLE | `{"type": "artifact", "target_id": "task_root", "payload": {"action": "generate_code"}, "artifact_path": "output.py", "artifact_content": "def hello():\n    return \"hello world\"\n", "artifact_type": "code"}` |
| coder | GENERATE_WITH_BUG | 同上，但 `artifact_content` 为 `"def hello():\n    return undefined_var\n"` |
| reviewer | ALWAYS_APPROVE | `{"type": "intent", "target_id": "task_root", "payload": {"action": "approve", "reason": "Code meets requirements"}}` |
| reviewer | ALWAYS_REJECT | `{"type": "veto", "target_id": "task_root", "reason": "Code does not meet quality standards"}` |
| reviewer | REJECT_THEN_APPROVE | 第1次调用返回 veto（reason: "Missing type annotations"），第2次起返回 intent approve |
| tester | — | `{"type": "intent", "target_id": "task_root", "payload": {"action": "test_passed", "coverage": "100%"}}` |
| integrator | — | `{"type": "intent", "target_id": "task_root", "payload": {"action": "integrate", "files": ["output.py"]}}` |

**REJECT_THEN_APPROVE 的判断方式**：用 `_call_counts["reviewer"]` 判断，0 时返回 veto，>=1 时返回 approve。

**行为模式优先级**：`behavior_mode > structured_mode > legacy_mode`。

### REQ-003：新建 snapshot 模块

**现在**：`05_delivery/statekanban/snapshot.py` 不存在。StateKanban 有 `to_json()` / `from_json()` 方法，但无独立的快照存取模块。

**改成**：新建 `snapshot.py`，提供 `save_snapshot()` 和 `load_snapshot()` 两个函数。

**接口**：
```python
def save_snapshot(kanban: StateKanban, path: str) -> None:
    """序列化 StateKanban 为 JSON，原子写入文件。
    用 tempfile.mkstemp + os.replace 实现原子写。
    失败时抛 SnapshotWriteError（SK_SN_002）。
    """

def load_snapshot(path: str) -> StateKanban:
    """从文件加载快照。
    内部调 StateKanban.from_json()，含 SHA-256 校验。
    文件不存在抛 FileNotFoundError。
    JSON 无效或校验失败抛 SnapshotIntegrityError（SK_SN_001）。
    """
```

**依赖**：`core/errors.py` 中 `SnapshotIntegrityError`（SK_SN_001）和 `SnapshotWriteError`（SK_SN_002）已存在，可直接使用。

### REQ-004：端到端测试套件

**现在**：无端到端测试。所有测试都是单元级，MockLLMAdapter 未与 Engine 集成测试。

**改成**：新建 `04_testing/test_scripts/test_e2e.py`，包含以下测试用例：

**TC-E2E-001：Mock LLM 完整流程**
- 构建完整系统（kanban + bus + registry + valve + slicer + pm + adapter + engine）
- adapter 设置 `ALWAYS_APPROVE + GENERATE_SIMPLE`
- `engine.drive("实现 hello world 函数")`
- 断言：`result.converged is True`，`result.total_rounds >= 1`，CrystalZone 有 artifact

**TC-E2E-002：碰撞收敛**
- adapter 设置 `REJECT_THEN_APPROVE + GENERATE_SIMPLE`
- `engine.drive("实现带类型注解的函数")`
- 断言：`result.converged is True`，`result.total_rounds == 2`
- 断言：FluidZone 有至少 1 个 VetoSignal

**TC-E2E-003：拦截率**
- adapter 设置 `ALWAYS_REJECT + GENERATE_WITH_BUG`
- `engine.drive("实现安全函数")`，max_rounds=3
- 断言：`result.converged is False`，`result.forced_terminate is True`
- 断言：CrystalZone 无 artifact（有问题的代码没有混入）

**TC-E2E-004：快照恢复**
- 跑完 drive 后 `save_snapshot(kanban, path)`
- `load_snapshot(path)` 恢复
- 断言：恢复后的 FluidZone 信号数和 CrystalZone artifact 数与原始一致

**测试辅助**：需要一个 `_make_system()` 工厂函数，构建完整系统实例。参考现有 `conftest.py` 中的 fixture，但需要额外配置 ViewportSpec（coder/reviewer/tester/integrator 四个角色）。

### REQ-005：修复 R2-CON-001（Engine 绕过 ToolRegistry）

**现在**：`engine/engine.py` 的 `_call_llm_for_role()` 直接调 `self._adapter.complete()`，审计链断裂。ToolRegistry 注册了 `call_llm` 工具但 Engine 不走它。

**改成**：`_call_llm_for_role()` 改为调 `self._registry.dispatch("call_llm", ...)`，从 dispatch 结果中提取 `LLMResponse`。

**前置条件**：当前 ToolRegistry 中仅注册了 `read_file` 和 `call_codex`，**无 `call_llm` 工具**。必须先创建 `tools/call_llm.py` 并注册到 ToolRegistry（见 REQ-005a），REQ-005 才可实施。

**具体改动**（`engine/engine.py`）：
- 将 `_call_llm_for_role()` 中构建上下文和调 adapter 的逻辑拆分
- 上下文构建提取为 `_build_context(role, slice_data) -> str` 方法
- `_call_llm_for_role()` 改为：
  ```python
  result = await self._registry.dispatch(
      "call_llm",
      role=role,
      messages=[{"role": m.role, "content": m.content} for m in messages],
      max_tokens=self._config.llm_max_tokens,
      temperature=self._config.llm_temperature,
  )
  if not result.success:
      raise LLMResponseParseError(f"call_llm failed: {result.error}")
  output = result.output
  return LLMResponse(
      content=output.get("content"),
      finish_reason=output.get("finish_reason", "end_turn"),
  )
  ```

**注意**：需确认 `ToolRegistry.dispatch()` 的返回格式和 `call_llm` 工具的注册方式，确保参数传递正确。

### REQ-005a：新建 tools/call_llm.py（REQ-005 前置条件）

**现在**：`05_delivery/statekanban/tools/` 下只有 `read_file.py` 和 `call_codex.py`，无 `call_llm.py`。ToolRegistry 中未注册 `call_llm` 工具，REQ-005 的 `registry.dispatch("call_llm", ...)` 调用会失败。

**改成**：新建 `tools/call_llm.py`，封装 LLM adapter 的 `complete()` 调用，并注册到 ToolRegistry。

**接口**：
```python
# tools/call_llx.py
async def call_llm(
    role: str,
    messages: list[dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """调用 LLM adapter.complete()，返回结构化结果。

    Returns:
        {"success": True, "output": {"content": ..., "finish_reason": ...}}
        或 {"success": False, "error": "...", "error_code": "SK_LLM_001"}
    """
```

**注册方式**：参照 `call_codex.py` 的注册模式，在 `tools/__init__.py` 中将 `call_llm` 注册到 ToolRegistry。

**依赖**：需从 Engine 注入 adapter 实例，或在 ToolRegistry 初始化时传入。具体注入方式由开发阶段决定，但必须保证 `call_llm` 能访问到 `LLMAdapter.complete()`。

### REQ-006：新增 SK_CX_003（Codex timeout 错误码）

**现在**：`core/errors.py` 有 `CodexExecutionError`（SK_CX_001）和 `CodexAdapterError`（SK_CX_002），无 timeout 专用错误码。Codex 超时时抛 `CodexExecutionError`，无法区分超时和其他执行错误。

**改成**：新增 `CodexTimeoutError(CodexAdapterError)`，`error_code="SK_CX_003"`，`http_analogy=408`。`CodexAdapter.complete()` 超时时抛此异常。

### REQ-007：新增 SK_EN_004（Valve rework loop 错误码）

**现在**：`core/errors.py` 有 `EngineError`（SK_EN_001）、`ConvergenceError`（SK_EN_002）、`LLMResponseParseError`（SK_EN_003），无 valve rework loop 错误码。

**改成**：新增 `ValveReworkLoopError(EngineError)`，`error_code="SK_EN_004"`，`http_analogy=500`。Engine 在 `_crystalize_and_write()` 中检测连续 valve 失败时抛此异常。

### REQ-008：CodexAdapter null bytes 校验（R2-SEC-001）

**现在**：`adapters/codex_adapter.py` 和 `tools/call_codex.py` 未校验 prompt 中的 null bytes（`"\x00"`）。

**改成**：
- `tools/call_codex.py` 入口加：`if "\x00" in prompt: return {"success": False, "error": "Null bytes detected in prompt", "error_code": "SK_TR_004"}`
- `adapters/codex_adapter.py` 的 `complete()` 入口加同样校验

---

## 技术约束

1. **不改核心模块接口**：kanban / message_bus / viewport / valve / registry / process 的公开方法签名不变
2. **向后兼容**：MockLLMAdapter 默认行为不变时，现有 369 项测试必须全部通过
3. **底座零 I/O 原则**：核心模块不做文件 I/O，snapshot.py 是应用层模块
4. **新增文件遵循现有目录结构**：snapshot.py 放 `05_delivery/statekanban/snapshot.py`，test_e2e.py 放 `04_testing/test_scripts/test_e2e.py`
5. **真实 API 测试**：用 `@pytest.mark.live_api` 标记，默认跳过，需 `--run-live` 才执行（本轮不强制要求真实 API 验证，但测试框架要预留）
6. **迭代轮次 lock 文件**：R3 重置 lock 文件时，必须增加 `"round": 3` 字段，以便区分不同轮次的 pending/completed 状态

## 验收标准

1. `python -m pytest 04_testing/test_scripts/ -q` — 全部通过（现有 369 + 新增端到端测试）
2. `python -c "from statekanban.adapters.mock_adapter import MockLLMAdapter, MockReviewerBehavior, MockCoderBehavior; m = MockLLMAdapter(); m.set_behavior_mode(MockReviewerBehavior.REJECT_THEN_APPROVE); print('OK')"` — 行为模式可导入可配置
3. `python -c "from statekanban.snapshot import save_snapshot, load_snapshot; print('OK')"` — snapshot 模块可导入
4. `python -c "from statekanban.core.errors import CodexTimeoutError, ValveReworkLoopError; print(CodexTimeoutError.error_code, ValveReworkLoopError.error_code)"` — 新错误码可导入
5. Engine 的 `_call_llm_for_role()` 不再直接调 `self._adapter.complete()`，改为走 `self._registry.dispatch("call_llm", ...)`

## 交付物清单

| # | 文件 | 操作 |
|---|------|------|
| 1 | `05_delivery/statekanban/adapters/mock_adapter.py` | 修改：新增 structured_mode + behavior_mode |
| 2 | `05_delivery/statekanban/snapshot.py` | 新增：save_snapshot / load_snapshot |
| 3 | `04_testing/test_scripts/test_e2e.py` | 新增：4 个端到端测试用例 |
| 4 | `05_delivery/statekanban/tools/call_llm.py` | 新增：call_llm 工具（REQ-005a） |
| 5 | `05_delivery/statekanban/engine/engine.py` | 修改：REQ-005（_call_llm_for_role 改走 registry） |
| 6 | `05_delivery/statekanban/core/errors.py` | 修改：新增 SK_CX_003 + SK_EN_004 + SK_TR_004 |
| 7 | `05_delivery/statekanban/adapters/codex_adapter.py` | 修改：null bytes 校验 |
| 8 | `05_delivery/statekanban/tools/call_codex.py` | 修改：null bytes 校验 |
