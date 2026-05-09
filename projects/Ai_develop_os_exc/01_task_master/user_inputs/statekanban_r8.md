# 任务师指令：StateKanban R8 修正 — 看板唯一真理源

## 需求文档

`00_requirement_writer/user_inputs/statekanban_r8.md`（v2.0）

## 实现顺序

按依赖关系从底向上：

1. **REQ-804** — 信号压缩（FluidZone 层变更，视口切片依赖压缩后的看板状态）
2. **REQ-802** — FluidZone 清空恢复（依赖 REQ-804 的压缩逻辑，清空后需要看板能正常工作）
3. **REQ-803** — 视口切片完整状态读取（依赖 REQ-804 的压缩和 REQ-802 的清空恢复）
4. **REQ-801** — 看板生命周期与 drive 解耦（依赖 REQ-803 的视口切片，CLI 集成最上层）

## 关键约束

- **不修改 Engine 驱动循环核心逻辑** — `drive()` 的 while True 循环和角色遍历顺序不变（R9 改）
- **只改熔断分支** — 熔断时加 `kanban.fluid.clear_signals()` 调用
- **不修改隔离边界代码** — `valve.py`、`read_file.py` 不动
- **不新增 pip 依赖** — 只用标准库
- **向后兼容** — 不指定 `--kanban-id` 时行为与 R7 完全一致
- **删除 memory.py 和 briefing.py** — R8 ISA 的旁路记忆模块全部移除
- **复用 ISA 代码** — `_estimate_tokens()` 迁移到 viewport.py，摘要逻辑迁移到 FluidZone

## 每个 REQ 的测试要求

### REQ-804 测试（信号压缩）
- FluidZone 默认 max_signals=50
- 信号超过阈值时自动触发压缩
- 压缩后旧信号从 FluidZone 移除，最近 30% 保留
- 压缩产物写入 CrystalZone（signal_summary artifact）
- 压缩操作记录到 AuditZone
- _summarize_signals() 正确摘要 IntentSignal/VetoSignal/ErrorSignal
- 摘要总长度不超过 500 字符
- Config.fluid_max_signals 和 fluid_compress_ratio 可配置

### REQ-802 测试（FluidZone 清空恢复）
- Engine 熔断时调用 clear_signals()
- clear_signals() 后 FluidZone 为空，CrystalZone 不受影响
- 清空操作记录到 AuditZone（action="fluid_cleared", reason="fused"）
- `kanban clear <id>` CLI 命令手动清空
- 清空后下一次 drive 能正常执行
- 清空后视口切片只看到 CrystalZone artifact

### REQ-803 测试（视口切片完整状态读取）
- ViewportSlicer.slice() 返回 CrystalZone artifact + FluidZone signals + AuditZone entries
- token 总量硬限制在 viewport_max_tokens 以内
- 截断策略：CrystalZone 不截断 → AuditZone 截断 → FluidZone 截断
- Engine._memory 和 Engine._briefing_text 已删除
- Engine.set_briefing() 已删除
- CLI --memory/--briefing 已删除
- Config memory/briefing 字段已删除
- Config.viewport_max_tokens 可配置
- 不指定 --kanban-id 时视口行为与 R7 一致

### REQ-801 测试（看板生命周期与 drive 解耦）
- `sk drive "task" --kanban-id proj1` 创建看板实例
- 同一 kanban-id 第二次 drive 复用看板，能看到上次的信号和 artifact
- `sk kanban list` 列出所有看板实例
- `sk kanban destroy proj1` 销毁看板实例
- `sk kanban clear proj1` 清空 FluidZone
- 不指定 --kanban-id 时每次新建看板（向后兼容）
- Config.kanban_id 字段

## 代码风格

- 遵循现有代码风格：dataclass(frozen=True)、类型注解、docstring
- 测试文件放在 `04_testing/test_scripts/` 下
- 新增测试文件：test_kanban_lifecycle.py、test_fluid_recovery.py、test_viewport_full_state.py、test_signal_compression.py
- 删除旧测试文件：test_memory.py、test_briefing.py
- 所有变更在现有文件内完成，不新增模块文件

## ISA 代码迁移指引

| ISA 文件 | 迁移目标 | 迁移内容 |
|:---|:---|:---|
| core/memory.py `_estimate_tokens()` | engine/viewport.py | token 估算函数，用于视口截断 |
| core/memory.py `_compact_if_needed()` | core/kanban.py FluidZone._compress_if_needed() | 压缩触发逻辑 |
| core/memory.py `_summarize_messages()` | core/kanban.py FluidZone._summarize_signals() | 信号摘要生成 |
| core/memory.py ConversationMemory | **删除** | 不迁移，方向错误 |
| core/briefing.py Briefing | **删除** | 不迁移，方向错误 |