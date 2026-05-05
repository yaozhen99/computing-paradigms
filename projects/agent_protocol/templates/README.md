# Agent Protocol 模板库

## 版本索引

| 版本 | 目录 | 说明 |
|:---|:---|:---|
| v1.0 | `v1.0/` | 初始版本，原始模板 |
| v1.1 | `v1.1/` | 新增编码纪律、临时目录豁免 |
| **v1.2** | **`v1.2/`** | **当前推荐版本** |

## v1.0 → v1.1 变更记录

### AGENTS.md
- 第三条"目录驻留文档纪律"新增**豁免条款**：程序运行时自动生成的临时目录（build/、dist/、__pycache__/、.tmp/ 等）无需创建或更新 README.md
- 新增**第四条"编码执行纪律（强制）"**：目标先行（必须先输出目标+验证方式，等确认后再动手）、手术式修改（改完 diff 自检，无法追溯的改动必须撤回）、禁止顺手重构

### CLAUDE.md
- 新增"编码纪律"章节：
  - **目标驱动微循环**：编码前必须先输出目标与验证方式，等确认后再动手，不准跳过
  - **手术式修改**：只碰触必须修改的部分，改完后 diff 自检，无法追溯的改动必须撤回

### general_patterns.md
- "代码优化模式"章节沉淀上述两条模式（含强制步骤和自检要求）

## v1.1 → v1.2 变更记录（架构级重构）

### 目录结构重构
- 从平铺文件改为按岗位分包，每个角色独立目录（prompt.md + manifest.json）
- 新增 `_shared/`：共享层独立，包含 node_protocol.md、AGENTS.md、CLAUDE.md
- 新增 `00_task_master/`：任务师 Prompt + manifest
- 新增 `00_global_manager/`：全局 AI Prompt + manifest
- 底层协议引用方式变更：`@_system/node_protocol.md` → `@_shared/node_protocol.md`
- 删除旧平铺结构（prompts/ 目录、根目录 AGENTS.md/CLAUDE.md）

### Ai_develop_os 集成
- v1.2 完整拷贝至 `Ai_develop_os/agent_protocol_v1.2/`
- 架构文档中任务师创世流程引用 v1.2 路径
- 节点底层协议第7条引用 `_shared/` 路径