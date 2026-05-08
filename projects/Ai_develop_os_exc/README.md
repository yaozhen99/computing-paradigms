# Ai_develop_os — 纯文件驱动 AI 操作系统

## 这是什么

一个零对话、零API、纯文件管道驱动的多AI协作开发系统。人类提需求，需求写手精炼需求，任务师铸造世界，全局AI守护流水线，13个岗位节点各司其职，全部通过文件交接。

## 快速开始

### 方式一：从需求开始（完整流程）

1. 打开一个 AI 窗口，指向 `00_requirement_writer/` 目录
2. 告诉 AI："你是需求写手，读取本目录下 prompt.md 并执行"
3. 在 `00_requirement_writer/user_inputs/` 中填写项目需求（或让需求写手帮你写）
4. 需求写手产出需求文档后，自动复制到 `01_task_master/user_inputs/`
5. 打开另一个 AI 窗口，指向 `01_task_master/` 目录
6. 告诉 AI："你是任务师，读取本目录下 prompt.md 并执行"

### 方式二：直接铸造（已有需求文档）

1. 将需求文档放入 `01_task_master/user_inputs/`，命名格式：`{项目名}_r{N}.md`
2. 打开一个 AI 窗口，指向 `01_task_master/` 目录
3. 告诉 AI："你是任务师，读取本目录下 prompt.md 并执行"
4. 任务师输出技术选型提案后暂停，等待你亲手创建 `approved_tech_stack.json`
5. 批准后任务师铸造整个工作区，全局AI接管流水线

## 角色→目录映射

| 角色 | 目录 | 职责文件 | 输入目录 | 输出目录 |
|:---|:---|:---|:---|:---|
| 需求写手 | `00_requirement_writer/` | `prompt.md` | `user_inputs/` | `user_inputs/` + `01_task_master/user_inputs/` |
| 任务师 | `01_task_master/` | `prompt.md` | `user_inputs/` | `$PROJECT_SPACE/` 整个目录树 |

任务师铸造完成后，各岗位角色在 `$PROJECT_SPACE/` 下工作，由全局 AI 调度。

## 目录结构

```
Ai_develop_os/
├── 00_requirement_writer/        # 需求写手（将模糊想法转化为精确需求文档）
│   ├── prompt.md                 # 执行流程指令
│   ├── manifest.json             # 角色声明
│   └── user_inputs/              # 需求文档存放处（命名：{项目名}_r{N}.md）
├── 01_task_master/               # 任务师（将需求转化为可执行的流水线世界）
│   ├── prompt.md                 # 铸造协议指令
│   ├── architecture_guide.md     # 架构规则操作手册
│   ├── role_templates_guide.md   # 岗位模板规格手册
│   ├── manifest.json             # 角色声明
│   └── user_inputs/              # 需求文档输入（由需求写手复制过来）
├── agent_protocol/               # 岗位模板库 + 共享层
│   ├── v2_agent/                 # V2 Agent 模式（Claude 单会话调度）
│   │   ├── _shared/              # 共享层（node_protocol、hooks）
│   │   ├── 00_global_manager/    # 全局 AI
│   │   ├── 01_pm ~ 14_release/   # 14个岗位模板（各含 prompt.md）
│   │   └── README.md
│   ├── v2_isa/                   # V2 ISA 模式（混合 AI 平台并行执行）
│   │   ├── _shared/              # 共享层（AGENTS.md、CLAUDE.md、_isa/ 工具）
│   │   ├── 00_global_manager/    # 全局 AI
│   │   ├── 01_pm ~ 14_release/   # 14个岗位模板（各含 prompt.md）
│   │   └── README.md
│   └── README.md
├── v2_draft/                     # 协议设计草稿
├── 纯文件驱动 AI 操作系统架构 V1.0 (最终版).md   # 原始设计文档
└── 为全套开发岗位定制的 AI 定义与 Prompt 模板.md  # 原始设计文档
```

## 核心机制

| 机制 | 说明 |
|:---|:---|
| 纯文件管道 | AI之间零对话，所有通信通过 _pipes/ 下的 lock 文件 |
| 人类圣裁 | 任务师提案后暂停，人类必须亲手批准才能进入创世 |
| 心跳斩首 | 节点超时15分钟，全局AI执行 kill -9 |
| 影子写入 | 先写 .tmp，自检后覆盖，防止半成品污染 |
| 审核否决 | 审核员只判不改，否决时生成 override 令触发返工 |
| 熔断保护 | 连续失败3次停止重启，标红等待人类介入 |
| 双写交接 | 需求写手产出必须同时存入 `00_requirement_writer/user_inputs/` 和 `01_task_master/user_inputs/` |

## 岗位流水线

```
PM → 架构师 → DBA + UIUX → 后端 + 前端 → 运维 + 测试编写 → 测试执行 + 安全审计 → 审核员 → 文档 → 发布
```

任务师可根据项目规模裁剪岗位和调整流转顺序。

## 需求文档命名规范

- 格式：`{项目名}_r{轮次号}.md`
- 示例：`statekanban_r7.md`
- 需求写手产出后，必须同时存放在两个位置（内容完全一致）：
  - `00_requirement_writer/user_inputs/{项目名}_r{N}.md`
  - `01_task_master/user_inputs/{项目名}_r{N}.md`

## 设计文档

- `纯文件驱动 AI 操作系统架构 V1.0 (最终版).md` — 系统完整架构定义
- `为全套开发岗位定制的 AI 定义与 Prompt 模板.md` — 14个岗位的原始 Prompt 设计
- `00_requirement_writer/prompt.md` — 需求写手执行流程指令
- `01_task_master/prompt.md` — 任务师铸造协议指令
- `01_task_master/architecture_guide.md` — 从架构文档提炼的任务师操作手册
- `01_task_master/role_templates_guide.md` — 从岗位模板提炼的规格手册