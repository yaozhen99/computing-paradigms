# V2 ISA 异步模式

## 概述

全局 AI 在 Claude Code 对话中常驻，通过 ISA handoff 在独立 PowerShell 窗口中拉起各岗位节点。每个节点是独立进程，通过文件系统（lock、heartbeat、override）协调。watchdog.ps1 监控心跳和信号。

## 适用场景

- 跨平台 AI 协作（Claude + Aider + Cursor 等）
- 需要并行执行多个节点
- 需要进程隔离和故障恢复
- 长时间运行的项目

## 目录结构

```
$PROJECT_SPACE/
├── 01_requirements/
├── 02_design/
├── 03_source/
├── 04_tests/
├── 05_review/
├── 05_delivery/
├── _system/
│   ├── system_state.json
│   ├── pipeline_blueprint.json
│   ├── approved_tech_stack.json
│   ├── user_input.md
│   └── signal_kill_*.json      # 看门狗信号
├── _pipes/                     # lock + override
│   ├── lock_<角色>.json
│   └── override_*.json
├── _heartbeats/                # 心跳文件
│   └── hb_<角色>.md
├── _prompts_active/            # 激活的 prompt
├── _scripts/                   # 启动脚本
├── _isa/                       # ISA 工具
│   ├── handoff_executor.py
│   ├── process_manager.py
│   ├── heartbeat_loop.py
│   └── watchdog.ps1
├── _logs/
├── _skills/
├── audit/                      # ISA 审计文件
│   ├── role_token.json
│   ├── heartbeat.json
│   └── handoff.json
└── .claude/settings.json
```

## 启动方式

1. 任务师铸造完世界后，提示人类启动全局 AI
2. 人类在 Claude Code 中 cd 到项目目录，输入："Read and execute the instructions in _prompts_active/active_prompt_global_manager.md"
3. 全局 AI 进入感知循环，用 ScheduleWakeup 自驱动
4. 注册 watchdog.ps1 到 Task Scheduler

## 调度流程

1. 全局 AI 读取 pipeline_blueprint.json，确定流水线顺序
2. 用 ISA handoff 在独立 PowerShell 窗口拉起第一个节点
3. 节点独立运行，写心跳、完成后签字 lock
4. 全局 AI 感知循环检测 lock completed，用 ISA handoff 拉起下一节点
5. 心跳超时 → signal_kill + 重新拉起
6. 审核员否决 → override + 返工
7. 最后一个节点 lock completed → MISSION_ACCOMPLISHED

## ISA Handoff 机制

- handoff_executor.py：在新 PowerShell 窗口启动 Claude 交互模式，通过剪贴板+SendKeys 输入交接命令
- process_manager.py：claim_primary / signal_kill / signal_start
- heartbeat_loop.py：后台线程持续更新心跳
- watchdog.ps1：处理信号文件 + 心跳超时恢复

## 铁三角

PM、Reviewer、Integration 不可裁剪。Release（CI/CD 分发）可选。
