# Hermes Agent 迭代预算优化：从"代码读不完"到三档开发流水线

**作者**: Tony + Hermes Agent 协作
**日期**: 2026-05-02
**版本**: v1.0

---

## 摘要

Hermes Agent 在开发场景中存在严重的迭代预算不足问题：默认90次迭代中，仅读取代码就可能耗尽预算，导致开发-测试-审核全流程无法完成。本文分析了迭代消耗的根本原因，提出三层优化方案（内部优化 → 子代理委派 → CC/Codex混编），并给出已验证的代码修改和配置调整。

**关键词**: 迭代预算、Agent开发流程、子代理委派、多Agent协作、迭代退款

---

## 1. 问题定义

### 1.1 现象

Hermes Agent 在执行开发任务时，经常出现"代码刚读完就到头了"的情况：

- 读取3-4个源文件 → 消耗3-4次迭代
- 读取2-3个配置/定义文件 → 消耗2-3次迭代
- 搜索相关代码 → 消耗1-2次迭代
- 规划+编写代码 → 消耗5-10次迭代
- 测试+修复 → 消耗5-10次迭代

**总计：16-29次迭代仅完成一个简单插件的单轮开发**，而默认预算只有90次。

### 1.2 根因分析

Hermes 的迭代预算机制（`IterationBudget`）设计为：**1次API调用 = 1次迭代消耗**。这意味着：

| 操作类型 | 迭代消耗 | 是否改变状态 |
|---------|---------|------------|
| read_file | 1 | 否（只读） |
| search_files | 1 | 否（只读） |
| web_search | 1 | 否（只读） |
| write_file | 1 | 是 |
| terminal | 1 | 是 |
| execute_code | 0（退款） | 否 |
| delegate_task | 1 | 是 |

**核心矛盾**：只读操作（占开发流程60%以上）和写操作消耗相同的迭代预算，但只读操作不改变任何外部状态。

### 1.3 影响范围

迭代预算不足影响开发全流程的每个环节：

1. **开发岗**：读代码+写代码，读取消耗过多预算
2. **测试岗**：读测试框架+运行测试+读结果，读取消耗过多预算
3. **审核岗**：读变更+读规范+写审核意见，读取消耗过多预算

---

## 2. IterationBudget 机制深度分析

### 2.1 核心实现

```python
class IterationBudget:
    def __init__(self, max_total: int):
        self.max_total = max_total
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> bool:
        with self._lock:
            if self._used >= self.max_total:
                return False
            self._used += 1
            return True

    def refund(self) -> None:
        with self._lock:
            if self._used > 0:
                self._used -= 1
```

### 2.2 消耗时机

迭代在主循环中消耗，每次API调用消耗1次：

```python
while (api_call_count < self.max_iterations 
       and self.iteration_budget.remaining > 0) \
       or self._budget_grace_call:
    # ...
    elif not self.iteration_budget.consume():
        break  # 预算耗尽
```

### 2.3 现有退款机制

修改前，仅 `execute_code` 获得退款：

```python
_tc_names = {tc.function.name for tc in assistant_message.tool_calls}
if _tc_names == {"execute_code"}:
    self.iteration_budget.refund()
```

### 2.4 每消息预算重置

每条用户消息创建全新预算：

```python
def run_conversation(self, ...):
    self.iteration_budget = IterationBudget(self.max_iterations)
```

这意味着用户发"继续"即可获得完整预算，但频繁中断影响开发连贯性。

### 2.5 并行工具调用

同一API响应中的多个工具调用只消耗1次迭代：

```python
def _should_parallelize_tool_batch(tool_calls) -> bool:
    # read_file + search_files 可并行 → 1次迭代
    # write_file + write_file（不同路径）可并行 → 1次迭代
```

这是已有的优化，但利用率取决于模型是否主动并行调用。

---

## 3. 三层优化方案

### 3.1 第一层：内部迭代优化（已实施）

#### 3.1.1 只读工具迭代退款

**修改文件**: `run_agent.py`

**核心变更**: 将迭代退款从仅 `execute_code` 扩展到所有非变异工具。

```python
# 新增：非变异工具集合
_BUDGET_FREE_TOOLS = frozenset({
    "execute_code",
    "read_file",
    "search_files",
    "session_search",
    "skill_view",
    "skills_list",
    "web_extract",
    "web_search",
    "vision_analyze",
    "ha_get_state",
    "ha_list_entities",
    "ha_list_services",
})

# 修改退款逻辑
_tc_names = {tc.function.name for tc in assistant_message.tool_calls}
if _tc_names and not _tc_names - _BUDGET_FREE_TOOLS:
    self.iteration_budget.refund()
```

**效果估算**：

| 场景 | 修改前迭代消耗 | 修改后迭代消耗 | 节省 |
|------|-------------|-------------|------|
| 读取5个文件 | 5 | 0 | 100% |
| 搜索+读取3个文件 | 4 | 0 | 100% |
| 读取3个文件+写1个文件 | 4 | 1 | 75% |
| 完整开发流程（读10+写5+测3） | 18 | 8 | 56% |

#### 3.1.2 提升迭代上限

| 参数 | 修改前 | 修改后 | 说明 |
|------|--------|--------|------|
| `agent.max_turns` | 90 | 200 | 每消息迭代上限 |
| `delegation.max_iterations` | 50 | 80 | 子代理迭代上限 |
| `file_read_max_chars` | 100000 | 200000 | 单次读取上限 |

#### 3.1.3 开发流程规则（SOUL.md）

在 SOUL.md 中注入开发流程规则，引导模型高效使用迭代：

- 并行读文件（1次迭代读2-3个文件）
- 不重复读（利用文件去重机制）
- 先规划再动手（第一轮只读不写）
- 大文件分段读

### 3.2 第二层：子代理委派

#### 3.2.1 机制

`delegate_task` 创建独立子代理，子代理拥有自己的 `IterationBudget`：

```python
child = AIAgent(
    max_iterations=80,  # 独立预算
    iteration_budget=None,  # 创建全新 IterationBudget(80)
)
```

**关键特性**：
- 子代理预算与父代理完全独立
- 父代理消耗1次迭代调用 delegate_task
- 子代理获得完整80次迭代
- 父+子总迭代可达 200 + 3×80 = 440（max_concurrent_children=3）

#### 3.2.2 委派配置

```yaml
delegation:
  model: astron-code-latest
  provider: xunfei
  max_iterations: 80
  child_timeout_seconds: 900
  max_concurrent_children: 3
  max_spawn_depth: 2
  orchestrator_enabled: true
```

### 3.3 第三层：CC/Codex 混编流水线

#### 3.3.1 架构

```
Hermes（调度中枢）
  │
  ├─ terminal: claude -p "开发任务" --cwd 项目目录
  │   └─ Claude Code（讯飞API，astron-code-latest）
  │
  ├─ terminal: codex exec "运行测试" -q --cwd 项目目录
  │   └─ Codex（ACW API，gpt-5.5）
  │
  └─ terminal: claude -p "审核代码" --cwd 项目目录
      └─ Claude Code（讯飞API，astron-code-latest）
```

#### 3.3.2 三岗流水线

| 岗位 | 工具 | API | 模型 | 职责 |
|------|------|-----|------|------|
| 开发岗 | Claude Code | 讯飞 | astron-code-latest | 编写代码 |
| 测试岗 | Codex | ACW | gpt-5.5 | 运行测试+报告 |
| 审核岗 | Claude Code | 讯飞 | astron-code-latest | 代码审核 |

#### 3.3.3 调度方式

Hermes 通过 `terminal` 工具依次调用：

1. 开发岗：`claude -p "根据以下需求开发..." --cwd c:\civibbs\v2.0`
2. 收集输出，判断是否完成
3. 测试岗：`codex exec "运行 pytest 测试..." -q --cwd c:\civibbs\v2.0`
4. 收集输出，判断是否通过
5. 审核岗：`claude -p "审核以下变更..." --cwd c:\civibbs\v2.0`
6. 收集输出，判断是否需要修改

---

## 4. 优化效果对比

### 4.1 迭代预算对比

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 每消息迭代上限 | 90 | 200 | +122% |
| 只读操作迭代消耗 | 1/次 | 0/次 | -100% |
| 子代理迭代上限 | 50 | 80 | +60% |
| 单次文件读取量 | 100KB | 200KB | +100% |
| 理论最大迭代（父+3子） | 90+3×50=240 | 200+3×80=440 | +83% |

### 4.2 典型开发场景对比

**场景：开发一个 CiviBBS small 插件**

| 阶段 | 优化前迭代 | 优化后迭代 | 说明 |
|------|-----------|-----------|------|
| 读取 definition.yaml | 1 | 0 | 只读免费 |
| 读取 __init__.py | 1 | 0 | 只读免费 |
| 读取相关插件代码（3个文件） | 3 | 0 | 并行读取，只读免费 |
| 搜索项目结构 | 1 | 0 | 只读免费 |
| 编写代码 | 3 | 3 | 写操作仍消耗 |
| 运行测试 | 2 | 2 | terminal 消耗 |
| 修复bug | 2 | 2 | 写+终端消耗 |
| **合计** | **13** | **7** | **节省46%** |

**场景：完整三岗流水线（使用CC/Codex混编）**

| 阶段 | Hermes迭代 | 说明 |
|------|-----------|------|
| 调度开发岗 | 1 | terminal调用claude -p |
| 收集开发结果 | 0 | terminal输出自动返回 |
| 调度测试岗 | 1 | terminal调用codex exec |
| 收集测试结果 | 0 | terminal输出自动返回 |
| 调度审核岗 | 1 | terminal调用claude -p |
| 收集审核结果 | 0 | terminal输出自动返回 |
| **合计** | **3** | **Hermes仅消耗3次迭代** |

---

## 5. 风险与限制

### 5.1 只读工具免费的风险

- **无限读取循环**：模型可能反复读取同一文件。已有防护：文件去重机制在连续2次stub后硬阻断。
- **上下文窗口溢出**：免费读取可能导致上下文过大。已有防护：自动压缩在50%阈值触发。
- **API成本增加**：免费读取可能导致更多API调用。但讯飞API按token计费，读取操作token量小。

### 5.2 CC/Codex混编的限制

- Claude Code `-p` 模式无交互能力，复杂任务可能失败
- Codex `exec` 模式对Windows支持有限
- 两个外部工具的输出格式不统一，Hermes需要解析

### 5.3 子代理委派的限制

- 子代理无法使用 `delegate_task`（被阻止的工具之一）
- 子代理超时600秒，长时间任务可能被杀
- 嵌套深度限制为2层

---

## 6. 结论

通过三层优化，Hermes Agent 的开发流程迭代预算问题得到系统性解决：

1. **第一层（内部优化）**：只读工具免费 + 提升上限 + 流程规则，直接将开发场景的迭代消耗降低约50%
2. **第二层（子代理委派）**：复杂任务委派给独立预算的子代理，理论最大迭代提升83%
3. **第三层（CC/Codex混编）**：完整三岗流水线，Hermes仅消耗3次迭代作为调度中枢

三层方案逐层递进，每层独立可用，组合效果叠加。第一层已通过代码修改验证，第二层和第三层通过配置和SOUL.md规则实现。

---

## 附录A：修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `c:\hermes-win\src\run_agent.py` | 新增 `_BUDGET_FREE_TOOLS` 集合，修改迭代退款逻辑 |
| `c:\hermes-win\src\tools\delegate_tool.py` | `DEFAULT_MAX_ITERATIONS` 从50提升到80 |
| `c:\hermes-win\home\config.yaml` | `max_turns` 90→200，`max_iterations` 50→80，`file_read_max_chars` 100K→200K |
| `c:\hermes-win\home\SOUL.md` | 重写开发流程规则，增加三档开发和三岗流水线 |

## 附录B：配置参考

### CC（Claude Code）配置
- 版本：2.1.123
- API：讯飞 Anthropic兼容（`maas-coding-api.cn-huabei-1.xf-yun.com/anthropic`）
- 模型：astron-code-latest
- 调用方式：`claude -p "任务" --cwd 目录`

### Codex 配置
- 版本：0.128.0
- API：ACW聚合（`api.aicodewith.com/v1`）
- 模型：gpt-5.5
- 调用方式：`codex exec "任务" -q --cwd 目录`

### Fallback 配置
- 第一备选：DeepSeek（`api.deepseek.com/v1`，deepseek-chat）
- 第二备选：ACW（`api.aicodewith.com/v1`，gpt-5.5）
