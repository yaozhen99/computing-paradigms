# 项目需求：StateKanban 第二轮 — 驱动循环 + Codex 接入

## 项目概述

StateKanban 内核六大模块已实现（kanban/message_bus/viewport/valve/registry/process），3987 行代码，203 项测试全部通过。但 `statekanban run --intent "xxx"` 只做了初始化就停了——没有视口切片→调LLM→信号回传→碰撞收敛→晶态固化→阀门写出的驱动循环。

本轮需求两件事：
1. **补完驱动引擎**：让 run 命令能真正跑起来，自动驱动 Coder→Reviewer→Tester 的碰撞收敛循环
2. **Codex 接入**：注册 call_codex 工具，让 OpenAI Codex 成为引擎的算力单元之一

## 第一部分：驱动引擎（Engine）

### 1. 调度引擎（statekanban/engine.py）

驱动看板上的信号流转循环。每次循环：

1. 从看板流态区读取未处理的意图信号
2. 根据信号类型和目标角色，选择对应进程
3. 视口切片器裁剪上下文（只传该角色该看到的信息）
4. 调用 LLM（通过适配层），传入视口切片
5. 解析 LLM 返回值：
   - 意图信号 → 写回流态区
   - 否决信号 → 写回流态区，触发碰撞
   - 代码片段 → 写入晶态区候选
6. 检测碰撞收敛：流态区同一目标的意图和否决信号是否达成一致
7. 收敛后 → 晶态区固化 → 输出阀门校验 → 物理写出
8. 未收敛 → 下一轮循环

### 2. 碰撞收敛策略

- 同一目标（target_id）的意图信号和否决信号在同一轮中碰撞
- 收敛条件：最新一轮没有新的否决信号，或否决信号被意图信号覆盖
- 最大循环轮数：可配置，默认 10 轮
- 超过最大轮数：熔断，报告人类

### 3. LLM 返回值解析

LLM 返回结构化 JSON：
- `{"type": "intent", "target_id": "...", "payload": {...}}` — 意图信号
- `{"type": "veto", "target_id": "...", "reason": "..."}` — 否决信号
- `{"type": "artifact", "artifact_type": "code", "content": "...", "path": "..."}` — 代码产出

解析失败时作为错误信号回注流态区。

### 4. 角色调度顺序

默认：Coder → Reviewer → Tester → Integrator

每个角色处理完后，下一个角色看到前序角色的产出（通过视口切片）。

### 5. CLI 集成

`statekanban run --intent "xxx"` 现在应该：
- 初始化系统（已有）
- 写入意图信号（已有）
- **启动驱动循环（新增）**
- 循环结束后输出结果摘要

新增选项：
- `--max-rounds N`：最大循环轮数，默认 10
- `--adapter {mock,anthropic,cli,codex}`：LLM 适配层选择，默认 mock
- `--verbose`：输出每轮循环的详细信息

### 6. 测试

- Mock LLM 驱动循环测试：Coder 产出 → Reviewer 通过 → 晶态固化 → 阀门写出
- Mock LLM 碰撞收敛测试：Coder 产出 → Reviewer 否决 → Coder 修改 → Reviewer 通过
- 熔断测试：超过最大轮数后正确熔断
- 视口隔离测试：Coder 的视口不包含 Reviewer 的内部信号

## 第二部分：Codex 接入

### 1. call_codex 工具（statekanban/tools/call_codex.py）

注册到 ToolRegistry，与 call_llm 平级。引擎不关心底层是 Anthropic API 还是 Codex，它只管视口切片→工具调用→信号回传。

工具参数：
- `prompt`：任务描述（由视口切片器生成）
- `context_files`：需要 Codex 读取的文件路径列表
- `output_path`：Codex 产出的目标文件路径
- `max_tokens`：最大产出 token 数

工具权限：
- Coder、Integrator 可调用
- Reviewer、Tester、Architect 不可调用（他们用 call_llm）

### 2. CodexAdapter（statekanban/adapters/codex_adapter.py）

与 AnthropicMessagesAdapter 平级的适配层。

调用方式：
- 通过 OpenAI Codex CLI（`codex` 命令行工具）执行
- 输入：prompt + context files
- 输出：生成的代码片段
- 返回值解析后注入看板

### 3. CLI 集成

新增适配层选项：
- `--adapter {mock,anthropic,cli,codex}`：LLM/Codex 适配层选择

### 4. 测试

- Mock Codex 测试：验证 call_codex 工具注册和权限控制
- Codex 产出注入看板：验证返回值正确解析为意图信号或代码产出
- 权限隔离：Reviewer 调用 call_codex 应被拒绝

## 技术约束

- 驱动循环是同步的（一轮接一轮），不是并行的
- 底座零 I/O 原则不变：引擎不直接写文件，所有写出通过阀门
- 复用现有模块，不重写 kanban/message_bus/viewport/valve/registry/process
- Codex 接入遵循现有 ToolRegistry 模式，不引入新的调度机制

## 项目空间

C:\tower-of-babel\projects\statekanban\

## 交付物

- engine.py（调度引擎）
- tools/call_codex.py（Codex 工具）
- adapters/codex_adapter.py（Codex 适配层）
- 更新后的 cli/main.py（集成驱动循环 + Codex 选项）
- 新增测试用例