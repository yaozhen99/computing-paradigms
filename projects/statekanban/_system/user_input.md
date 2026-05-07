# 项目需求：StateKanban 第五轮 — 可配置项目空间 + R4 遗留修正

## 项目概述

R4 完成了接口修正和端到端测试（381 项测试通过），但存在 2 项实现偏差未修正，且项目空间路径硬编码无法迁移。本轮目标：**实现可配置的项目空间路径，修正 R4 遗留偏差，让 StateKanban 可在任何位置运行。**

## 当前状态

### Config（`05_delivery/statekanban/config.py`）

- `EngineConfig` 有 `output_dir: str = "output"`，但无 `project_root` 概念
- `output_dir` 是绝对路径或相对于 cwd，没有统一的基准目录
- snapshot 路径由调用者自行传入，无配置化

### CLI（`05_delivery/statekanban/cli/main.py`）

- `drive` 命令的 output_dir 硬编码为 `"./output"`
- 无 `--project-root` 参数
- snapshot 子命令无路径配置

### MockLLMAdapter（`05_delivery/statekanban/adapters/mock_adapter.py`）

- `set_behavior_mode(mode)` 仍为单参数签名（R4 REQ-001 要求双参数）
- `GENERATE_WITH_BUG` 的 `artifact_content` 是 `"def hello():\n    print('hello world')"` 而非 `"def hello():\n    return undefined_var\n"`
- tester / integrator 角色无专属预设行为，落入 reviewer 的 ALWAYS_APPROVE

### test_e2e.py（`04_testing/test_scripts/test_e2e.py`）

- TC-E2E-02/03 未走 Engine.drive()，仍用手动构造信号（R4 REQ-002 未修正）

---

## 需求条目

### REQ-501：Config 新增 project_root 字段

**现在**：Config 没有 `project_root` 字段。OutputValve 的写入路径、snapshot 的保存路径都由调用者传入绝对路径或相对于 cwd 的路径，没有统一的基准目录。

**改成**：Config 新增 `project_root` 字段，所有路径相对于此解析。

**接口**：
```python
@dataclass
class EngineConfig:
    project_root: str = "."  # 项目空间根目录，所有相对路径的基准
    output_dir: str = "output"  # 相对于 project_root
    snapshot_dir: str = ".statekanban/snapshots"  # 相对于 project_root
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7
    max_rounds: int = 10
```

**路径解析规则**：
1. 如果 `project_root` 是绝对路径，直接使用
2. 如果 `project_root` 是相对路径，相对于 `os.getcwd()` 解析
3. `output_dir` 和 `snapshot_dir` 始终相对于 `project_root` 解析
4. 提供辅助方法 `resolve_path(relative_path: str) -> str`，统一解析逻辑

**向后兼容**：`project_root` 默认为 `"."`，与当前行为一致（相对于 cwd）。

### REQ-502：CLI 支持 --project-root 参数

**现在**：CLI 无项目空间根目录概念，output_dir 硬编码为 `"./output"`。

**改成**：`statekanban drive` 和 `statekanban snapshot` 新增 `--project-root` 参数。

**接口**：
```bash
# 驱动任务
statekanban drive "实现 hello world 函数" --project-root /path/to/project

# 保存快照
statekanban snapshot save --project-root /path/to/project

# 加载快照
statekanban snapshot load snapshot.json --project-root /path/to/project
```

**默认值**：`--project-root` 默认为当前目录（`.`），与现有行为一致。

**实现**：
- `drive` 命令：从 `--project-root` 构建 Config，传给 Engine
- `snapshot save` 命令：从 `--project-root` 解析 snapshot 存储路径
- `snapshot load` 命令：同上

### REQ-503：调用者从 Config 解析路径传给 OutputValve

**现在**：CLI 构造 OutputValve 时无 output_dir 配置，Engine 不参与路径解析。

**改成**：CLI（或任何 Engine 调用者）从 `Config.resolve_path(config.output_dir)` 解析绝对路径，传给 OutputValve。Engine 本身不改构造签名。

**具体改动**（`cli/main.py`）：
- `cmd_drive()` 中：`valve = OutputValve(kanban=kanban, output_dir=config.resolve_path(config.output_dir))`
- OutputValve 新增 `output_dir` 构造参数（可选，默认 `"./output"`），用于指定写入目录

**具体改动**（`core/valve.py`）：
- OutputValve 构造新增 `output_dir: str = "./output"` 参数
- `_atomic_write()` 中 artifact.path 若为相对路径，相对于 output_dir 解析

### REQ-504：修正 set_behavior_mode 为双参数签名（R4 遗留）

**现在**：`set_behavior_mode(mode: MockReviewerBehavior | MockCoderBehavior)` 只接受单个枚举值。

**改成**：改为双参数签名，与 R4 需求一致。

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

**artifact_content 精确值**：
- GENERATE_SIMPLE：`"def hello():\n    return \"hello world\"\n"`
- GENERATE_WITH_BUG：`"def hello():\n    return undefined_var\n"`

**破坏性变更**：现有单参数调用 `set_behavior_mode(MockReviewerBehavior.ALWAYS_APPROVE)` 会因签名变更报错。需同步修改所有调用点（test_e2e.py、test_mock_adapter.py 等）。这是有意为之——双参数签名是唯一正确的调用方式，不再支持单参数。

### REQ-505：修正 E2E 测试为 Engine.drive() 驱动（R4 遗留）

**现在**：TC-E2E-02/03 使用手动构造信号测试收敛，未走 Engine.drive() 完整流程。

**改成**：改为通过 Engine.drive() + behavior_mode 驱动，验证完整驱动循环。

**TC-E2E-002：碰撞收敛（重写）**
- 用 `_make_system()` 工厂函数构建完整系统
- adapter 设置 `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE, coder_behavior=MockCoderBehavior.GENERATE_SIMPLE)`
- `result = await engine.drive("实现带类型注解的函数")`
- 断言：`result.converged is True`
- 断言：FluidZone 有至少 1 个 VetoSignal

**TC-E2E-003：拦截率（重写）**
- 用 `_make_system()` 工厂函数构建完整系统
- adapter 设置 `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT, coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG)`
- `result = await engine.drive("实现安全函数")`，max_rounds=3
- 断言：`result.converged is False`，`result.forced_terminate is True`
- 断言：CrystalZone 无 artifact

**`_make_system()` 工厂函数定义**：
```python
def _make_system(config: Config | None = None) -> tuple[StateKanban, MessageBus, ToolRegistry, OutputValve, ViewportSlicer, ProcessManager, MockLLMAdapter, Config]:
    """构建完整系统，返回 (kanban, bus, registry, valve, slicer, pm, adapter, config)。"""
    config = config or Config()
    kanban = StateKanban()
    bus = MessageBus(kanban)
    registry = ToolRegistry(kanban)
    valve = OutputValve(kanban=kanban, output_dir=config.resolve_path(config.output_dir))
    # 注册 4 个 viewport（coder/reviewer/tester/integrator）
    for spec in _make_viewport_specs():
        kanban.register_viewport(spec)
    slicer = ViewportSlicer(kanban, _make_viewport_specs())
    pm = ProcessManager(kanban, bus)
    adapter = MockLLMAdapter()
    # 注册 call_llm 工具
    registry.register(ToolDef(...), create_call_llm_tool(adapter))
    return kanban, bus, registry, valve, slicer, pm, adapter, config
```

**TC-E2E-001 也需修正**：改为双参数调用：
```python
adapter.set_behavior_mode(
    reviewer_behavior=MockReviewerBehavior.ALWAYS_APPROVE,
    coder_behavior=MockCoderBehavior.GENERATE_SIMPLE,
)
```

---

## 技术约束

1. **不改核心模块接口**：kanban / message_bus / viewport / valve / registry / process 的公开方法签名不变
2. **向后兼容**：Config.project_root 默认为 `"."`，与当前行为一致
3. **路径解析统一**：所有路径解析走 `Config.resolve_path()`，不允许模块自行拼接路径
4. **新增文件遵循现有目录结构**

## 验收标准

1. `python -m pytest 04_testing/test_scripts/ -q` — 全部通过（现有 381 + 修正后的 E2E 测试）
2. `python -c "from statekanban.config import EngineConfig; c = EngineConfig(project_root='/tmp/test'); print(c.resolve_path('output'))"` — 输出 `/tmp/test/output`
3. `python -c "from statekanban.adapters.mock_adapter import MockLLMAdapter, MockReviewerBehavior, MockCoderBehavior; m = MockLLMAdapter(); m.set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE, coder_behavior=MockCoderBehavior.GENERATE_SIMPLE); print('OK')"` — 双参数签名可调用
4. TC-E2E-002/003 通过 Engine.drive() 驱动
5. `python -m statekanban.cli.main drive "test" --project-root /tmp/test_project` — CLI 可指定项目根目录

## 交付物清单

| # | 文件 | 操作 |
|---|------|------|
| 1 | `05_delivery/statekanban/config.py` | 修改：REQ-501（新增 project_root + resolve_path） |
| 2 | `05_delivery/statekanban/cli/main.py` | 修改：REQ-502（--project-root 参数）+ REQ-503（从 Config 解析路径传给 OutputValve） |
| 3 | `05_delivery/statekanban/core/valve.py` | 修改：REQ-503（新增 output_dir 构造参数） |
| 4 | `05_delivery/statekanban/adapters/mock_adapter.py` | 修改：REQ-504（双参数签名 + artifact_content 精确值 + tester/integrator 预设） |
| 5 | `04_testing/test_scripts/test_e2e.py` | 修改：REQ-505（TC-E2E-001/002/003 改为 Engine.drive() 驱动 + _make_system 工厂函数） |
| 6 | `04_testing/test_scripts/test_mock_adapter.py` | 修改：同步更新 set_behavior_mode 调用点 |
