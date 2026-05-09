# 项目需求：StateKanban 第八轮 — 记忆层 + Briefing 交接

## 项目概述

R1~R7 完成了 StateKanban 内核、引擎、隔离、三路适配器的全量实现（596 测试通过）。但每次 `statekanban drive` 结束后，所有运行时状态随进程消亡——信号、审计日志、收敛轨迹全部丢失。下次启动时 StateKanban 是一张白纸，不知道上次做过什么、为什么做、结果如何。

本轮目标：**给 StateKanban 加上跨会话记忆和结构化交接能力。每次驱动循环结束后自动持久化关键信息，下次启动时可读取 briefing 恢复上下文。**

## 当前痛点

| 痛点 | 表现 | 根因 |
|:---|:---|:---|
| 失忆 | 两次 `drive` 之间无法传递任何信息 | EngineResult 不持久化，AuditZone 随进程消亡 |
| 约束是墙 | 不知道上次收敛在哪、为什么中断 | 没有 session 概念，无法追溯历史 |
| 验证靠模型 | 无法回答"上次跑了几轮？有几个 error？" | 审计日志只在内存，进程结束即丢失 |

## 现有相关模块

| 模块 | 能力 | 缺什么 |
|:---|:---|:---|
| `snapshot.py` | 全量 StateKanban 序列化/反序列化 | 太重（完整 kanban 状态），不适合做轻量交接 |
| `engine/result.py` | EngineResult 摘要（信号计数、artifact 列表） | 不持久化，drive 结束即丢弃 |
| `core/kanban.py` AuditZone | 审计日志（event_type, actor, action, details） | 只在内存，无 session_id，无时间窗口查询 |

## 需求条目

### REQ-801：Session 日志持久化

**描述**：新增 `session/` 模块，每次 `drive` 结束后自动将 EngineResult + 关键审计摘要写入 session 日志文件。

**新增文件**：`session/__init__.py`、`session/logger.py`

**SessionLogger 接口**：
```python
class SessionLogger:
    def __init__(
        self,
        log_dir: str = ".statekanban/sessions",  # 日志目录
        config: Config | None = None,             # 用于路径解析
    )

    def write_session(
        self,
        session_id: str,           # UUID 格式
        intent: str,               # 驱动意图
        result: EngineResult,      # 驱动结果
        adapter_name: str,         # 适配器名
        audit_summary: dict,       # 审计摘要（见下方）
    ) -> str
    # 返回写入的文件路径

    def list_sessions(
        self,
        limit: int = 10,          # 最近 N 个
    ) -> list[SessionMeta]
    # 按时间倒序

    def read_session(self, session_id: str) -> SessionRecord | None

    def read_recent_sessions(
        self,
        hours: float = 72.0,      # 最近 N 小时
    ) -> list[SessionRecord]
```

**数据结构**：
```python
@dataclass(frozen=True)
class SessionMeta:
    session_id: str
    timestamp: str          # ISO 8601
    intent: str             # 截断到 200 字
    converged: bool
    total_rounds: int
    adapter_name: str

@dataclass(frozen=True)
class SessionRecord:
    meta: SessionMeta
    signal_summary: dict[str, int]   # {"intent": N, "veto": N, "error": N}
    artifact_files: list[str]
    error_count: int
    duration_seconds: float
    audit_summary: dict[str, Any]    # 按事件类型分组的计数
    error_codes: list[str]            # 本次 session 出现的 error signal 的 error_code 列表
```

**日志文件格式**：每个 session 一个 JSON 文件，命名 `{timestamp}_{session_id[:8]}.json`，存放在 `log_dir` 下。timestamp 格式：`YYYYMMDD_HHMMSS`（UTC）。

**审计摘要生成**：由 CLI 层（`cmd_drive()`）负责。在 `engine.drive()` 返回后，从 `kanban.audit.read_entries()` 读取所有 entries，按 `event_type` 分组计数，生成 `{"intent_seeded": 1, "circuit_break": 0, ...}` 格式，作为 `audit_summary` 参数传给 `SessionLogger.write_session()`。SessionLogger 不持有 AuditZone 引用——职责分离：CLI 层提取，SessionLogger 只负责持久化。

**验收标准**：
- AC-801.1：`SessionLogger` 可实例化，`log_dir` 不存在时自动创建
- AC-801.2：`write_session()` 写入 JSON 文件，文件内容可被 `read_session()` 完整读回
- AC-801.3：`list_sessions()` 返回按时间倒序的 `SessionMeta` 列表
- AC-801.4：`read_recent_sessions(hours=72)` 只返回 72 小时内的 session
- AC-801.5：日志文件路径通过 `Config.resolve_path()` 解析，受沙箱保护

### REQ-802：Briefing 生成

**描述**：新增 `session/briefing.py`，从最近的 session 日志生成结构化交接文档（briefing），供下次启动或人类阅读。

**Briefing 生成逻辑**：
1. 读取最近 N 个 session 日志（默认 5）
2. 汇总：总驱动次数、收敛率、平均轮次、错误趋势
3. 最近一次 session 的详细信息（意图、结果、artifact）
4. 错误热点：出现频率最高的 error 信号
5. 适配器使用统计

**BriefingGenerator 接口**：
```python
class BriefingGenerator:
    def __init__(self, logger: SessionLogger)

    def generate(
        self,
        recent_count: int = 5,      # 读取最近 N 个 session
    ) -> Briefing

    def generate_text(
        self,
        recent_count: int = 5,
    ) -> str
    # 生成人类可读的文本格式 briefing
```

**Briefing 数据结构**：
```python
@dataclass(frozen=True)
class Briefing:
    total_sessions: int
    convergence_rate: float         # 0.0 ~ 1.0
    avg_rounds: float
    error_trend: str                # "improving" / "stable" / "worsening"
    last_session: SessionRecord | None
    adapter_stats: dict[str, int]   # {"mock": 3, "iflytek": 2, ...}
    error_hotspots: list[tuple[str, int]]  # [("SK_EN_006", 5), ...]  — 从各 SessionRecord.error_codes 汇总
    generated_at: str               # ISO 8601
```

**error_trend 判定**：取最近 5 个 session 的 error_count，计算线性趋势斜率。斜率 < -0.5 为 improving，> 0.5 为 worsening，其余为 stable。

**generate_text() 输出格式**：
```
StateKanban Briefing — {generated_at}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sessions: {total_sessions} | Convergence: {convergence_rate:.0%} | Avg rounds: {avg_rounds:.1f}
Error trend: {error_trend}
Adapters: {adapter_stats}
Last session: {intent} → {"converged" if converged else "not converged"} ({total_rounds} rounds, {duration_seconds:.1f}s)
```

**验收标准**：
- AC-802.1：无 session 日志时，`generate()` 返回空 briefing（total_sessions=0）
- AC-802.2：有 session 日志时，convergence_rate = converged_count / total_sessions
- AC-802.3：error_trend 在连续 5 个 session error_count 递增时为 "worsening"
- AC-802.4：`generate_text()` 输出可被人类直接阅读，无 JSON 残留
- AC-802.5：Briefing 是只读操作，不修改任何文件

### REQ-803：CLI 集成 — session 自动记录 + briefing 命令

**描述**：修改 `cli/main.py`，在 `drive` 命令结束后自动调用 SessionLogger 记录；新增 `briefing` 子命令。

**drive 命令变更**：
1. `cmd_drive()` 在 `engine.drive()` 返回后，自动创建 `SessionLogger` 并调用 `write_session()`
2. session_id 在 drive 开始时生成（UUID4），传入 Engine 用于审计日志关联
3. 新增 `--session-dir` 参数：覆盖默认日志目录
4. 新增 `--no-session` 参数：跳过 session 记录（测试场景用）

**新增 briefing 子命令**：
```
statekanban briefing [--recent N] [--session-dir DIR]
```
- `--recent N`：读取最近 N 个 session（默认 5）
- `--session-dir DIR`：指定日志目录
- 输出 `BriefingGenerator.generate_text()` 的结果到 stdout

**验收标准**：
- AC-803.1：`statekanban drive --adapter mock "test"` 完成后，`.statekanban/sessions/` 下新增一个 session JSON 文件
- AC-803.2：`statekanban briefing` 输出包含最近 session 的信息
- AC-803.3：`statekanban drive --no-session "test"` 不写入 session 日志
- AC-803.4：`--session-dir` 参数可覆盖默认日志目录
- AC-803.5：向后兼容：不带 `--session-dir` / `--no-session` 时行为正确

### REQ-804：AuditZone session_id 关联

**描述**：给 AuditZone 的每个 entry 增加 `session_id` 字段，使审计日志可按 session 过滤。

**变更**：
1. `AuditEntry` 新增 `session_id: str` 字段（默认空字符串，向后兼容）
2. `AuditZone.log()` 新增可选参数 `session_id: str = ""`
3. `AuditZone.read_entries()` 新增可选过滤参数 `session_id: str | None = None`
4. `StateKanban` 的 `to_json()` / `from_json()` 序列化/反序列化 `session_id` 字段
5. `Engine.__init__()` 新增可选参数 `session_id: str = ""`，在调用 `kanban.audit.log()` 时传入

**向后兼容**：
- `session_id` 默认为空字符串，不传时行为与 R7 完全一致
- 旧格式 snapshot（无 `session_id` 字段）加载时，`from_json()` 填充空字符串

**验收标准**：
- AC-804.1：`AuditEntry` 包含 `session_id` 字段
- AC-804.2：`AuditZone.log(event_type="x", actor="y", action="z", details={}, session_id="abc")` 写入的 entry 的 `session_id == "abc"`
- AC-804.3：`AuditZone.read_entries(session_id="abc")` 只返回 `session_id == "abc"` 的 entries
- AC-804.4：不传 `session_id` 时，`AuditEntry.session_id == ""`（向后兼容）
- AC-804.5：R7 snapshot 可正常加载（`session_id` 填充空字符串）

---

## 技术约束

1. **不修改 Engine 驱动循环核心逻辑** — `engine.py` 的 `drive()` 和 `_process_role()` 的循环行为不变，只在 drive 结束后追加 session 记录。`Engine.__init__()` 新增 `session_id` 可选参数属于初始化签名扩展，不算核心逻辑变更。
2. **不修改隔离边界代码** — `valve.py`、`read_file.py` 的沙箱逻辑不动
3. **不新增 pip 依赖** — 只用标准库（`json`、`os`、`uuid`、`datetime`、`dataclasses`）
4. **不引入向量/语义检索** — 本轮只做轻量方案（JSON 文件 + 文本 briefing），不上 RAG
5. **向后兼容** — R7 的 596 测试全部通过；不带 `--session-dir` / `--no-session` 时行为与 R7 一致
6. **session 日志不进 git** — `.statekanban/sessions/` 加入 `.gitignore`（与 snapshots 同策略）

## 验收标准

1. `python -m pytest --tb=short -q` — 全量测试通过（含新增 session/briefing 测试）
2. `statekanban drive --adapter mock "写一个快排函数"` — 完成后 `.statekanban/sessions/` 下有 session 日志
3. `statekanban briefing` — 输出包含最近 session 的结构化摘要
4. `statekanban drive --no-session "test"` — 不写入 session 日志
5. R7 全量测试无回归

## 交付物清单

| # | 文件 | 操作 | 内容 |
|:---|:---|:---|:---|
| 1 | `session/__init__.py` | 新增 | 模块导出 |
| 2 | `session/logger.py` | 新增 | SessionLogger + SessionMeta + SessionRecord |
| 3 | `session/briefing.py` | 新增 | BriefingGenerator + Briefing |
| 4 | `cli/main.py` | 改 | drive 后自动记录 + briefing 子命令 + --session-dir + --no-session |
| 5 | `core/kanban.py` | 改 | AuditEntry/AuditZone 增加 session_id |
| 6 | `config.py` | 改 | 新增 session_dir 配置项 |
| 7 | `04_testing/test_scripts/test_session_logger.py` | 新增 | SessionLogger 单元测试 |
| 8 | `04_testing/test_scripts/test_briefing.py` | 新增 | BriefingGenerator 单元测试 |
