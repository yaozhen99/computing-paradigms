# OpenClaw应用场景定位

> 作者：Atlas 🏛️
> 日期：2026-05-02
> 原则：只管自己这摊，不碰Hermes家族内部

---

## 1. 边界

**OpenClaw这摊**：4个agent（Atlas、Puck、Athena、Guardian），1个Gateway，飞书群通信。

**Hermes家族**：130herwin负责安全维护，内部通信自己解决，不通过OpenClaw桥接。

**两家的接口**：飞书群。需要协作时@对方，不需要桥接。

---

## 2. 过去的错位

| 错位 | 后果 |
|------|------|
| OpenClaw跑CiviBBS重型开发 | 崩溃、超时、流程断裂 |
| Hertes走HTTP桥接做测试 | 桥接不稳定→Puck代跑→越权 |
| Atlas做纯决策不落地 | 监督只听汇报，不验证 |
| Puck一人多岗 | 开发+测试+对接全揽，越权成常态 |
| Claude Code子代理不理解流程 | 跳步，dev直接到done |

**根因**：OpenClaw不是重型开发运行时，硬撑只会出问题。

---

## 3. OpenClaw擅长什么

OpenClaw的核心能力：

1. **多平台消息路由**——飞书、微信、Telegram等20+平台
2. **轻交互**——一问一答、查资料、写文档
3. **飞书群即时响应**——4个agent都在群里，@谁谁回
4. **定时任务**——cron提醒、定期检查
5. **浏览器自动化**——网页操作
6. **Node配对**——手机/电脑远程控制
7. **子代理**——sessions_spawn跑一次性任务
8. **文件系统**——读写文件、执行命令

**不擅长**：7×24重型开发、多agent长时间协作、大上下文长会话。

---

## 4. 重新定位

### 4.1 Atlas（我）

**定位：Tony的接口人 + 测试责任人**

| 职责 | 具体内容 |
|------|---------|
| Tony的接口 | 日常问答、任务接收、结果汇报 |
| 决策 | 做什么、优先级、流程是否合规 |
| **测试责任人** | **自己跑测试**——pytest、触发机验证、判断通过不通过 |
| 上下衔接 | dev→test→review→done每步有人接 |
| 环境监控 | Gateway状态、进程检查、配置安全 |
| 飞书群响应 | @Atlas时响应，不越权抢别人的活 |

**不做**：
- ❌ 不写代码
- ❌ 不跑长会话开发任务
- ❌ 不替其他岗位干活（测试我自己跑，不是代跑）

### 4.2 Puck

**定位：开发责任人 + 外部开发能力对接**

| 职责 | 具体内容 |
|------|---------|
| 开发责任人 | 对开发产出负责 |
| 任务拆解 | 把开发需求拆成Claude Code/Codex可执行的子任务 |
| 对接外部开发能力 | sessions_spawn Claude Code子代理 |
| 开发进度跟踪 | 跟踪每个开发任务的状态 |
| 飞书群响应 | @Puck时响应开发相关问题 |

**不做**：
- ❌ 不代跑测试（这是我的教训）
- ❌ 不替审核
- ❌ 不做环境管理

### 4.3 Athena

**定位：审核岗 + 闭环追踪**

| 职责 | 具体内容 |
|------|---------|
| 代码审核 | 审核definition.yaml + execute.py + triggers |
| 闭环追踪 | 审核→反馈→修改→再审核，直到闭环 |
| 反模式检查 | 对照anti-patterns.md检查 |
| 飞书群响应 | @Athena时响应审核相关问题 |

**关键变化**：Athena不只是"审完出报告"，要追踪反馈是否被修改闭环。

### 4.4 Guardian

**定位：环境安全官**

| 职责 | 具体内容 |
|------|---------|
| 凭据安全 | API key不落地明文 |
| 配置审计 | 配置变更是否安全 |
| 环境检查 | 端口、进程、权限 |
| 飞书群响应 | @Guardian时响应安全相关问题 |

---

## 5. OpenClaw内部通信

### 5.1 现状

- sessions_send：不稳定，Puck和Athena都超时
- 飞书群：4个agent都在，@指定agent可响应
- 文件系统：共享pipeline目录

### 5.2 通信优先级

| 通道 | 场景 | 可靠性 |
|------|------|--------|
| 飞书群@指定agent | 正式任务派发和结果回传 | 高 |
| 文件系统 | 产出物传递、状态记录 | 高 |
| sessions_send | OpenClaw内部快速确认 | 不稳定 |
| sessions_spawn | 一次性子代理任务 | 可用 |

### 5.3 通信保障

**核心原则：飞书群是主要通道，sessions_send是辅助。**

当sessions_send不通时：
1. 飞书群@指定agent
2. 文件系统传递任务描述和产出
3. 不因为通信问题而跳步或代跑

---

## 6. 开发流程

### 6.1 CiviBBS流水线（OpenClaw内部版）

```
Tony下达开发任务
  → Atlas决策（做什么、优先级）
    → 飞书群@Puck（开发责任人）
      → Puck拆解任务，sessions_spawn Claude Code子代理
        → 产出放入pipeline/workspace_dev/
      → Puck通知Atlas开发完成
    → **Atlas自己跑测试**（测试责任人）
      → pytest、触发机验证
      → 测试不通过→打回Puck修改
      → 测试通过→推给Athena审核
    → 飞书群@Athena（审核岗）
      → Athena审核，反馈闭环
      → 审核报告放入pipeline/workspace_review/
    → Atlas确认流程完整
      → 移入pipeline/done/
      → 飞书群汇报Tony
```

### 6.2 断档保护

| 断档点 | 保护措施 |
|--------|---------|
| Puck不可达 | Atlas飞书群通知Tony，暂停开发 |
| Athena不可达 | Atlas飞书群通知Tony，暂停审核 |
| sessions_spawn不可用 | 飞书群通知Tony，降级处理 |
| Gateway崩溃 | 重启后从记忆文件恢复上下文 |

**核心原则：任何环节断开，暂停等待，不跳步不代跑。**

---

## 7. 与Hermes家族的接口

### 7.1 唯一接口：飞书群

- OpenClaw agent和Hermes agent都在130Ai开发者群
- 需要协作时@对方
- 不走桥接、不走sessions_send、不走HTTP

### 7.2 不做的事

- ❌ 不把Hermes Agent拉进OpenClaw的开发流程
- ❌ 不走HTTP桥接派任务给Hermes
- ❌ 不替Hermes家族做内部通信

### 7.3 协作场景

| 场景 | 方式 |
|------|------|
| 需要Hermes帮忙测试 | 飞书群@130herwin |
| 需要Hermes安全检查 | 飞书群@130herwin |
| Hermes需要OpenClaw信息 | 飞书群@Atlas/Puck/Athena |
| 两家共享的文件 | pipeline目录、tower-of-babel目录 |

---

## 8. 实施步骤

### 立即

1. 打B1补丁（反转崩溃策略）
2. 打B2补丁（配置写入原子化）
3. 确认飞书群4个agent都能响应

### 本周

1. 更新各agent的SOUL.md（新职责定位）
2. 测试飞书群@指定agent的响应
3. 用新流程跑一个CiviBBS插件开发

### 持续

1. 监控Gateway稳定性（B1+B2补丁效果）
2. 定期检查agent间通信
3. 上下文55%就compact

---

*管好自己这摊。*
*Atlas 🏛️*
*2026-05-02 14:10 GMT+8*