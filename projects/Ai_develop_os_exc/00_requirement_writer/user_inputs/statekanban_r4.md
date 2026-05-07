# 项目需求：StateKanban 第四轮 — R3 遗留修正 + 真实 API 验证

## 项目概述

R3 完成了引擎调校和端到端测试（381 项测试通过），但 Reviewer 审核发现 2 项需求吻合度偏差。本轮目标：**修正 R3 遗留的接口偏差，补强端到端测试的真实驱动路径，并验证真实 API 可用性。**

## 当前状态

### MockLLMAdapter（`05_delivery/statekanban/adapters/mock_adapter.py`）

- `set_behavior_mode(mode: MockReviewerBehavior | MockCoderBehavior)` — **单参数签名**
- 需求要求：`set_behavior_mode(reviewer_behavior=..., coder_behavior=...)` — **双参数签名**
- 当前实现无法一次调用同时配置 reviewer + coder 行为
- tester / integrator 角色无预设行为配置
- behavior_mode 下 coder 返回的 `artifact_content` 为 `"# simple code\npass"`，需求要求为 `"def hello():\n    return \"hello world\"\n"`

### test_e2e.py（`04_testing/test_scripts/test_e2e.py`）

- TC-E2E-02/03 使用手动构造信号 + `kanban.run_convergence()` 测试收敛
- 需求要求：通过 `Engine.drive()` + `behavior_mode` 驱动完整流程
- TC-E2E-01 只设了 `MockCoderBehavior.GENERATE_SIMPLE`，未同时设 reviewer 行为（受 REQ-002 单参数限制）

### Engine（`05_delivery/statekanban/engine/engine.py`）

- `_call_llm_for_role()` 已改走 `registry.dispatch("call_llm", ...)`（R3 REQ-005 完成）
- 新增 `set_use_registry_for_llm()` 回退开关（R3 未要求，但合理，保留）

### 真实 API

- 无真实 API 测试（`@pytest.mark.live_api` 标记已预留但无实际用例）
- Anthropic API 调用路径未验证

---

## 需求条目

### REQ-001：修正 set_behavior_mode 签名为双参数

**现在**：`set_behavior_mode(mode: MockReviewerBehavior | MockCoderBehavior)` 只接受单个枚举值，无法同时配置 reviewer 和 coder 行为。

**改成**：改为双参数签名，与 R3 需求文档一致。

**接口**：
```python
def set_behavior_mode(
    self,
    reviewer_behavior: MockReviewerBehavior = MockReviewerBehavior.ALWAYS_APPROVE,
    coder_behavior: MockCoderBehavior = MockCoderBehavior.GENERATE_SIMPLE,
) -> None:
    """启用行为模式。自动启用 structured_mode。同时配置 reviewer 和 coder 行为。"""
```

**行为配置逻辑**：
1. 根据 `reviewer_behavior` 配置 reviewer 角色的 structured_response
2. 根据 `coder_behavior` 配置 coder 角色的 structured_response
3. 自动配置 tester 角色：`{"type": "intent", "target_id": "task_root", "payload": {"action": "test_passed", "coverage": "100%"}}`
4. 自动配置 integrator 角色：`{"type": "intent", "target_id": "task_root", "payload": {"action": "integrate", "files": ["output.py"]}}`

**向后兼容**：现有调用 `set_behavior_mode(MockReviewerBehavior.ALWAYS_APPROVE)` 会因签名变更报错。需同步修改所有调用点（test_e2e.py、test_mock_adapter.py 等）。

**artifact_content 精确值**：
- GENERATE_SIMPLE：`"def hello():\n    return \"hello world\"\n"`（不是 `"# simple code\npass"`）
- GENERATE_WITH_BUG：`"def hello():\n    return undefined_var\n"`（不是 `"# buggy code\nimport os; os.remove('/')"`）

### REQ-002：修正 E2E 测试用例为 Engine.drive() 驱动

**现在**：TC-E2E-02/03 使用手动构造信号测试收敛，未走 Engine.drive() 完整流程。

**改成**：改为通过 Engine.drive() + behavior_mode 驱动，验证完整驱动循环。

**TC-E2E-002：碰撞收敛（重写）**
- 构建完整系统（`_make_system()` 工厂函数）
- adapter 设置 `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE, coder_behavior=MockCoderBehavior.GENERATE_SIMPLE)`
- `result = await engine.drive("实现带类型注解的函数")`
- 断言：`result.converged is True`
- 断言：FluidZone 有至少 1 个 VetoSignal

**TC-E2E-003：拦截率（重写）**
- 构建完整系统
- adapter 设置 `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT, coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG)`
- `result = await engine.drive("实现安全函数")`，max_rounds=3
- 断言：`result.converged is False`，`result.forced_terminate is True`
- 断言：CrystalZone 无 artifact

**TC-E2E-001 也需修正**：当前只设了 `MockCoderBehavior.GENERATE_SIMPLE`，需改为双参数调用：
```python
adapter.set_behavior_mode(
    reviewer_behavior=MockReviewerBehavior.ALWAYS_APPROVE,
    coder_behavior=MockCoderBehavior.GENERATE_SIMPLE,
)
```

### REQ-003：新增真实 API 烟雾测试

**现在**：无真实 API 测试。`@pytest.mark.live_api` 标记已预留但无实际用例。

**改成**：新增 `04_testing/test_scripts/test_live_api.py`，包含 1 个烟雾测试。

**TC-LIVE-001：Anthropic API 烟雾测试**
```python
@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_anthropic_smoke():
    """验证 Anthropic API 可达且返回有效响应。"""
    adapter = AnthropicAdapter(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = await adapter.complete(
        messages=[LLMMessage(role="user", content="Say hello")],
        max_tokens=50,
    )
    assert response.content
    assert response.finish_reason in ("end_turn", "stop_sequence")
```

- 用 `@pytest.mark.live_api` 标记，默认跳过
- 需 `--run-live` 才执行
- 需 `ANTHROPIC_API_KEY` 环境变量
- 失败不阻塞 R4 验收（烟雾测试，非强制）

---

## 技术约束

1. **不改核心模块接口**：与 R3 一致
2. **向后兼容**：REQ-001 签名变更是破坏性变更，需同步修改所有调用点，修改后 381 项测试仍通过
3. **新增文件遵循现有目录结构**：test_live_api.py 放 `04_testing/test_scripts/test_live_api.py`
4. **真实 API 测试**：`@pytest.mark.live_api` 标记，默认跳过，需 `--run-live` 才执行，失败不阻塞验收

## 验收标准

1. `python -m pytest 04_testing/test_scripts/ -q` — 全部通过（现有 381 + 修正后的 E2E 测试）
2. `python -c "from statekanban.adapters.mock_adapter import MockLLMAdapter, MockReviewerBehavior, MockCoderBehavior; m = MockLLMAdapter(); m.set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE, coder_behavior=MockCoderBehavior.GENERATE_SIMPLE); print('OK')"` — 双参数签名可调用
3. TC-E2E-002/003 通过 Engine.drive() 驱动，而非手动构造信号
4. test_live_api.py 存在且可导入（实际执行需 `--run-live`）

## 交付物清单

| # | 文件 | 操作 |
|---|------|------|
| 1 | `05_delivery/statekanban/adapters/mock_adapter.py` | 修改：REQ-001（双参数签名 + artifact_content 精确值 + tester/integrator 预设） |
| 2 | `04_testing/test_scripts/test_e2e.py` | 修改：REQ-002（TC-E2E-001/002/003 改为 Engine.drive() 驱动） |
| 3 | `04_testing/test_scripts/test_mock_adapter.py` | 修改：同步更新 set_behavior_mode 调用点 |
| 4 | `04_testing/test_scripts/test_live_api.py` | 新增：REQ-003（Anthropic API 烟雾测试） |
