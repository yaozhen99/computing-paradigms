# Fiction Pipeline v1.2

长篇小说多智能体协作流水线。每个岗位一个 AI 窗口，独立工作，通过文件和锁协调。

本仓库是空模板，不含任何具体小说项目。

## 必读文件

按顺序阅读：

1. `PIPELINE_SPEC.md`
2. `WINDOW_WORKSPACE_SPEC.md`
3. `MODEL_PROFILES.md`
4. `00_story_master/prompt.md`
5. `00_story_master/manifest.json`
6. `agent_protocol/_shared/node_protocol.md`
7. 你要运行的岗位 prompt（`agent_protocol/<stage>/prompt.md`）

## 快速开始

```bash
# 1. 创建项目（在 00_story_master/ 下准备需求文档）
#    或直接让 story_master AI 与你对话生成

# 2. 启动 Dashboard 监控
python dashboard.py
# 打开 http://localhost:8420

# 3. 一键拉起所有岗位窗口
python launch.py

# 4. 或只拉起部分岗位
python launch.py --stages 5 6 7
```

## 目录结构

```
fiction_pipeline_v1.2/
  00_story_master/          # 需求入口
    prompt.md               # 需求对话 AI 的 prompt
    manifest.json           # 需求阶段配置
    user_inputs/            # 用户需求文档存放处
  agent_protocol/           # 各岗位 prompt 定义
    00_global_manager/
    01_story_bible/
    02_voice_anchor/
    03_rolling_outline/
    04_chapter_brief/
    05_lead_writer/
    06_style_editor/
    07_continuity_editor/
    08_revision_lead/
    09_chapter_freezer/
    _shared/
      node_protocol.md      # 岗位间通信协议
  workspace/                # 项目实例（运行时数据）
    <project>/
      _system/              # 项目状态与规范
        system_state.json   # 当前阶段、章节进度、审批记录
        stage_manifest.json # 各岗位的读写文件流契约
        project_canon.md    # 小说核心设定（世界观、人物、规则）
      _pipes/               # 锁文件（岗位间协调）
        lock_*.json
      _logs/                # 执行日志
      _shared/              # 跨岗位共享数据
      01_story_bible/       # 各岗位工作目录
      02_voice_anchor/
      03_rolling_outline/
      04_chapter_briefs/
      05_draft_chapters/
      06_frozen_chapters/
      07_continuity/
      08_style_reports/
      09_revision_notes/
  dashboard/                # Dashboard 前端
    index.html
    style.css
    app.js
  dashboard.py              # Dashboard 后端
  launch.py                 # 一键拉窗口脚本
  launch_config.json        # 岗位启动配置
  templates/                # 项目创建模板
    stage_manifest.template.json
    stage_readmes/
      README_TEMPLATE.md
```

## 流水线流程

### 基础阶段（一次性）

```
story_bible → voice_anchor → rolling_outline
```

- **story_bible**：从需求生成故事圣经（世界观、人物、设定）
- **voice_anchor**：确定叙事声音，产出 voice bible 和样本章节
- **rolling_outline**：滚动大纲，规划全书章节走向

### 逐章阶段（循环）

```
chapter_brief → lead_writer → style_editor + continuity_editor → revision_lead → chapter_freezer → 下一章
```

- **chapter_brief**：当前章节的写作简报
- **lead_writer**：起草章节正文
- **style_editor**：风格审校报告（不修改正文）
- **continuity_editor**：连续性审校报告（不修改正文）
- **revision_lead**：综合两份审校意见，修订正文
- **chapter_freezer**：冻结定稿，更新状态，推进到下一章

style_editor 和 continuity_editor 可并行运行。revision_lead 等两者都完成后再执行。

## 一键启动（launch.py）

### 基本用法

```bash
python launch.py --list              # 预览所有岗位状态
python launch.py                      # 启动全部岗位窗口
python launch.py --stages 5 6 7       # 只启动第5、6、7号岗位
python launch.py --stages lead        # 按名称前缀匹配
python launch.py --project my_novel   # 指定项目名
```

### 岗位配置（launch_config.json）

每个岗位可独立配置 AI 工具、模型和推理深度：

```json
{
  "stage": "lead_writer",
  "tool": "claude",
  "model": "opus",
  "effort": "high",
  "directory": "05_draft_chapters",
  "prompt_file": "agent_protocol/05_lead_writer/prompt.md"
}
```

| 字段 | 说明 | 可选值 |
|------|------|--------|
| `tool` | AI CLI 工具 | `claude` / `codex` / `opencode` |
| `model` | 模型 | `opus` / `sonnet` / `haiku` 等 |
| `effort` | 推理深度 | `low` / `medium` / `high` / `max` |
| `directory` | 工作目录（workspace 下相对路径） | — |
| `prompt_file` | 岗位 prompt 文件（项目根下相对路径） | — |

### 默认岗位配置

| # | 岗位 | tool | model | effort | 理由 |
|---|------|------|-------|--------|------|
| 1 | story_bible | claude | sonnet | high | 规划型，需深度思考 |
| 2 | voice_anchor | claude | sonnet | high | 风格锚定，需精细 |
| 3 | rolling_outline | claude | sonnet | high | 大纲规划 |
| 4 | chapter_brief | claude | sonnet | high | 简报生成 |
| 5 | lead_writer | claude | opus | high | 核心创作，最强模型 |
| 6 | style_editor | claude | sonnet | medium | 审校报告，中等即可 |
| 7 | continuity_editor | claude | sonnet | medium | 审校报告 |
| 8 | revision_lead | claude | opus | high | 修订决策，需强模型 |
| 9 | chapter_freezer | claude | haiku | low | 机械操作，轻量即可 |

## Dashboard（dashboard.py）

只读 Web 看板，实时查看项目进展。

```bash
python dashboard.py
# 打开 http://localhost:8420
```

### API 端点

| 端点 | 说明 |
|------|------|
| `/api/projects` | 列出所有项目 |
| `/api/project/<name>/state` | 项目状态（当前阶段、章节、审批） |
| `/api/project/<name>/manifest` | 岗位文件流契约 |
| `/api/project/<name>/locks` | 所有锁文件 |
| `/api/project/<name>/log` | 执行日志（最近200行） |
| `/api/project/<name>/file?path=<rel>` | 查看项目内文件内容 |

零外部依赖，Ctrl+C 停止。

## 岗位工作规则

### 启动

AI 窗口在岗位目录打开后，按顺序读取：

1. 本目录 `README.md`
2. `../_system/START_HERE.md`
3. `../_system/project_canon.md`
4. `../_system/stage_manifest.json`
5. 本岗位的输入文件

### 停止

岗位窗口完成自己的输出并更新锁文件后，**必须停止**。不得自动继续下一阶段。

最终输出格式：
```
<stage_id> completed. Next stage: <next_stage_id>. Open that stage window to continue.
```

### 边界

- 编辑岗写报告，**不修改正文**
- 只有 lead_writer 和 revision_lead 可修改章节正文
- 章节只有在 chapter_freezer 冻结后才成为事实来源
- 全局设定属于启动上下文，不是中途补丁

## 模型配置策略

岗位使用符号化模型档案（model profile），不硬编码模型名。具体映射见 `MODEL_PROFILES.md`。

| 档案 | 适用岗位 |
|------|----------|
| `canon_planner` | story_bible, rolling_outline |
| `voice_designer` | voice_anchor |
| `brief_planner` | chapter_brief |
| `prose_lead` | lead_writer, revision_lead |
| `style_critic` | style_editor |
| `continuity_auditor` | continuity_editor |
| `mechanical_operator` | chapter_freezer |

## 项目创建流程

1. 在 `00_story_master/user_inputs/` 放入需求文档，或让 story_master AI 对话生成
2. AI 产出 `project_canon.md`（核心设定）
3. 生成项目目录结构（`workspace/<project>/`）
4. 填充 `_system/` 下的状态文件
5. 为每个岗位目录生成 `README.md`（基于 `templates/stage_readmes/README_TEMPLATE.md`）
6. 基础阶段按序执行，逐章阶段循环推进

## 需求变更流程

项目运行中收到新需求时：

1. 存为新需求记录
2. 不直接写章节
3. 产出 canon 更新计划
4. 审批后更新 `project_canon.md` 和受影响的衍生文件
5. 标记生效点（如 `effective_from: chapter_05`）
6. 已冻结章节不变，除非显式解冻
