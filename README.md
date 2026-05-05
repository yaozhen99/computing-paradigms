# Tower of Babel — Atlas 的巴比伦塔

> **"来吧，我们建造一座城和一座塔，塔顶通天，为要传扬我们的名。"**

## 这是什么

Tower of Babel 是我们团队（Tony、Atlas、Claude Code、NanoBot）的共享工作空间。
它是一个临时的、基于文件系统的协作基础设施。

**当 CiviBBS 引擎正式运行后，这套架构将迁移到邮件总线上。**
我们就是 CiviBBS 的第一个用户——用自己的项目验证自己的设计。

## 目录结构

```
C:\tower-of-babel\
│
├── atlas\                  ← Atlas 的一级目录
│   ├── tasks\              # 任务管理
│   ├── logs\               # 工作日志
│   ├── design\             # 设计文档
│   └── reviews\            # 评审记录
│
├── claude-code\            ← Claude Code 的一级目录
│   ├── tasks\              # 接收的任务
│   └── logs\               # 开发日志
│
├── nanobot\                ← NanoBot 的一级目录
│   ├── tasks\
│   └── logs\
│
├── tony\                   ← Tony 的一级目录
│   ├── tasks\              # Tony 的待办
│   └── logs\               # Tony 的记录
│
├── public\                 ← 公共目录（所有人周知）
│   ├── policies\           # 制度文件
│   ├── announcements\      # 公告
│   ├── staging\            # 临时文件交换
│   │   ├── incoming\       #   给所有人的文件
│   │   └── outgoing\       #   产出文件
│   └── meeting-notes\      # 会议纪要/重要对话记录
│
├── projects\               ← 项目归档
│   ├── netdef\             # Netdef 项目
│   │   ├── releases\
│   │   └── dev-docs\
│   └── civibbs\            # CiviBBS 项目
│       ├── releases\
│       └── dev-docs\
│
└── chronicle\              ← 编年史（最重要的对话和决策记录）
```

## 核心规则

### 1. 每个智能体的一级目录是自己的领地

- 自己的目录自己管，别人可以读，写之前先声明
- 跨目录写文件 = 发邮件，必须遵循格式

### 2. public 是所有人必须关注的

- `policies/` — 制度变更，所有人必须阅读
- `announcements/` — 公告，所有人必须知晓
- `staging/` — 临时文件交换，不过夜
- `meeting-notes/` — 重要对话记录

### 3. chronicle 是编年史

- 记录最重要的对话、决策、突破性时刻
- 只记录真正有价值的内容，不是流水账
- 这是团队的记忆，比任何单个智能体的日志都重要

### 4. 迁移路径

```
现在：文件系统（Tower of Babel）
  ↓ CiviBBS 引擎就绪
未来：邮件总线（CiviBBS Mail Bus）
```

迁移时，每个目录对应一个智能体的收件箱，
public 对应公共讨论区，
chronicle 对应归档区。
结构一一对应，无缝迁移。

## 命名由来

Tony 说："就叫 Atlas 的巴比伦塔。"

巴比伦塔是人类协作的象征——不同语言的人共同建造。
我们的塔也是：不同智能体（人、AI、小模型）共同建造。
不同的是，我们的塔不会因为语言不通而停工——
因为我们正在建造的 CiviBBS，就是解决这个问题的。

---

*创建日期：2026-04-21*
*命名者：Tony*
*建造者：Atlas 🏛️*
