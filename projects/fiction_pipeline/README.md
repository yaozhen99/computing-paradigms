# Fiction Pipeline — 纯文件驱动小说创作流水线

## 概念

借鉴 Ai_develop_os_exc 的核心机制，为小说创作量身设计的多角色协作系统。

**零对话、零 API** — 多个 AI 角色通过文件交接工作，不直接对话。

## 设计原则

- **文件是唯一真相** — 角色间零对话，通过文件交接
- **签字协议** — 每个环节完成后在 lock 文件签字
- **人类圣裁** — 关键节点（世界观、大纲）需人类批准
- **审核否决** — 审稿员只判不改，否决触发返工
- **防御性写入** — 先写 .tmp，自检后覆盖
- **熔断** — 连续否决 3 次等人类介入

## 流水线

```
worldbuilder → [人类批准] → outliner → [人类批准] → chapter_planner → writer → editor → finalizer
```

## 岗位

| 编号 | 角色 | 职责 | 人类圣裁 |
|:---|:---|:---|:---|
| 00 | 全局 AI | 调度流水线，处理否决和熔断 | 否 |
| 01 | 世界观构建师 | 构建世界观设定 | **是** |
| 02 | 大纲架构师 | 设计故事大纲 | **是** |
| 03 | 章节规划师 | 将大纲拆分为章节 | 否 |
| 04 | 正文撰写师 | 按章节规划撰写正文 | 否 |
| 05 | 审稿修订师 | 审查正文质量 | 否 |
| 06 | 定稿师 | 整合全稿，产出终稿 | 否 |

## 审稿否决 → 返工

- 世界观矛盾 → 回退到 worldbuilder
- 大纲偏离 → 回退到 outliner
- 章节规划问题 → 回退到 chapter_planner
- 正文质量问题 → 回退到 writer（抛弃半成品，从零重写该章）

## 目录结构

```
fiction_pipeline/
├── README.md
├── 00_story_master/                 # 故事师
│   ├── prompt.md
│   ├── manifest.json
│   ├── worldbuilding_guide.md
│   └── user_inputs/
├── agent_protocol/                  # 岗位模板库
│   ├── _shared/
│   │   └── node_protocol.md
│   ├── 00_global_manager/
│   ├── 01_worldbuilder/
│   ├── 02_outliner/
│   ├── 03_chapter_planner/
│   ├── 04_writer/
│   ├── 05_editor/
│   └── 06_finalizer/
└── v2_draft/
```
