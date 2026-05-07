# StateKanban 全程测试流程

> 测试日期：2026-05-07
> 测试主导：00 需求编写师（代理测试协调）
> 基线：381 项自动化测试通过

## 测试目标

验证 StateKanban 从意图注入到文件产出的完整驱动循环可用性。

## 测试阶段

### 阶段一：自动化回归（5 分钟）

**目的**：确认基线未破坏

```bash
cd C:\tower-of-babel\projects\statekanban\04_testing\test_scripts
python -m pytest -q --tb=short
```

**通过标准**：381 项全部通过，0 failed

### 阶段二：Mock 端到端验证（10 分钟）

**目的**：验证 Engine.drive() 完整循环

#### TC-MANUAL-001：正常收敛流程

```python
import asyncio
from statekanban.adapters.mock_adapter import MockLLMAdapter, MockReviewerBehavior, MockCoderBehavior
from statekanban.engine.engine import Engine
from statekanban.core.kanban import StateKanban
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.engine.convergence import ConvergenceDetector
from statekanban.engine.response_parser import ResponseParser
from statekanban.engine.slicer import Slicer
from statekanban.engine.process_manager import ProcessManager

async def test_normal_convergence():
    # 1. 构建系统
    kanban = StateKanban()
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode('reviewer', 'always_approve')
    adapter.set_behavior_mode('coder', 'generate_simple')

    registry = ToolRegistry()
    valve = OutputValve(output_dir="./test_output")
    parser = ResponseParser()
    slicer = Slicer()
    detector = ConvergenceDetector(kanban)
    pm = ProcessManager(kanban, registry, valve, parser, slicer, detector)

    engine = Engine(kanban, adapter, registry, valve, parser, slicer, detector, pm)

    # 2. 驱动
    result = await engine.drive("实现 hello world 函数")

    # 3. 断言
    assert result.converged is True, f"未收敛: {result}"
    assert result.total_rounds >= 1, f"轮次异常: {result.total_rounds}"
    print(f"✅ TC-MANUAL-001 通过: converged={result.converged}, rounds={result.total_rounds}")

asyncio.run(test_normal_convergence())
```

**通过标准**：converged=True, total_rounds>=1

#### TC-MANUAL-002：碰撞收敛（先否决后通过）

```python
async def test_collision_convergence():
    kanban = StateKanban()
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode('reviewer', 'reject_then_approve')
    adapter.set_behavior_mode('coder', 'generate_simple')

    registry = ToolRegistry()
    valve = OutputValve(output_dir="./test_output")
    parser = ResponseParser()
    slicer = Slicer()
    detector = ConvergenceDetector(kanban)
    pm = ProcessManager(kanban, registry, valve, parser, slicer, detector)

    engine = Engine(kanban, adapter, registry, valve, parser, slicer, detector, pm)
    result = await engine.drive("实现带类型注解的函数")

    assert result.converged is True, f"未收敛: {result}"
    # FluidZone 应有 VetoSignal
    veto_count = len([s for s in kanban.fluid_zone.signals if s.type == "veto"])
    assert veto_count >= 1, f"应有至少1个VetoSignal，实际: {veto_count}"
    print(f"✅ TC-MANUAL-002 通过: converged={result.converged}, vetos={veto_count}")

asyncio.run(test_collision_convergence())
```

**通过标准**：converged=True, veto_count>=1

#### TC-MANUAL-003：拦截率（持续否决）

```python
async def test_interception():
    kanban = StateKanban()
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode('reviewer', 'always_reject')
    adapter.set_behavior_mode('coder', 'generate_with_bug')

    registry = ToolRegistry()
    valve = OutputValve(output_dir="./test_output")
    parser = ResponseParser()
    slicer = Slicer()
    detector = ConvergenceDetector(kanban)
    pm = ProcessManager(kanban, registry, valve, parser, slicer, detector)

    engine = Engine(kanban, adapter, registry, valve, parser, slicer, detector, pm)
    result = await engine.drive("实现安全函数", max_rounds=3)

    assert result.converged is False, f"不应收敛: {result}"
    assert result.forced_terminate is True, f"应强制终止: {result}"
    # CrystalZone 不应有 artifact
    artifact_count = len(kanban.crystal_zone.artifacts)
    assert artifact_count == 0, f"不应有artifact，实际: {artifact_count}"
    print(f"✅ TC-MANUAL-003 通过: converged={result.converged}, forced={result.forced_terminate}")

asyncio.run(test_interception())
```

**通过标准**：converged=False, forced_terminate=True, artifact_count=0

### 阶段三：快照恢复验证（5 分钟）

**目的**：验证 snapshot 保存/恢复完整性

#### TC-MANUAL-004：快照保存与恢复

```python
import tempfile, os
from statekanban.snapshot import save_snapshot, load_snapshot
from statekanban.core.kanban import StateKanban

kanban = StateKanban()
# 注入一些信号
from statekanban.core.kanban import IntentSignal
kanban.fluid_zone.add_signal(IntentSignal(author="user", target="task_root", payload={"action": "test"}))

with tempfile.TemporaryDirectory() as tmpdir:
    path = os.path.join(tmpdir, "snapshot.json")

    # 保存
    save_snapshot(kanban, path)
    assert os.path.exists(path), "快照文件未创建"

    # 恢复
    restored = load_snapshot(path)

    # 对比
    assert len(restored.fluid_zone.signals) == len(kanban.fluid_zone.signals), \
        f"信号数不一致: {len(restored.fluid_zone.signals)} vs {len(kanban.fluid_zone.signals)}"
    print(f"✅ TC-MANUAL-004 通过: 信号数={len(kanban.fluid_zone.signals)}")

# 损坏文件测试
with tempfile.TemporaryDirectory() as tmpdir:
    path = os.path.join(tmpdir, "bad.json")
    with open(path, "w") as f:
        f.write("{invalid json")
    try:
        load_snapshot(path)
        print("❌ TC-MANUAL-004b 失败: 应抛 SnapshotIntegrityError")
    except Exception as e:
        print(f"✅ TC-MANUAL-004b 通过: 正确抛出 {type(e).__name__}")
```

**通过标准**：信号数一致 + 损坏文件正确抛异常

### 阶段四：讯飞 MaaS 烟雾测试（5 分钟）

**目的**：验证讯飞 MaaS（Anthropic 兼容接口）通道可达

**配置来源**：`C:\tower-of-babel\claude-code\model_configs\global-settings-xfyun.json`

- Base URL：`https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic`
- Auth Token：`2eb8e6c687fbb47b855a82e8a5e81533:MjU3ZjM3NjkwZjc0MTViOTFmYmVhNWQx`
- Model：`astron-code-latest`

**方式 A：直接 Python 调用**

```python
import asyncio
from statekanban.adapters.anthropic_adapter import AnthropicMessagesAdapter
from statekanban.core.kanban import LLMMessage

async def test_xfyun_smoke():
    adapter = AnthropicMessagesAdapter(
        api_key="2eb8e6c687fbb47b855a82e8a5e81533:MjU3ZjM3NjkwZjc0MTViOTFmYmVhNWQx",
        base_url="https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic",
        model="astron-code-latest",
    )
    response = await adapter.complete(
        messages=[LLMMessage(role="user", content="Say hello")],
        max_tokens=50,
    )
    assert response.content, f"无响应内容: {response}"
    assert response.finish_reason in ("end_turn", "stop_sequence"), f"异常结束: {response.finish_reason}"
    print(f"✅ 讯飞 MaaS 烟雾通过: content={response.content[:50]}")

asyncio.run(test_xfyun_smoke())
```

**方式 B：pytest 标记**

```bash
cd C:\tower-of-babel\projects\statekanban\04_testing\test_scripts
set ANTHROPIC_API_KEY=2eb8e6c687fbb47b855a82e8a5e81533:MjU3ZjM3NjkwZjc0MTViOTFmYmVhNWQx
set ANTHROPIC_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic
python -m pytest test_live_api.py -q --run-live
```

**通过标准**：API 返回有效响应（失败不阻塞，仅记录）

### 阶段五：CLI 验证（5 分钟）

**目的**：验证 CLI 可启动，不再因 snapshot 模块缺失报错

```bash
cd C:\tower-of-babel\projects\statekanban\05_delivery
python -m statekanban.cli.main --help
```

**通过标准**：输出帮助信息，无 ImportError

## 已知偏差（测试时需关注）

| 编号 | 描述 | 影响 | 处理 |
|------|------|------|------|
| DEV-001 | GENERATE_WITH_BUG 的 artifact_content 是正常代码而非有 bug 的代码 | TC-MANUAL-003 可能无法验证"有问题的代码被拦截"语义 | 测试时记录实际行为，R5 修正 |
| DEV-002 | tester/integrator 角色返回 reviewer 的 ALWAYS_APPROVE 预设，无专属行为 | 多角色驱动时 tester/integrator 信号类型可能不符合预期 | 测试时记录实际行为，R5 修正 |

## 测试结果记录

测试完成后，将结果填入下表：

| 阶段 | 用例 | 结果 | 备注 |
|------|------|------|------|
| 一 | 自动化回归 | ✅ | 381 项全部通过，0 failed |
| 二 | TC-MANUAL-001 正常收敛 | ⚠️ | converged=False, rounds=5, forced_terminate=True。DEV-002 影响：tester/integrator 无专属预设，收敛检测无法通过 |
| 二 | TC-MANUAL-002 碰撞收敛 | ⚠️ | converged=False, vetos=0。DEV-002 影响：第二次 set_behavior_mode 清除前一次状态；tester/integrator 无专属预设 |
| 二 | TC-MANUAL-003 拦截率 | ✅ | converged=False, forced_terminate=True, artifacts=0。符合预期（持续否决→强制终止） |
| 三 | TC-MANUAL-004 快照恢复 | ✅ | 信号数一致，保存/恢复正常 |
| 三 | TC-MANUAL-004b 损坏文件 | ✅ | 正确抛出 SnapshotIntegrityError |
| 四 | 讯飞 MaaS 烟雾 | ✅ | API 返回有效响应，finish_reason=end_turn |
| 五 | CLI 验证 | ✅ | 输出帮助信息，无 ImportError |
