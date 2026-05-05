# agent_protocol

**最后更新**：2026-04-23 00:00

## 用途
会话生命周期与自我演化协议项目，定义 AI 助手必须遵守的行为纪律、文档产生规则与自我演化机制。可将本文件包整体拷贝至任意项目根目录，即可为该项目注入完整的协议治理框架。

## 目录结构
项目根目录/
├── AGENTS.md # 行为协议主文件（AI 启动时首先读取，含版本与变更日志）
├── CLAUDE.md # Claude Code 专用自动执行指令（通过 @AGENTS.md 引用主协议）
├── readme_agent.md # 协议框架自述文件（区别于项目本身的 README.md）
├── docs/
│ ├── README.md # docs 目录自描述
│ ├── templates/ # 文档格式模板（AI 生成文档时必须遵循）
│ │ ├── README.md # 模板清单与使用说明
│ │ ├── requirement.md # 需求文档模板
│ │ ├── plan.md # 计划文档模板
│ │ ├── dev_note.md # 开发笔记模板
│ │ ├── dev_summary.md # 开发总结模板（含差异分析）
│ │ ├── test_req.md # 测试需求模板
│ │ ├── test_plan.md # 测试计划模板
│ │ ├── test_process.md # 测试过程记录模板
│ │ ├── test_summary.md # 测试总结模板
│ │ ├── review.md # 代码审核报告模板
│ │ ├── project_skill.md # 项目专属技能模板
│ │ ├── general_skill.md # 通用技能模板
│ │ └── dir_readme.md # 目录级 README 模板
│ ├── requirements/ # 需求文档（按需生成）
│ │ └── README.md
│ ├── plans/ # 计划文档（按需生成）
│ │ └── README.md
│ ├── notes/ # 开发笔记（按需生成）
│ │ └── README.md
│ ├── summaries/ # 开发总结（按需生成）
│ │ └── README.md
│ ├── reviews/ # 审核报告（按需生成）
│ │ └── README.md
│ ├── proposals/ # 协议修正建议（按需生成）
│ │ └── README.md
│ └── skills/ # 技能文档（持续沉淀）
│ ├── README.md
│ ├── project_specific.md # 项目专属技能库
│ └── general_patterns.md # 通用技能模式库
└── tests/ # 测试文档（按模块生成）
└── README.md

text

## 拷贝指引

将本文件包整体拷贝至目标项目根目录即可生效：

```bash
# 示例：拷贝至 my_project 项目
xcopy /E /I C:\agent_protocol\* D:\my_project\
拷贝后需确认：

AGENTS.md 与 CLAUDE.md 位于目标项目根目录

docs/ 目录结构完整

AI 助手启动时会自动读取 AGENTS.md 并按协议执行

对外接口
本项目为协议规范项目，不暴露编程接口

依赖
外部依赖：无

内部依赖：无

约定与规范
AGENTS.md 自身具备版本号与变更日志，由项目管理者（人）负责维护。

所有文档生成必须遵循 docs/templates/ 下对应模板的格式要求。

项目根目录下 readme_agent.md 为协议框架自述文件，各子目录下必须存在 README.md 文件。

对目录下任何代码进行修改后，必须同步更新该目录的 README.md。

AI 不得直接修改 AGENTS.md 或模板文件，修改建议须提交至 docs/proposals/。

发送 @protocol 可触发 AI 立即重新读取协议全文并修正后续行为。

更新记录
2026-04-23 00:00：新增完整目录结构图与拷贝指引；新增 docs/proposals/ 目录；明确 CLAUDE.md 作用与 AGENTS.md 版本管理机制。

2026-04-23 00:00：根据协议规范初始化项目目录结构和文档模板。