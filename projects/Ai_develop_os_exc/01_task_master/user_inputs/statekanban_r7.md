# StateKanban R7 — 任务师指令

## 项目

StateKanban 第七轮迭代：三路适配器 CLI 接入

## 需求文件

完整需求规格书：`00_requirement_writer/user_inputs/statekanban_r7.md`

任务师必须先读取该文件，理解全部 REQ 和验收标准后再执行。

## 代码空间

`C:\tower-of-babel\projects\statekanban\05_delivery\statekanban\`

## 测试空间

`C:\tower-of-babel\projects\statekanban\04_testing\test_scripts\`

## 范围

4 个 REQ：
- REQ-701：IflytekAdapter — 讯飞 MaaS 适配器（新增文件）
- REQ-702：DeepSeekAdapter — DeepSeek 双模式适配器（新增文件）
- REQ-703：CLI 多适配器接入 + `--model` + `--api-mode` 参数（修改文件）
- REQ-704：真实 LLM 端到端验证（验证性 REQ，不产出代码）

7 个交付物：2 个新适配器文件、3 个修改文件、2 个新测试文件

## 约束

- 不修改 Engine 驱动循环核心逻辑
- 不修改隔离边界代码
- 不新增 pip 依赖
- 不抽象适配器公共基类
- 向后兼容：`--adapter mock` 和 `--adapter codex` 行为不变

## 前置条件

- R6 完成，526 测试通过
- `openai` 包已安装（v2.30.0）
- `anthropic` 包已安装
- 环境变量已配置：`IFLYTEK_API_KEY`、`DEEPSEEK_API_KEY`、`ANTHROPIC_API_KEY`

## 验收

1. 全量测试通过（含新增适配器测试）
2. 三路 LLM 各跑通一次 `statekanban drive`
3. `--adapter mock` 无回归
