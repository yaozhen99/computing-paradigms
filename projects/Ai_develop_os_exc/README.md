# Ai_develop_os — 纯文件驱动 AI 操作系统

## 这是什么

一个零对话、零API、纯文件管道驱动的多AI协作开发系统。人类提需求，任务师铸造世界，全局AI守护流水线，13个岗位节点各司其职，全部通过文件交接。

## 快速开始

1. 打开一个 AI 窗口，指向 `00_task_master/` 目录
2. 在 `00_task_master/user_input.md` 中填写项目需求
3. 告诉 AI："你是任务师，读取本目录下所有文件并执行"
4. 任务师输出技术选型提案后暂停，等待你亲手创建 `approved_tech_stack.json`
5. 批准后任务师铸造整个工作区，全局AI接管流水线

## 目录结构

```
Ai_develop_os/
├── 00_task_master/              # 任务师（独立自包含，打开窗口就能跑）
│   ├── prompt.md                # 执行流程指令
│   ├── architecture_guide.md    # 架构规则操作手册
│   ├── role_templates_guide.md  # 岗位模板规格手册
│   ├── user_input.md           # 人类原始需求（填空式模板）
│   └── manifest.json
├── agent_protocol/              # 岗位模板库 + 共享层
│   ├── _shared/                 # 所有节点共享（底层协议、编码宪法、编码纪律）
│   ├── 00_global_manager/       # 全局 AI（常驻主脑）
│   ├── 01_pm ~ 13_release/      # 13个岗位模板（各含 prompt.md + manifest.json）
│   └── README.md
├── 纯文件驱动 AI 操作系统架构 V1.0 (最终版).md   # 原始设计文档
└── 为全套开发岗位定制的 AI 定义与 Prompt 模板.md  # 原始设计文档
```

## 核心机制

| 机制 | 说明 |
|---|---|
| 纯文件管道 | AI之间零对话，所有通信通过 _pipes/ 下的 lock 文件 |
| 人类圣裁 | 任务师提案后暂停，人类必须亲手批准才能进入创世 |
| 心跳斩首 | 节点超时15分钟，全局AI执行 kill -9 |
| 影子写入 | 先写 .tmp，自检后覆盖，防止半成品污染 |
| 审核否决 | 审核员只判不改，否决时生成 override 令触发返工 |
| 熔断保护 | 连续失败3次停止重启，标红等待人类介入 |

## 岗位流水线

```
PM → 架构师 → DBA + UIUX → 后端 + 前端 → 运维 + 测试编写 → 测试执行 + 安全审计 → 审核员 → 文档 → 发布
```

任务师可根据项目规模裁剪岗位和调整流转顺序。

## 设计文档

- `纯文件驱动 AI 操作系统架构 V1.0 (最终版).md` — 系统完整架构定义
- `为全套开发岗位定制的 AI 定义与 Prompt 模板.md` — 13个岗位的原始 Prompt 设计
- `00_task_master/architecture_guide.md` — 从架构文档提炼的任务师操作手册
- `00_task_master/role_templates_guide.md` — 从岗位模板提炼的规格手册
