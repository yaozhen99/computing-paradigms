# V2 Agent 子代理模式

## 概述

全局 AI 在 Claude Code 对话中常驻，通过 Agent 子代理调度各岗位。子代理同步执行，完成后返回结果。无需独立进程、无需心跳、无需异步轮询。

## 适用场景

- 所有 AI 都是 Claude（同一平台）
- 单会话内完成全部开发
- 不需要跨平台 AI 协作

## 目录结构

```
$PROJECT_SPACE/
├── 01_requirements/          # PM 输出
├── 02_design/                # 架构师输出
├── 03_source/                # 开发者输出
├── 04_tests/                 # 测试输出
├── 05_review/                # 审核员输出
├── 05_delivery/              # 发布经理输出
├── _system/                  # 系统文件
│   ├── system_state.json
│   ├── pipeline_blueprint.json
│   ├── approved_tech_stack.json
│   └── user_input.md
├── _pipes/                   # lock 文件（签字凭证）
├── _logs/
├── _skills/
└── .claude/settings.json     # 读写权限
```

## 启动方式

1. 任务师铸造完世界后，提示人类启动全局 AI
2. 人类在 Claude Code 中 cd 到项目目录，输入："Read and execute the instructions in _prompts_active/active_prompt_global_manager.md"
3. 全局 AI 进入调度循环，用 ScheduleWakeup 自驱动

## 调度流程

1. 全局 AI 读取 pipeline_blueprint.json，确定流水线顺序
2. 按顺序用 Agent 子代理拉起各岗位
3. 子代理完成后签字 lock 文件
4. 全局 AI 检测 lock completed，拉起下一岗位
5. 审核员否决时，全局 AI 用 Agent 子代理拉起返工
6. 最后一个节点 lock completed → MISSION_ACCOMPLISHED

## 铁三角

PM、Reviewer、Integration 不可裁剪。Release（CI/CD 分发）可选。
