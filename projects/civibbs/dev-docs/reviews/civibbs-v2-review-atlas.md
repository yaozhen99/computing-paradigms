# CiviBBS v2.0 技术审阅报告

> 审阅者：Atlas（基于代码阅读）
> 日期：2026-04-21
> 任务编号：T-CB-001

---

## 一、核心架构设计

CiviBBS v2.0 是一个**邮件驱动的去中心化智能体协作平台**。核心理念：所有通信都是邮件，文件系统就是消息队列。

### 架构分层

```
L3 协作体系 (7个YAML流程)    ← 业务编排层
    ↓ 调用
L2 流程插件 (6种执行模式)    ← 控制流层
    ↓ 调用
L1 功能插件 (59个YAML定义)   ← 原子操作层
```

**关键设计**：
- 引擎（Orchestrator）解析YAML流程定义，按步骤调度L1/L2插件
- 插件通过 loader.py 动态加载，YAML定义接口，Python实现逻辑
- 零外部依赖——纯Python标准库 + 文件系统

### 核心模块

| 模块 | 行数 | 职责 |
|------|------|------|
| orchestrator.py | 303 | 流程引擎：解析YAML，执行7种步骤类型 |
| mail_manager.py | 145 | 邮件CRUD：创建/投递/读取/线程管理 |
| loader.py | 64 | 插件加载：动态发现和注册L1/L2插件 |
| topology.py | 134 | 拓扑管理：智能体注册/心跳/拓扑存储 |
| ai_model.py | 348 | AI模型：DeepSeek/星火/多模型路由 |
| app.py | 591 | Web服务：Flask BBS/聊天/拓扑/API |
| ac_scheduler.py | 354 | AC调度：任务拆解/分发（开发中） |

---

## 二、邮件总线实现分析

### 设计标准（docs/core/core_mail_format_standard.md）

上一个AI已经定义了完整的邮件格式标准：

```json
{
  "msg_id": "uuid-v4",
  "from": "sender_id",
  "to": "receiver_id | group_id | public",
  "type": "task | result | progress | register | ping | pong | shutdown | cancel | topology_data",
  "content": "...",
  "context": {
    "task_type": "general | code_edit | file_operation | message_processing",
    "priority": "low | normal | high | urgent",
    "deadline": "ISO8601",
    "requirements": [],
    "agent_type": "trae | cursor | web | bbs | dispatcher",
    "capabilities": [],
    "workspace": "...",
    "file_tree": "..."
  },
  "topology": { "storage": [...], "units": [...] },
  "timestamp": "ISO8601",
  "expires": null,
  "completed": false
}
```

**设计标准已存在，但代码未实现。** 这是最大的差距——标准写好了，代码没跟上。

### 当前实现（mail_manager.py）

```python
# 只实现了基础字段
- create_mail(from, to, subject, body, thread_id, in_reply_to)
- deliver_mail(mail, agent_id)
- read_inbox(agent_id)
- load_thread(thread_id)
```

**通信模型**：
```
用户发消息 → 写入用户outbox → 移动到AI inbox → AI读取+加载上下文 → AI回复 → 移动到用户inbox
```

**原子操作**：使用 `os.rename()` 实现文件移动的原子性，避免读写竞争。

### 差距对照

| 设计要求 | 当前状态 | 差距 |
|---------|---------|------|
| msg_id, from, to, thread_id, in_reply_to | ✅ 已实现 | - |
| type (task/result/ping/pong/register/shutdown) | ❌ 缺失 | 邮件无类型区分 |
| context (task_type, priority, deadline, requirements) | ❌ 缺失 | 无任务上下文 |
| topology (storage, units) | ❌ 缺失 | 无拓扑信息 |
| expires, completed | ❌ 缺失 | 无生命周期管理 |

**核心差距**：设计标准已完备，代码实现滞后。邮件只有"对话"语义，缺少"任务"语义。

---

## 三、插件体系结构

### L1 功能插件（59个YAML定义）

```
lib/small/
├── fs/   (文件操作 10个)  — read_file, write_file, atomic_write, ...
├── cf/   (配置验证 2个)   — validate_config, load_schema
├── lg/   (日志 3个)       — write_log, read_log, rotate_log
├── ml/   (邮件操作 8个)   — create_mail, deliver_mail, read_inbox, ...
├── pt/   (进程线程 18个)  — spawn_process, wait_process, ...
├── bb/   (BBS操作 3个)    — create_discussion, list_threads, ...
└── dt/   (数据转换 7个)   — parse_json, format_yaml, ...
```

**问题**：59个YAML定义了接口，但缺少配套的**触发机**（自测用例）。没有触发机，插件无法独立验证。

### L2 流程插件（6种执行模式）

| 模式 | 实现 | 说明 |
|------|------|------|
| sequence | ✅ | 顺序执行 |
| parallel | ✅ | ThreadPoolExecutor并行 |
| condition | ✅ | 条件分支 |
| for | ✅ | 数组遍历循环 |
| loop | ✅ | while循环 |
| retry | ✅ | 重试+退避 |
| race | ✅ | 竞争执行 |

### L3 协作体系（7个YAML流程）

system_init / mail_bus / topology / bbs_web 等，定义了完整的系统启动和运行流程。

---

## 四、当前差距与优先级

### 高优先级（核心功能缺失）

1. **邮件格式标准** — 缺少 type/context/topology 字段，邮件总线无法驱动任务
2. **触发机系统** — 59个L1插件无法自测，质量无保证
3. **AC调度器** — 无任务拆解和超时重发，复杂任务无法自动编排
4. **Git仓库初始化** — 代码未版本管理，无法协作开发

### 中优先级（功能增强）

5. **邮件总线监听** — 无watchdog，邮件到达无通知（轮询方式效率低）
6. **拓扑单元进程** — 无独立进程和心跳，智能体无法真正"在线"
7. **智能体适配器** — adapters/ 未接入邮件协议，Trae/Cursor等无法通信

### 低优先级（远期目标）

8. 流程定义验证
9. 模型微调闭环

---

## 五、优先推进方向建议

### 我的判断：邮件格式标准 > 一切

理由：

1. **邮件是CiviBBS的血液**。没有type/context/topology字段，邮件只是"对话记录"，不是"任务指令"。这是从聊天工具到协作平台的质变。

2. **Tower of Babel 就是验证场**。我们现在的文件系统协作（JSON任务文件、日志、staging）就是CiviBBS邮件总线的粗糙原型。如果邮件格式标准化了，Tower of Babel可以直接迁移上去——**我们就是自己的第一个用户**。

3. **触发机依赖邮件格式**。触发机的输入输出需要标准化的邮件格式来描述。先定格式，再写触发机。

### 推荐路径

```
1. 定义邮件格式标准（type/context/topology/expires/completed）
2. 改造 mail_manager.py 支持新格式
3. Tower of Babel 迁移到 CiviBBS 邮件总线
4. 在真实使用中发现问题、迭代格式
5. 为L1插件写触发机（基于标准化的邮件格式）
6. AC调度器（基于标准化的任务邮件）
```

---

## 六、与 Tower of Babel 的对比

| 维度 | Tower of Babel（当前） | CiviBBS 邮件总线（目标） |
|------|----------------------|------------------------|
| 通信方式 | JSON文件 + 目录约定 | 标准化邮件 + os.rename原子操作 |
| 邮件格式 | 自定义JSON（无type/context） | 标准化（type/context/topology） |
| 智能体发现 | 目录名约定 | profile.json + scan_profiles() |
| 任务分发 | 手动写JSON文件 | AC调度器自动拆解分发 |
| 监听 | 无（被动读取） | watchdog/inotify |
| 拓扑 | 无 | topology.py + SVG可视化 |
| 流程引擎 | 无 | orchestrator.py 6种执行模式 |

**核心差距**：Tower of Babel 是"约定"，CiviBBS 是"协议"。从约定到协议，就是迁移的本质。

---

*审阅者：Atlas 🏛️*
*任务编号：T-CB-001*
*日期：2026-04-21*
