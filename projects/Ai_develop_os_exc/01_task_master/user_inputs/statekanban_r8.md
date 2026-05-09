# 任务师指令：StateKanban R8 — 记忆层 + Briefing 交接

## 需求文档

`00_requirement_writer/user_inputs/statekanban_r8.md`

## 实现顺序

按依赖关系从底向上：

1. **REQ-804** — AuditZone session_id 关联（基础设施变更，其他需求依赖）
2. **REQ-801** — Session 日志持久化（核心数据层）
3. **REQ-802** — Briefing 生成（依赖 REQ-801 的 SessionLogger）
4. **REQ-803** — CLI 集成（依赖 REQ-801 + REQ-802）

## 关键约束

- **不修改 Engine 驱动循环核心逻辑** — `engine.py` 的 `drive()` 和 `_process_role()` 逻辑不变
- **不修改隔离边界代码** — `valve.py`、`read_file.py` 不动
- **不新增 pip 依赖** — 只用标准库
- **向后兼容** — R7 的 596 测试全部通过；旧 snapshot 正常加载
- **session 日志不进 git** — `.statekanban/sessions/` 加入 `.gitignore`

## 每个 REQ 的测试要求

### REQ-804 测试
- AuditEntry 包含 session_id 字段
- AuditZone.log() 传入 session_id 后可被 read_entries(session_id=...) 过滤
- 不传 session_id 时默认空字符串（向后兼容）
- 旧格式 snapshot 加载后 session_id 为空字符串

### REQ-801 测试
- SessionLogger 初始化时 log_dir 不存在则自动创建
- write_session() 写入 JSON 后 read_session() 可完整读回
- list_sessions() 按时间倒序
- read_recent_sessions(hours=N) 只返回时间窗口内的 session
- 日志路径受 Config.resolve_path() 保护

### REQ-802 测试
- 无 session 时 generate() 返回空 briefing
- convergence_rate 计算正确
- error_trend 判定正确（improving/stable/worsening）
- generate_text() 输出人类可读，无 JSON 残留
- Briefing 是只读操作

### REQ-803 测试
- drive 结束后 session 日志文件存在
- briefing 子命令输出正确
- --no-session 跳过记录
- --session-dir 覆盖默认目录
- 向后兼容（不带新参数时行为正确）

## 代码风格

- 遵循现有代码风格：dataclass(frozen=True)、类型注解、docstring
- 测试文件放在 `04_testing/test_scripts/` 下
- 新模块放在 `05_delivery/statekanban/session/` 下
