# StateKanban R8 更新需求 — 看板唯一真理源

> 版本：v2.0（替代 v1.0 ISA 记忆层方案）
> 日期：2026-05-09
> 作者：yaozhen99 + Claude Opus 4.7
> 状态：需求定义

---

## 0. 为什么要更新

R8 v1.0（ISA 管道实现）用 ConversationMemory + Briefing 给 LLM 加了旁路记忆，违反了 Final Spec 三条公理：

1. **公理 1 违反**：LLM 应无状态，ConversationMemory 让 LLM 依赖对话历史而非看板信号
2. **公理 2 违反**：看板应是唯一真理源，ConversationMemory 制造了第二个真理源
3. **公理 3 违反**：memory 的生命周期由 Engine 管理，不在看板生命周期之内

v2.0 的方向：**所有状态都在看板上，LLM 每次调用只看看板**。不需要旁路记忆，不需要 briefing 注入。

---

## 1. 需求总览

| REQ | 名称 | 核心变更 |
|:---|:---|:---|
| REQ-801 | 看板生命周期与 drive 解耦 | drive 结束看板不销毁，看板是长驻的 |
| REQ-802 | FluidZone 清空恢复 | 进程取消时清空流态区，从晶态稳定点重启 |
| REQ-803 | 视口切片完整状态读取 | 视口从看板读取完整状态，不需要 memory 注入 |
| REQ-804 | 信号压缩 | FluidZone 信号过多时自动压缩为 CrystalZone artifact |

---

## 2. REQ-801：看板生命周期与 drive 解耦

### 2.1 问题

当前 `cmd_drive()` 每次调用创建新的 StateKanban 实例，drive 结束后看板被丢弃。看板是 drive 的附属品，不是独立实体。

```python
# 当前 cli/main.py cmd_drive()
kanban = StateKanban()  # 每次新建
engine = Engine(kanban=kanban, ...)
result = await engine.drive(task)
# drive 结束，kanban 随函数退出被 GC
```

### 2.2 变更

**看板是长驻的，drive 是临时的。** drive 是看板上的一次信号碰撞循环，不是看板的生命周期。

#### AC-801.1：看板实例跨 drive 复用

`cmd_drive()` 支持看板实例复用：

- 新增 CLI 参数 `--kanban-id <id>`：指定看板实例标识
- 同一 `--kanban-id` 的多次 drive 调用复用同一个看板实例
- 不指定 `--kanban-id` 时，行为与 R7 一致（每次新建看板，向后兼容）
- 看板实例存储在进程内存中（`dict[str, StateKanban]`），不需要跨进程持久化

```python
# 修正后
_KANBAN_REGISTRY: dict[str, StateKanban] = {}

def cmd_drive(task, kanban_id=None, ...):
    if kanban_id and kanban_id in _KANBAN_REGISTRY:
        kanban = _KANBAN_REGISTRY[kanban_id]
    else:
        kanban = StateKanban()
        if kanban_id:
            _KANBAN_REGISTRY[kanban_id] = kanban
    engine = Engine(kanban=kanban, ...)
    result = await engine.drive(task)
    # drive 结束，kanban 保留在 registry 中
```

#### AC-801.2：看板状态在 drive 间保留

- drive 结束后，FluidZone 信号、CrystalZone artifact、AuditZone 记录全部保留
- 下一次 drive（同一 kanban_id）看到上一次 drive 的完整状态
- 不需要 ConversationMemory，不需要 Briefing——看板本身就是状态延续

#### AC-801.3：看板显式销毁

- 新增 CLI 命令 `kanban destroy <id>`：显式销毁看板实例
- 销毁时从 registry 移除，释放内存
- 不提供 `destroy` 命令时，看板在进程生命周期内一直存在

#### AC-801.4：看板列表查看

- 新增 CLI 命令 `kanban list`：列出当前进程内所有看板实例
- 输出格式：`<id>  signals=<N>  artifacts=<N>  audits=<N>`

#### AC-801.5：Config 新增 kanban_id 字段

- `Config.kanban_id: str | None = None`
- CLI `--kanban-id` 参数写入 Config.kanban_id

### 2.3 不做的事

- 不做看板跨进程持久化（R9+ 考虑）
- 不做看板序列化/反序列化（已有 snapshot.py，但不在 R8 范围）

---

## 3. REQ-802：FluidZone 清空恢复

### 3.1 问题

当前 `FluidZone.clear_signals()` 存在但从未被调用。Engine 熔断时只返回失败，不清空流态区。半成品信号留在 FluidZone 里，下一次 drive 会看到脏数据。

### 3.2 变更

**进程取消 = 清空流态区 + 从晶态稳定点重启。** 零成本无损接管。

#### AC-802.1：Engine 熔断时清空 FluidZone

- `Engine.drive()` 熔断（超过 max_rounds）时，调用 `kanban.fluid.clear_signals()`
- 清空后，FluidZone 为空，CrystalZone 的 artifact 不受影响
- 熔断恢复路径：清空 → 视口切片只看到 CrystalZone → LLM 从稳定点重新推理

```python
# engine.py drive() 熔断分支
if round_count >= self._max_rounds:
    kanban.fluid.clear_signals()  # 清空半成品信号
    return EngineResult(status="fused", ...)
```

#### AC-802.2：手动清空 FluidZone

- 新增 CLI 命令 `kanban clear <id>`：手动清空指定看板的 FluidZone
- 用途：开发者发现看板卡死时，手动清空重来
- 清空后 CrystalZone 和 AuditZone 不受影响

#### AC-802.3：清空操作记录到 AuditZone

- `clear_signals()` 执行时，向 AuditZone 写入一条记录
- 记录内容：`{"action": "fluid_cleared", "reason": "fused"|"manual", "cleared_signal_count": N}`
- 清空不是无声的——审计追踪保留

#### AC-802.4：清空后 drive 可恢复

- 清空 FluidZone 后，下一次 drive 能正常执行
- 视口切片只看到 CrystalZone artifact（稳定事实），不看到已清空的信号
- LLM 基于 CrystalZone 重新推理，不需要任何"记忆"辅助

### 3.3 不做的事

- 不做 CrystalZone 回滚（清空只影响 FluidZone，CrystalZone 是稳定事实不回滚）
- 不做信号选择性清空（全部清空，不留半成品）

---

## 4. REQ-803：视口切片完整状态读取

### 4.1 问题

当前 `ViewportSlicer._build_context()` 没有执行 token 截断，且视口只读取当前角色的相关信号。LLM 看不到看板的完整状态。

R8 ISA 的解法是给 LLM 注入 ConversationMemory 历史——但这是旁路，违反公理 2。

正确解法：**视口切片从看板读取完整状态，组装为 LLM 输入**。不需要 memory，不需要 briefing。

### 4.2 变更

#### AC-803.1：视口切片读取看板完整状态

- `ViewportSlicer.slice(role)` 返回的上下文包含：
  1. CrystalZone 全部 artifact（稳定事实，通常很小）
  2. FluidZone 全部信号（当前轮次的活跃信号）
  3. AuditZone 最近 N 条记录（可选，由配置控制）
- 不再需要 Engine 注入 memory 或 briefing

#### AC-803.2：token budget 硬限制

- 视口切片组装后，token 总量硬限制在 `max_tokens` 以内
- 截断策略：
  1. CrystalZone artifact 不截断（稳定事实优先）
  2. AuditZone 记录截断（只保留最近 N 条）
  3. FluidZone 信号截断（从最旧的开始截断）
- 复用 R8 ISA 的 `_estimate_tokens()` 逻辑，迁移到 ViewportSlicer

```python
class ViewportSlicer:
    def slice(self, role: str) -> list[LLMMessage]:
        context = self._build_context(role)
        context = self._enforce_token_budget(context, self._max_tokens)
        return context

    def _enforce_token_budget(self, messages, max_tokens):
        total = sum(_estimate_tokens(m.content) for m in messages)
        if total <= max_tokens:
            return messages
        # 截断策略：CrystalZone 不动 → AuditZone 截断 → FluidZone 截断
        ...
```

#### AC-803.3：移除 Engine 的 memory/briefing 注入

- 删除 `Engine._memory` 属性
- 删除 `Engine._briefing_text` 属性
- 删除 `Engine.set_briefing()` 方法
- 删除 `Engine.drive()` 中的 memory append/inject 逻辑
- LLM 的输入完全由视口切片决定，Engine 不再干预

#### AC-803.4：移除 CLI --memory/--briefing 参数

- 删除 `--memory on/off/auto` 参数
- 删除 `--briefing on/off` 参数
- 删除 `_init_memory()` 辅助函数
- 删除 `_save_memory_with_adapter()` 辅助函数
- 看板永远在，不需要"开关记忆"

#### AC-803.5：Config 移除 memory/briefing 字段

- 删除 `Config.memory_mode`
- 删除 `Config.memory_max_tokens`
- 删除 `Config.memory_persist_path`
- 删除 `Config.briefing_mode`
- 删除 `Config.briefing_rounds`
- 删除 `Config.memory_file_path`
- 新增 `Config.viewport_max_tokens: int = 8000`（视口 token 预算，替代 memory_max_tokens）

### 4.3 不做的事

- 不做视口切片的角色差异化（当前所有角色看到相同上下文，R9 信号驱动后角色只订阅自己关心的信号类型，视口自然差异化）

---

## 5. REQ-804：信号压缩

### 5.1 问题

FluidZone 信号无限增长。多次 drive 后，FluidZone 可能积累大量信号，导致视口切片 token 超限。

当前没有机制将 FluidZone 的旧信号沉淀为 CrystalZone 的稳定事实。

### 5.2 变更

**信号压缩 = FluidZone 旧信号 → CrystalZone artifact。** 复用 R8 ISA 的摘要逻辑，但迁移到看板层面。

#### AC-804.1：FluidZone 信号数量阈值

- `FluidZone` 新增 `max_signals: int = 50` 参数
- 信号数量超过 `max_signals` 时，触发自动压缩
- 默认值 50 是经验值，可通过 Config 调整

#### AC-804.2：自动压缩逻辑

- 压缩触发时，将最旧的 70% 信号摘要为一条 CrystalZone artifact
- 摘要格式：`{"type": "signal_summary", "source_signals": N, "summary": "...", "compressed_at": "ISO8601"}`
- 摘要后，被压缩的信号从 FluidZone 移除
- 保留最近 30% 信号不被压缩

```python
class FluidZone:
    def write_signal(self, signal):
        self._signals.append(signal)
        self._compress_if_needed()

    def _compress_if_needed(self):
        if len(self._signals) <= self._max_signals:
            return
        # 保留最近 30%
        split = int(len(self._signals) * 0.7)
        old_signals = self._signals[:split]
        recent_signals = self._signals[split:]
        # 摘要旧信号
        summary = self._summarize_signals(old_signals)
        # 写入 CrystalZone
        self._kanban.crystal.write_artifact(
            key=f"signal_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            value=summary,
        )
        # 更新 FluidZone
        self._signals = recent_signals
```

#### AC-804.3：信号摘要生成

- 复用 R8 ISA `ConversationMemory._summarize_messages()` 的逻辑
- 迁移为 `FluidZone._summarize_signals(signals: list[Signal]) -> str`
- 摘要规则：
  - IntentSignal → 截取前 100 字符
  - VetoSignal → 截取前 100 字符 + 原因
  - ErrorSignal → 截取前 100 字符 + 错误码
  - 总摘要不超过 500 字符

#### AC-804.4：压缩操作记录到 AuditZone

- 压缩执行时，向 AuditZone 写入一条记录
- 记录内容：`{"action": "signals_compressed", "compressed_count": N, "artifact_key": "signal_summary_XXXXXX"}`

#### AC-804.5：Config 新增信号压缩配置

- `Config.fluid_max_signals: int = 50` — FluidZone 信号数量阈值
- `Config.fluid_compress_ratio: float = 0.7` — 压缩比例（旧信号占比）

### 5.3 不做的事

- 不做信号选择性压缩（全部旧信号一起压缩，不挑拣）
- 不做压缩撤销（压缩是不可逆的，审计记录保留）

---

## 6. 交付物

| 编号 | 交付物 | 对应 REQ |
|:---|:---|:---|
| D-801 | `core/kanban.py` 修改：FluidZone 新增 max_signals、_compress_if_needed、_summarize_signals；StateKanban 新增 name 属性 | 801, 804 |
| D-802 | `engine/engine.py` 修改：移除 _memory/_briefing_text/set_briefing；熔断时调用 clear_signals() | 802, 803 |
| D-803 | `engine/viewport.py` 修改：_build_context 从看板读取完整状态；新增 _enforce_token_budget | 803 |
| D-804 | `cli/main.py` 修改：移除 --memory/--briefing；新增 --kanban-id；新增 kanban list/destroy/clear 命令 | 801, 802, 803 |
| D-805 | `config.py` 修改：移除 memory/briefing 字段；新增 kanban_id、viewport_max_tokens、fluid_max_signals、fluid_compress_ratio | 801, 803, 804 |
| D-806 | `core/memory.py` 删除 | 803 |
| D-807 | `core/briefing.py` 删除 | 803 |
| D-808 | 测试更新：移除 test_memory.py/test_briefing.py；新增 test_kanban_lifecycle.py、test_fluid_recovery.py、test_viewport_full_state.py、test_signal_compression.py | 全部 |

---

## 7. 技术约束

### 7.1 向后兼容

- 不指定 `--kanban-id` 时，行为与 R7 完全一致（每次新建看板，drive 结束丢弃）
- `--kanban-id` 是新功能，不影响现有用法
- 移除 `--memory`/`--briefing` 是**破坏性变更**，但 R8 尚未正式发布，无外部用户

### 7.2 不修改 Engine 核心循环

- Engine.drive() 的 while True 循环和角色遍历顺序不变（R9 改）
- 只改熔断分支（加 clear_signals 调用）和移除 memory/briefing 注入

### 7.3 不新增模块

- 所有变更都在现有文件内完成
- 删除 memory.py 和 briefing.py，不新增文件
- 看板注册表 `_KANBAN_REGISTRY` 放在 cli/main.py 内（进程级单例）

### 7.4 R8 ISA 代码复用

| ISA 组件 | 复用方式 |
|:---|:---|
| `_estimate_tokens()` | 迁移到 viewport.py，作为视口 token 估算函数 |
| `_compact_if_needed()` 逻辑 | 迁移到 FluidZone._compress_if_needed() |
| `_summarize_messages()` 逻辑 | 迁移到 FluidZone._summarize_signals() |
| Briefing._extract_* 逻辑 | 不复用——视口切片直接读取看板，不需要提取/注入 |

---

## 8. 验收标准

### 功能验收

- [ ] `sk drive "task" --kanban-id proj1` 连续执行两次，第二次 drive 能看到第一次的看板状态
- [ ] `sk kanban list` 列出当前所有看板实例
- [ ] `sk kanban clear proj1` 清空 FluidZone，CrystalZone 不受影响
- [ ] `sk kanban destroy proj1` 销毁看板实例
- [ ] Engine 熔断时自动清空 FluidZone
- [ ] 清空后下一次 drive 能正常执行，LLM 基于 CrystalZone 重新推理
- [ ] 视口切片 token 量硬限制在 viewport_max_tokens 以内
- [ ] FluidZone 信号超过 fluid_max_signals 时自动压缩为 CrystalZone artifact
- [ ] 压缩和清空操作记录到 AuditZone

### 回归验收

- [ ] 不指定 `--kanban-id` 时，所有 R7 测试通过
- [ ] 移除 `--memory`/`--briefing` 后，无残留引用
- [ ] 668 测试基线中，R8 ISA 新增的 72 测试替换为新测试，其余 596 测试无回归

### 公理验收

- [ ] LLM 每次调用只看到看板状态，不依赖对话历史（公理 1）
- [ ] 看板是唯一真理源，不存在旁路状态容器（公理 2）
- [ ] 看板生命周期独立于 drive，drive 是看板上的临时循环（公理 3）

---

## 9. 与 R9 的边界

| R8 修正 | R9 信号驱动 |
|:---|:---|
| 看板是唯一真理源 | 看板是事件总线 |
| 状态承载：看板不灭、信号持久 | 通信模式：信号写入→即时通知→角色响应 |
| 视口从看板读取完整状态 | 角色只订阅自己关心的信号类型 |
| FluidZone 清空恢复 | 进程即生即灭 |
| 信号压缩（FluidZone→CrystalZone） | MessageBus 接通 |

R8 解决"状态在哪里"，R9 解决"状态怎么流动"。R8 是 R9 的前提。
