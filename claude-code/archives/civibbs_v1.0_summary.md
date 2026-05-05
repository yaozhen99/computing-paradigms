# CiviBBS v1.0.0 — 项目归档

> 归档时间: 2026-04-21 | 作者: Yao Zhen | GitHub: yaozhen99/civibbs-core (私有库)
> 首版由 Claude Haiku 编写 | 开发周期: 2026年1月-3月
> 本地路径: C:\civibbs-core

## 项目定位

去中心化智能体协作平台。核心理念：通过邮件驱动架构（Mail-Driven Architecture）让多个 AI 智能体异步协作完成复杂任务。

## 架构设计

```
┌──────────────────────────────────────────┐
│         L3 业务流程层 (业务逻辑)          │  ← 未实现
├──────────────────────────────────────────┤
│    L2 流程层 (Sequence/Parallel/...)     │  ← 未实现
├──────────────────────────────────────────┤
│     L1 功能层 (文件/HTTP/JSON/...)       │  ← 未实现
├──────────────────────────────────────────┤
│           流程引擎 (Orchestrator)        │  ← 未实现
├──────────────────────────────────────────┤
│         邮件系统 (Mail & Protocol)       │  ✅ 已实现
├──────────────────────────────────────────┤
│       邮件后端 (FileSystem Backend)      │  ✅ 已实现
└──────────────────────────────────────────┘
```

## 已实现模块 (~35%)

### 邮件协议 (civibbs/core/protocol.py)
- MailType 枚举: COMMAND / DATA / STATUS / RESPONSE / EVENT / WORKFLOW / PLUGIN_REQ / PLUGIN_RESP
- MailStatus 枚举: PENDING / PROCESSING / COMPLETED / FAILED / CANCELLED / RETRY
- MailProtocol 类: 邮件头常量、默认值(优先级5/重试3/TTL 86400s)、路径模板、特殊Agent ID(system/broadcast/scheduler)

### 邮件数据模型 (civibbs/core/mail.py)
- MailMetadata: dataclass — message_id(UUID), timestamp, from_agent, to_agents, cc/bcc, mail_type, status, priority, subject, reply_to, topology_id, workflow_id, plugin_id/version/action, retries, ttl
- Mail: 核心数据结构 — to_dict/to_json/from_dict/from_json, 状态更新, 重试递增, TTL过期检查

### 邮件后端 (civibbs/backends/mail/)
- MailBackend ABC: 7个抽象方法 (initialize/save/load/list/update_status/delete/get_stats/cleanup)
- FileSystemMailBackend: 原子操作(os.rename), 目录结构 {base}/{topology_id}/mailbox/{agent_id}/{msg_id}_{status}.mail

### 配置管理 (civibbs/runtime/config.py)
- Config: YAML/JSON加载, 深度合并, 环境变量覆盖, 点号路径访问, 验证

### 运行时骨架 (civibbs/runtime/main.py)
- CiviBBSRuntime: 初始化流程, 插件/工作流注册, 信号处理 (依赖缺失模块,无法运行)

## 核心缺失

| 缺失模块 | 预期功能 |
|----------|---------|
| civibbs/lib/plugin_base.py | L1/L2/L3 插件基类, PluginMetadata |
| civibbs/lib/loader.py | PluginLoader — 注册/发现/列举/热插拔 |
| civibbs/lib/orchestrator.py | Orchestrator — 工作流注册/执行/调度 |
| 邮件总线投递循环 | pending扫描→分发→执行→回写 |
| Agent 管理 | 注册/发现/收发邮件 |
| 上下文机制 | Agent间对话连续性 |
| HTTP 接口 | config中有定义但无实现 |

## 设计亮点

1. 邮件驱动架构 — 天然异步、可追踪、可重试
2. 原子状态转换 — os.rename() 无锁并发安全
3. 三层插件体系 — L1(原子)→L2(流程)→L3(业务) 分层清晰
4. 拓扑隔离 — topology_id 支持多拓扑独立邮箱空间
5. 变量引用 — ${task.validate.data} 工作流数据传递

## 设计文档 (docs/)

- ARCHITECTURE.md (20KB) — 完整架构设计，总线架构描述
- PLUGIN_DEVELOPMENT.md (24KB) — L1/L2/L3 接口定义
- MAIL_PROTOCOL.md — 投递规则定义
- API_REFERENCE.md — 完整API（大部分未实现）
- QUICK_START.md / DEPLOYMENT.md

## V2.0 推进方向

基于现有邮件协议，优先实现：
1. 邮件总线投递循环 + Agent基类 → 让智能体间能互发邮件
2. 上下文机制 → 对话连续性
3. 插件体系 + 热插拔 → L1/L2/L3 可用
4. 流程引擎 → 工作流编排

本机智能体: 用户 / Atlas / Hermes / Nanobot / Claude Code
