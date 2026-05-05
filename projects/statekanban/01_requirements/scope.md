# Scope: StateKanban -- 范围定义

> **迭代轮次**: 第二轮 -- 驱动循环 + Codex 接入

## 1. 做什么（In Scope）

### 1.1 核心引擎（第一轮，已实现）

| 模块 | 范围 | 状态 |
|------|------|------|
| StateKanban（状态看板） | 流态区信号管理、碰撞与收敛循环；晶态区只追加写入；视口索引；JSON 快照序列化与恢复；审计区 | 已实现 |
| MessageBus（消息总线） | 发布/订阅模式；同步调用 + 异步通知；纯内存通信；不落盘 | 已实现 |
| ViewportSlicer（视口切片器） | 角色感知切片；Token 阈值控制；切片策略优先级；切片日志 | 已实现 |
| OutputValve（输出阀门） | 校验链；校验失败回注流态区；原子写入；人工确认门（可选） | 已实现 |
| ToolRegistry（工具注册表） | 工具注册（write_file, read_file, run_shell, call_llm, search_code）；权限控制；调用审计；超时与重试 | 已实现 |
| ProcessManager（进程管理） | 生命周期状态机；禁止自杀约束；心跳机制；交接协议 | 已实现 |

### 1.2 驱动引擎（第二轮新增）

| 子模块 | 范围 |
|--------|------|
| Engine 主循环 | 从流态区读取未处理信号→根据信号类型选择进程→视口切片→调用 LLM/Codex→解析返回值→信号回传→碰撞检测→收敛判定→晶态固化→阀门写出 |
| 碰撞收敛策略 | 同一 target_id 的意图与否定信号碰撞；收敛条件=最新一轮无新否决或否决被覆盖；最大轮数可配置默认 10；超时熔断报告人类 |
| LLM 返回值解析 | 解析结构化 JSON（intent/veto/artifact）；解析失败→错误信号回注流态区 |
| 角色调度顺序 | 默认 Coder→Reviewer→Tester→Integrator；每角色处理后下一角色通过视口看到前序产出 |
| 视口隔离 | 每个角色的视口不包含其他角色的内部信号 |
| 循环结果摘要 | 循环结束后输出：收敛状态、产出文件列表、轮数统计 |
| 熔断机制 | 超过最大轮数后熔断，输出当前状态，不进入死循环 |

**不重写**: 复用现有 kanban/message_bus/viewport/valve/registry/process 模块，引擎只做调度串联。

### 1.3 Codex 接入（第二轮新增）

| 子模块 | 范围 |
|--------|------|
| CodexAdapter | 与 AnthropicMessagesAdapter 平级的适配层；通过 Codex CLI（`codex` 命令行工具）执行；输入 prompt + context_files；输出代码片段；返回值解析后注入看板 |
| call_codex 工具 | 注册到 ToolRegistry，与 call_llm 平级；参数：prompt / context_files / output_path / max_tokens |
| 权限控制 | Coder/Integrator 可调用 call_codex；Reviewer/Tester/Architect 不可调用；调用被拒时记录审计日志 |
| 产出注入 | Codex 产出的代码片段解析为意图信号或代码产出，注入看板流态区/晶态区候选 |

**遵循现有模式**: Codex 接入遵循 ToolRegistry 模式，不引入新的调度机制。

### 1.4 LLM 调用层（第一轮 + 第二轮增量）

| 形态 | 范围 | 状态 |
|------|------|------|
| Mock 适配器 | 支持返回结构化 JSON（intent/veto/artifact），用于驱动循环测试 | 新增/增强 |
| Anthropic API 适配器 | 直接调 Messages API，支持 tool_use，支持 streaming | 已实现 |
| Claude Code CLI 适配器 | 通过 subprocess 调用 claude -p | 已实现 |
| Codex CLI 适配器 | 通过 Codex CLI 执行，输入 prompt + context files，输出代码片段 | 新增 |

### 1.5 内部进程角色（第一轮，不变）

- Coder：代码生成（可调用 call_llm + call_codex）
- Reviewer：代码审核（仅可调用 call_llm）
- Integrator：模块集成（可调用 call_llm + call_codex）
- Tester：测试生成与执行（仅可调用 call_llm）
- Architect：架构设计（仅可调用 call_llm）

### 1.6 CLI 入口（第一轮 + 第二轮增量）

- 任务启动：`statekanban run --intent "..."`（初始化→写入意图信号→启动驱动循环→输出结果摘要）
- 适配层选择：`--adapter {mock,anthropic,cli,codex}`，默认 mock
- 最大循环轮数：`--max-rounds N`，默认 10
- 详细输出：`--verbose`，输出每轮循环详细信息
- 状态查询：`statekanban status`
- 快照管理：`statekanban snapshot` / `statekanban restore`

### 1.7 第二轮交付物

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 调度引擎 | statekanban/engine.py | 驱动循环主逻辑 |
| Codex 工具 | statekanban/tools/call_codex.py | call_codex 工具实现 |
| Codex 适配层 | statekanban/adapters/codex_adapter.py | CodexAdapter 实现 |
| CLI 更新 | statekanban/cli/main.py | 集成驱动循环 + --adapter + --max-rounds + --verbose |
| 测试用例 | tests/ | 驱动循环测试 + Codex 接入测试 + 权限隔离测试 |

### 1.8 测试标准

| 指标 | 目标 | 覆盖场景 |
|------|------|----------|
| 收敛率 | 碰撞循环 90% 在 3 轮内收敛 | Mock LLM: Coder→Reviewer 通过→固化→写出 |
| 拦截率 | 恶意/错误代码拦截 >= 95% | Mock LLM: Coder→Reviewer 否决→Coder 修改→通过 |
| 无损交接 | 崩溃恢复状态零丢失 100% | 进程崩溃→看板快照恢复→继续执行 |
| 熔断可靠 | 超过最大轮数一定触发熔断 | Mock LLM: 持续否决→10 轮后熔断 |
| 视口隔离 | 角色视口不包含其他角色内部信号 | Coder 视口不含 Reviewer 内部信号 |
| Codex 权限 | 未授权角色调用被拒绝 | Reviewer 调用 call_codex→拒绝+审计 |
| Codex 产出注入 | Codex 返回值正确解析并注入看板 | Mock Codex: 产出代码→解析为 artifact→注入晶态区候选 |
| 解析容错 | LLM 返回非法 JSON 时不崩溃 | LLM 返回非结构化文本→错误信号回注流态区 |

## 2. 不做什么（Out of Scope）

| 编号 | 排除项 | 原因 |
|------|--------|------|
| OOS-01 | 图形界面（GUI / Web UI） | 系统定位为内核引擎，交互通过 CLI 完成 |
| OOS-02 | 多用户权限系统 | 单机单进程场景，无多用户需求 |
| OOS-03 | 分布式部署 | 明确限定单机单进程，不涉及集群/分片 |
| OOS-04 | IDE 集成（VS Code 插件等） | 独立工具，不依赖特定 IDE |
| OOS-05 | Git 操作封装 | git 操作由 run_shell 工具代理，内核不内置 git 客户端 |
| OOS-06 | 数据库持久化 | 看板快照使用 JSON 文件，不引入数据库依赖 |
| OOS-07 | 容器化 / K8s 部署 | 单机运行，不涉及容器编排 |
| OOS-08 | 插件市场 / 第三方插件加载 | 角色通过工具注册表声明，不做通用插件架构 |
| OOS-09 | 实时协作 / WebSocket 推送 | 单进程内部通信，无需外部推送 |
| OOS-10 | 国际化（i18n） | 系统面向开发者，界面语言为英文 |
| OOS-11 | 性能基准测试 / 压力测试 | 初始阶段不做系统级压测，仅验证核心指标 |
| OOS-12 | 并行驱动循环 | 驱动循环是同步的（一轮接一轮），不做并行调度 |
| OOS-13 | Codex 直接 API 调用 | Codex 接入仅通过 CLI 工具（`codex` 命令），不封装 Codex REST API |
| OOS-14 | 多 LLM 供应商适配（除 Anthropic/Codex 外） | 不做 OpenAI ChatGPT/Google Gemini 等其他适配层 |
| OOS-15 | 引擎对现有模块的重写 | 复用 kanban/message_bus/viewport/valve/registry/process，不重写 |
| OOS-16 | Codex 会话管理 | Codex 调用无状态，不维护 Codex 会话上下文 |

## 3. 技术约束

| 约束 | 值 |
|------|-----|
| 语言 | Python 3.11+ |
| 异步框架 | asyncio |
| LLM SDK | anthropic |
| Codex CLI | openai-codex |
| 序列化 | JSON |
| 测试框架 | pytest |
| CLI 框架 | click |
| 运行模式 | 单机单进程 |
| 驱动循环模式 | 同步（一轮接一轮），非并行 |
| 底座 I/O 原则 | 引擎零 I/O，所有写出通过阀门 |
| Codex 调度机制 | 遵循现有 ToolRegistry 模式，不引入新调度机制 |
| 模块复用 | 不重写 kanban/message_bus/viewport/valve/registry/process |

## 4. 边界条件

| 场景 | 处理方式 |
|------|----------|
| 看板快照损坏 | 启动时校验快照完整性，损坏则拒绝恢复并报错 |
| LLM API 不可用 | 工具调用超时，信号回注流态区，不崩溃 |
| LLM 返回非法 JSON | 作为错误信号回注流态区，不崩溃 |
| 收敛超过最大轮数 | 熔断，输出当前状态，报告人类 |
| Codex CLI 不可用 | CodexAdapter 抛出明确异常，引擎降级为 call_llm 或报告人类 |
| 磁盘空间不足 | 原子写入失败，信号回注流态区 |
| 所有进程同时崩溃 | 从最近有效快照恢复，重新创建全部进程 |
| 信号路由无匹配进程 | 作为错误信号回注流态区，不丢弃 |
| 碰撞收敛中意图信号缺失 | 等待下一轮，不强制收敛 |

## 5. 优先级定义

| 优先级 | 含义 | 交付要求 |
|--------|------|----------|
| P0 | 核心功能，无此不可运行 | 本轮必须包含 |
| P1 | 重要功能，显著提升可用性 | 本轮应包含 |
| P2 | 增强功能，锦上添花 | 后续版本按需加入 |

## 6. 第一轮→第二轮变更摘要

| 变更类型 | 内容 |
|----------|------|
| 新增模块 | 驱动引擎（engine.py） |
| 新增模块 | Codex 工具（tools/call_codex.py） |
| 新增模块 | Codex 适配层（adapters/codex_adapter.py） |
| 修改模块 | CLI 入口（cli/main.py）-- 集成驱动循环 + 新增选项 |
| 修改模块 | Mock 适配器 -- 增强支持结构化 JSON 返回 |
| 修改模块 | ToolRegistry -- 注册 call_codex 工具 |
| 新增需求 | EN-01~EN-09（驱动引擎功能需求） |
| 新增需求 | CX-01~CX-05（Codex 接入功能需求） |
| 新增需求 | LL-04/LL-05（Codex CLI 适配 + Mock 增强） |
| 新增需求 | CLI-04~CLI-07（CLI 新增选项） |
| 新增用户故事 | US-09~US-16（8 个第二轮用户故事） |
| 新增验收标准 | AC-02/AC-04/AC-09~AC-13（7 个第二轮验收标准） |
| 新增非功能需求 | NFR-P05/NFR-S05/NFR-R04/NFR-R05/NFR-C04/NFR-M04 |
