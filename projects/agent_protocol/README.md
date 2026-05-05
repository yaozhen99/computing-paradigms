markdown
# AI 协作外骨骼协议 (Agent Protocol)

本仓库提供一套**模型无关的、基于自然语言的 AI 协作行为协议**。通过一键脚本，你可以将这套“外骨骼”部署到任何项目中，让 AI 助手自动遵守文档纪律、保持上下文连续、并具备自我演化能力。

## 快速开始

### 1. 克隆本仓库
```bash
git clone <your-repo-url> agent_protocol
cd agent_protocol
2. 运行安装脚本
bash
chmod +x bin/install.sh
./bin/install.sh /path/to/your/project
将 /path/to/your/project 替换为你的目标项目根目录。

3. 进入项目并开始协作
bash
cd /path/to/your/project
# 启动 Claude Code 或任何支持自动读取 AGENTS.md 的工具
AI 助手将自动读取协议，并按照你定义的纪律工作。

脚本做了什么？
在目标项目根目录创建 AGENTS.md（行为协议主文件）。

创建 docs/ 目录，包含：

templates/ —— 所有过程文档的格式模板。

skills/ —— 项目专属技能与通用技能沉淀位置。

requirements/、plans/、notes/、summaries/、reviews/ —— 各阶段文档存放位置。

在 tests/ 目录下创建测试文档结构。

为每个一级、二级子目录生成 README.md 自描述文件。

处理已存在文件时的冲突（提示跳过/覆盖/备份）。

协议核心
人定义规则，AI 在规则内执行。

一次写入，终身无需重复沟通。

支持跨模型（Claude、GLM、DeepSeek、Gemini 等）。

内置自我演化机制：AI 会对比计划与实际的差异，沉淀经验，并主动建议优化协议本身。

目录结构
text
agent_protocol/
├── bin/
│   └── install.sh          # 安装脚本
├── templates/              # 所有模板文件（将被复制到目标项目）
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   ├── docs/
│   │   ├── templates/
│   │   │   ├── README.md
│   │   │   ├── requirement.md
│   │   │   ├── plan.md
│   │   │   ├── dev_note.md
│   │   │   ├── dev_summary.md
│   │   │   ├── test_req.md
│   │   │   ├── test_plan.md
│   │   │   ├── test_process.md
│   │   │   ├── test_summary.md
│   │   │   ├── review.md
│   │   │   ├── project_skill.md
│   │   │   ├── general_skill.md
│   │   │   └── dir_readme.md
│   │   ├── skills/
│   │   │   ├── project_specific.md
│   │   │   └── general_patterns.md
│   │   ├── requirements/
│   │   ├── plans/
│   │   ├── notes/
│   │   ├── summaries/
│   │   └── reviews/
│   └── tests/
│       └── README.md
└── README.md               # 本文件
协议版本与更新
本协议遵循语义化版本。你可以在 AGENTS.md 顶部查看当前版本和变更日志。当协议演化时，更新 templates/ 下的文件，然后重新运行安装脚本即可升级目标项目（注意处理冲突）。