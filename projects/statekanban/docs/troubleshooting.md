# StateKanban 常见问题与解决方案

> 涵盖 R3 迭代新增问题及历史问题。

---

## 安装与启动

### Q: `pip install -e .` 报错 "No module named 'statekanban'"

**原因**：未在正确的目录下执行安装命令。

**解决方案**：

```bash
cd 05_delivery/statekanban
pip install -e .
```

确认当前目录包含 `pyproject.toml`。

### Q: 启动 CLI 报 `ModuleNotFoundError: No module named 'rich'`

**原因**：依赖未完整安装。

**解决方案**：

```bash
pip install -e ".[full]"
# 或单独安装
pip install rich pydantic
```

---

## 适配器与 Registry

### Q: `AdapterNotFoundError: adapter 'openai' not found in registry`

**原因**：OpenAI 适配器未注册到 Registry，或 `statekanban.adapters.openai` 模块缺失。

**解决方案**：

1. 确认已安装 `openai` 包：`pip install openai`
2. 确认适配器已注册：

```python
from statekanban import Registry
from statekanban.adapters.codex_adapter import CodexAdapter

registry = Registry()
registry.register("codex", CodexAdapter())
engine = Engine(kanban=kb, registry=registry, adapter_name="codex")
```

3. 环境变量设置：`STATEKANBAN_LLM_PROVIDER=codex`

### Q: R3 升级后 Engine 构造报 `TypeError: __init__() missing required argument: 'registry'`

**原因**：R3 重构后 Engine 不再接受 `adapter` 参数，改为 `registry` + `adapter_name`。

**解决方案**：

R2 旧代码：
```python
engine = Engine(kanban=kb, adapter=MockAdapter())  # 已废弃
```

R3 新代码：
```python
registry = Registry()
registry.register("mock", MockAdapter())
engine = Engine(kanban=kb, registry=registry, adapter_name="mock")
```

### Q: `AdapterCallError: codex adapter call failed with timeout`

**原因**：Codex 服务不可达或响应超时。

**解决方案**：

1. 检查 Codex 服务端点配置
2. 增加超时时间（适配器 `call()` 方法的 `timeout` 参数）
3. 确认网络连通性：`curl <endpoint>/health`
4. 降级到 mock 适配器进行本地调试

---

## 快照 (Snapshot)

### Q: `SnapshotError: failed to deserialize snapshot file`

**原因**：快照文件损坏或格式不兼容（如 R2 生成的快照缺少 R3 新增字段）。

**解决方案**：

1. 检查文件是否为合法 JSON：`python -m json.tool <snapshot_file>`
2. R2 快照需手动添加缺失字段（`version`, `metadata`）
3. 使用 `Snapshot.from_kanban()` 重新生成快照

### Q: `snapshot --diff` 报 `KeyError` 或结果不完整

**原因**：两个快照来自不同版本的看板定义，泳道名称不一致。

**解决方案**：

1. 确保对比的快照来自同一看板实例或结构兼容的看板
2. 检查泳道名称是否完全匹配（区分大小写）
3. 使用 `--structured` 输出以获取详细错误信息

---

## 阀 (Valve) 与守卫

### Q: 卡片在阀处"卡住"不流动

**原因**：守卫条件过于严格，或守卫函数抛出异常（异常默认返回 `False`）。

**解决方案**：

1. 使用 `--behavior` 查看阀的语义描述，理解守卫意图
2. 检查守卫函数是否正确评估卡片的 `payload`
3. 为守卫函数添加日志：

```python
def my_guard(card: Card) -> bool:
    result = card.payload.get("approved", False)
    logger.debug("Guard evaluated for card %s: %s", card.id, result)
    return result
```

4. 临时移除守卫测试是否为守卫问题

### Q: `ValveGuardError` 但守卫函数返回 `True`

**原因**：R3 中阀守卫评估增加了类型检查，非布尔返回值会触发异常。

**解决方案**：

确保守卫函数返回严格的 `bool` 类型：

```python
# 错误：返回 truthy 值（如 1, "yes", [...]）
def bad_guard(card): return card.payload.get("count")  # 可能返回 int

# 正确：显式返回 bool
def good_guard(card): return bool(card.payload.get("count", 0))
```

---

## 视口 (Viewport)

### Q: 视口投影结果为空

**原因**：`swimlane_filter` 或 `card_filter` 过于严格。

**解决方案**：

1. 空的 `swimlane_filter` 表示订阅全部泳道——确认不是误设了空字符串列表
2. 检查 `card_filter` 函数是否对所有卡片返回 `False`
3. 先不带过滤器创建视口，逐步添加过滤条件

---

## 引擎 (Engine)

### Q: `ConvergenceError: engine failed to converge after N iterations`

**原因**：卡片在泳道间循环移动，导致引擎永远无法收敛。

**解决方案**：

1. 检查是否存在环路：泳道 A -> B -> A 的阀链
2. 增大 `max_iterations` 观察循环模式
3. 调整 `Convergence.max_idle_rounds` 阈值
4. 为环路中的阀添加守卫，打破循环条件

### Q: `advance_all()` 返回空结果列表

**原因**：没有卡片的守卫条件满足通过。

**解决方案**：

1. 使用 `show` 命令查看当前看板状态和卡片位置
2. 检查所有出边阀的守卫条件
3. 使用 `--behavior` 了解每个阀的语义预期
4. 确认卡片 `payload` 包含守卫所需的数据

### Q: Engine 运行时日志过多

**原因**：默认日志级别可能被覆盖。

**解决方案**：

```bash
# CLI 方式
statekanban advance --log-level WARNING

# 环境变量
export STATEKANBAN_LOG_LEVEL=WARNING

# 程序化方式
import logging
logging.getLogger("statekanban").setLevel(logging.WARNING)
```

---

## CLI 输出

### Q: `--structured` 输出不是合法 JSON

**原因**：标准输出混入了非 JSON 内容（如警告日志）。

**解决方案**：

1. 确保日志级别 >= WARNING：`statekanban show --structured --log-level WARNING`
2. 使用 stderr 重定向分离日志：`statekanban show --structured 2>/dev/null`

### Q: `--behavior` 输出为空或显示 "No behavior defined"

**原因**：阀未设置 `behavior` 字段。

**解决方案**：

创建阀时添加行为描述：

```python
valve = Valve(
    name="approve",
    source="review",
    target="approved",
    guard=lambda c: c.payload.get("reviewed"),
    behavior="将已审核的卡片从审核中移至已批准"
)
```

---

## R3 迁移相关

### Q: 旧版配置文件不兼容

**原因**：R3 引入了 `Registry`，配置结构有变更。

**解决方案**：

1. 将 `adapter` 配置替换为 `adapter_name` + `registry` 配置
2. 在启动脚本中显式注册适配器
3. 参考新版本的 `config.py` 对比差异

### Q: R2 测试用例在 R3 下失败

**原因**：Engine 构造签名变更、Snapshot 模块新增。

**解决方案**：

1. 更新 Engine 实例化代码（使用 `Registry`）
2. 确保测试中注册了所需的适配器
3. 为 Snapshot 相关功能添加新的测试用例
4. 参考测试报告 `04_testing/test_report.md` 了解 R3 测试覆盖范围
