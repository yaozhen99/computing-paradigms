# StateKanban R3 测试需求文档

## 版本历史

| 版本 | 轮次 | 日期 | 说明 |
|------|------|------|------|
| v1.0 | R1 | 2025-04-20 | 初始测试需求 |
| v2.0 | R2 | 2025-05-01 | 新增 call_codex、response_parser、CLI 测试 |
| v3.0 | R3 | 2026-05-05 | 端到端验证、snapshot/call_llm/ToolRegistry/新错误码 |

## 1. 测试目标

R3 核心目标：**端到端验证**——证明 StateKanban 从 Coder 发起到晶态固化、阀门写出的完整流程可用，并覆盖碰撞收敛、熔断、视口隔离、快照保存/恢复等关键场景。

## 2. 测试范围

### 2.1 R1/R2 回归（必须 100% 通过）

| 模块 | R1/R2 测试项 |
|------|-------------|
| core/errors | 错误码注册、继承、消息格式 |
| core/kanban | KanbanBoard CRUD、状态转移、并发安全 |
| core/viewport | 视口过滤、字段白名单 |
| core/valve | 阀门写出、去重、幂等 |
| core/audit | 审计日志写入、查询 |
| core/models | 数据模型验证 |
| core/message_bus | 发布订阅、消息路由 |
| adapters/mock_adapter | MockLLMAdapter 结构化/行为模式 |
| engine/engine | Engine tick、prompt 构建 |
| engine/response_parser | 信号解析、错误处理 |
| tools/call_codex | Codex 调用（Windows 容错） |
| CLI | 状态查看、运行命令 |

### 2.2 R3 新增（最高优先级）

#### 2.2.1 端到端测试

| ID | 场景 | 优先级 | 说明 |
|----|------|--------|------|
| E2E-01 | 快乐路径 | P0 | Coder→Reviewer→晶态固化→阀门写出 |
| E2E-02 | 碰撞收敛 | P0 | Coder→Reviewer否决→Coder修改→Reviewer通过 |
| E2E-03 | 熔断 | P0 | 超过最大轮数触发 CircuitBreaker |
| E2E-04 | 视口隔离 | P0 | Coder视口不包含Reviewer内部信号 |
| E2E-05 | 快照保存/恢复后继续 | P1 | 保存→恢复→继续推进到完成 |

#### 2.2.2 Snapshot 模块

| ID | 场景 | 优先级 |
|----|------|--------|
| SNAP-01 | save_snapshot 保存完整状态 | P0 |
| SNAP-02 | load_snapshot 恢复状态 | P0 |
| SNAP-03 | list_snapshots 列出所有快照 | P0 |
| SNAP-04 | delete_snapshot 删除指定快照 | P0 |
| SNAP-05 | 原子写入（临时文件+rename） | P0 |
| SNAP-06 | null bytes 路径校验 | P0 |
| SNAP-07 | load 不存在的快照抛 SK_CX_003 | P0 |
| SNAP-08 | delete 不存在的快照抛 SK_CX_003 | P0 |

#### 2.2.3 MockLLMAdapter

| ID | 场景 | 优先级 |
|----|------|--------|
| MOCK-01 | structured_mode 正常返回 | P0 |
| MOCK-02 | behavior_mode 正常返回 | P0 |
| MOCK-03 | structured_mode 缺少 signal 字段回退 | P1 |
| MOCK-04 | reset() 清除所有状态 | P0 |
| MOCK-05 | behavior_mode 多轮对话 | P1 |

#### 2.2.4 ToolRegistry & Engine 集成

| ID | 场景 | 优先级 |
|----|------|--------|
| TREG-01 | register_tool 注册 | P0 |
| TREG-02 | dispatch 调用注册的工具 | P0 |
| TREG-03 | dispatch 未注册工具抛 SK_TR_004 | P0 |
| TREG-04 | Engine tick 通过 ToolRegistry 分发 | P0 |
| TREG-05 | call_llm 注册到 ToolRegistry | P0 |

#### 2.2.5 call_llm 工具

| ID | 场景 | 优先级 |
|----|------|--------|
| CLLM-01 | 正常调用返回结果 | P0 |
| CLLM-02 | 权限控制（非白名单角色拒绝） | P0 |
| CLLM-03 | 审计日志记录 | P0 |
| CLLM-04 | null bytes 消息内容校验 | P0 |
| CLLM-05 | adapter 不可用抛 SK_CX_003 | P1 |

#### 2.2.6 新错误码

| ID | 场景 | 优先级 |
|----|------|--------|
| ERR-01 | SK_CX_003 ContextSnapshotNotFound | P0 |
| ERR-02 | SK_EN_004 MaxRoundsExceeded | P0 |
| ERR-03 | SK_TR_004 ToolNotFound | P0 |

#### 2.2.7 CLI snapshot 子命令

| ID | 场景 | 优先级 |
|----|------|--------|
| CLI-01 | snapshot save 子命令 | P0 |
| CLI-02 | snapshot load 子命令 | P0 |
| CLI-03 | snapshot list 子命令 | P0 |
| CLI-04 | snapshot delete 子命令 | P0 |

## 3. 论文测试标准

| 指标 | 阈值 | 验证方式 |
|------|------|---------|
| 收敛率 | >= 80% | 100次快乐路径 E2E 运行，统计完成率 |
| 拦截率 | 100% | Reviewer否决必须被拦截，不允许跳过 |
| 无损交接 | 快照恢复后继续完成 | 快照保存→恢复→完成全流程 |

## 4. 测试环境

- Python 3.11+
- Windows 11（需处理路径分隔符差异）
- pytest + pytest-cov
- 无外部 LLM 依赖（MockLLMAdapter）
