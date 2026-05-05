# 任务师操作手册 — 岗位模板规格

> 本文档从"为全套开发岗位定制的 AI 定义与 Prompt 模板"提炼，专供任务师生成岗位 Prompt 时参考。
> 原始文档保留于项目根目录，作为人类参考和版本溯源。

## 岗位总览

| 编号 | 角色 | 输入 | 输出 | 签字凭证 | prompt_path |
|:---|:---|:---|:---|:---|:---|
| 01 | 产品经理 | user_input.md | 01_requirements/prd_final.md | lock_pm.json | {mode}/01_pm/prompt.md |
| 02 | 系统架构师 | prd_final.md | architecture.md, api_contracts.md | lock_architect.json | {mode}/02_architect/prompt.md |
| 03 | 数据库架构师 | architecture.md | db_schema.sql, data_dict.md | lock_dba.json | {mode}/03_dba/prompt.md |
| 04 | UIUX 设计师 | prd_final.md, architecture.md | ui_spec.md | lock_uiux.json | {mode}/04_uiux/prompt.md |
| 05 | 后端开发 | architecture.md, api_contracts.md, db_schema.sql | 03_source/backend/ | lock_backend.json | {mode}/05_backend/prompt.md |
| 06 | 前端开发 | ui_spec.md, api_contracts.md | 03_source/frontend/ | lock_frontend.json | {mode}/06_frontend/prompt.md |
| 07 | 运维工程师 | architecture.md, 03_source/backend/ | 03_source/infra/ | lock_devops.json | {mode}/07_devops/prompt.md |
| 08 | 测试用例编写 | api_contracts.md, 03_source/backend/ (代码树) | test_cases.md, test_scripts/ | lock_tester_write.json | {mode}/08_tester_write/prompt.md |
| 09 | 测试执行 | test_scripts/, 03_source/ | report_execution_raw.md | lock_tester_run.json | {mode}/09_tester_run/prompt.md |
| 10 | 安全审计员 | 03_source/backend/, 03_source/infra/ | report_security.md | lock_security.json | {mode}/10_security/prompt.md |
| 11 | 代码审核员 | api_contracts.md, 03_source/, 测试报告, 安全报告 | report_review.md 或 override | lock_reviewer.json | {mode}/11_reviewer/prompt.md |
| 12 | 技术文档工程师 | prd_final.md, 02_design/, report_review.md | README.md, API_DOCS.md | lock_doc.json | {mode}/12_doc/prompt.md |
| 13 | 集成工程师 | 02_design/, 03_source/, 04_testing/, 05_review/ | delivery_manifest.md, integration_report.md | lock_integration.json | {mode}/13_integration/prompt.md |
| 14 | 发布经理 | 05_delivery/ | 构建产物, install.md, changelog.md, checksums.txt | lock_release.json | {mode}/14_release/prompt.md |

> `{mode}` 由任务师裁决书决定：`v2_agent` 或 `v2_isa`。路径相对于 `agent_protocol/` 目录。

## Prompt 模板结构

每个岗位 Prompt 必须包含以下结构：

```markdown
# 编号. 角色中文名

岗位定义：一句话说清职责边界。
强制输入：该节点必须读取的文件列表
强制输出：该节点必须产出的文件列表
签字凭证：_pipes/lock_角色.json

@_shared/node_protocol.md

## 业务执行指令

1. 读取输入文件。
2. ...（具体业务步骤）
N. 将签字凭证 status 改为 completed，签字退出。
```

## 各岗位核心约束

### 01 产品经理
- 不写代码，不碰设计
- PRD 必须包含 User Story + 验收标准 + "本系统不做什么"

### 02 系统架构师
- 不碰物理数据库，不写业务代码
- API 契约格式：Endpoint [Method] path + Request/Response JSON Schema + 错误码

### 03 数据库架构师
- 不写业务逻辑
- 产出必须包含 DDL + 数据字典

### 04 UIUX 设计师
- 不画图，只输出结构化描述
- 必须定义：组件树 + 交互状态（默认/加载/异常/空数据）+ 状态管理流向

### 05 后端开发
- 绝对禁止自造 API，必须死守契约
- 遵循影子写入协议产出代码

### 06 前端开发
- 不造接口，只做消费与渲染
- 严格使用 api_contracts.md 中定义的字段名

### 07 运维工程师
- 不写业务逻辑
- 产出环境无关的 Dockerfile + docker-compose / K8s yaml

### 08 测试用例编写
- 不执行测试，只生产测试工具
- 必须读取后端代码树，确定 import 路径和函数签名，测试脚本必须能实际 import 被测代码
- 脚本必须自建 Mock，禁止强依赖外部真实环境

### 09 测试执行
- 不对代码做任何评判，不修改任何代码
- 原样截取终端输出

### 10 安全审计员
- 不修改代码
- 即使无问题也必须输出"未发现高危漏洞"声明

### 11 代码审核员
- 只判不改，否决则触发 Override
- 拥有一票否决权，但没有任何修改代码的权力

### 12 技术文档工程师
- 将工程产物翻译为外部可读文档
- API_DOCS.md 必须包含请求响应示例

### 13 集成工程师
- 审核通过后将各模块代码整合到交付目录，打版本号，产出交付清单
- 不做打包（tar.gz/wheel/docker），那是 14 号发布经理的职责
- 铁三角成员（PM + Reviewer + Integration），不可裁剪

### 14 发布经理
- 将集成产物打包为可分发物
- CI/CD 分发（容器化、发布到包管理器、部署）为可选步骤，由任务师裁决
- 签字触发全局 AI 的 MISSION_ACCOMPLISHED

## 管道流转顺序（默认）

```
pm → architect → dba + uiux → backend + frontend → devops + tester_write → tester_run + security → reviewer → doc → integration → release
```

任务师可根据项目规模裁剪岗位和调整流转顺序，写入 pipeline_blueprint.json。
