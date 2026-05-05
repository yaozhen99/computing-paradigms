# Agent Protocol — 多模式协作框架

## 模式选择

| | V2 Agent 子代理模式 | V2 ISA 异步模式 |
|---|---|---|
| **适用场景** | 全是 Claude，单会话开发 | 跨平台 AI（Claude+Aider+Cursor），并行执行 |
| **调度方式** | Agent 子代理（同步） | ISA handoff（异步） |
| **进程模型** | 单进程，子代理串行 | 多进程，独立 PowerShell 窗口 |
| **协调机制** | lock 签字凭证 | lock + heartbeat + override + watchdog |
| **故障恢复** | 子代理失败重试即可 | signal_kill + claim_primary + 新进程接替 |
| **并行能力** | 无（串行） | 有（多窗口并行） |
| **复杂度** | 低 | 高 |

## 决策规则

- **所有 AI 都是 Claude** → V2 Agent 模式
- **混合 AI 平台** → V2 ISA 模式
- **需要并行执行** → V2 ISA 模式
- **快速原型/小项目** → V2 Agent 模式

任务师在裁决阶段根据技术栈和需求决定使用哪种模式。

## ISA 进程交接工具

ISA 模式下每个岗位是独立 PowerShell 窗口中的 Claude 交互进程，需要进程拉起、命令注入、旧进程清理。

工具位置：`C:\tower-of-babel\projects\isa-process-handoff\`

| 文件 | 用途 |
|------|------|
| handoff_executor.py | 拉起新 PowerShell 窗口，通过剪贴板+SendKeys 输入交接命令 |
| process_manager.py | claim_primary + 杀旧进程，保证同一角色只有一个活跃实例 |
| heartbeat_loop.py | 心跳循环，向 _heartbeats/ 写入存活标记 |
| watchdog.ps1 | 外部看门狗，检测心跳超时后触发重启 |

**调试方法**：

1. 单独测试拉起：`python handoff_executor.py --from-pid 0 --task "测试指令" --project-dir C:\test_project`
2. 单独测试进程管理：`python process_manager.py --action claim --role backend --project-dir C:\test_project`
3. 单独测试心跳：`python heartbeat_loop.py --role backend --project-dir C:\test_project`
4. watchdog 干跑：`powershell -File watchdog.ps1 -ProjectDir C:\test_project -TimeoutSeconds 120`

Agent 模式不需要这些工具（子代理在主会话内同步执行）。ISA 模式实战时直接调用即可。

---

## 铁三角（两种模式通用）

PM、Reviewer、Integration 不可裁剪。Release（CI/CD 分发）可选。无论项目大小，铁三角必须启用。

## 目录结构

```
agent_protocol/
├── v2_agent/           # Agent 子代理模式
│   ├── 00_global_manager/
│   ├── 01_pm/
│   ├── 02_architect/
│   ├── 03_dba/
│   ├── 04_uiux/
│   ├── 05_backend/
│   ├── 06_frontend/
│   ├── 07_devops/
│   ├── 08_tester_write/
│   ├── 09_tester_run/
│   ├── 10_security/
│   ├── 11_reviewer/
│   ├── 12_doc/
│   ├── 13_integration/     # 集成合成（铁三角，不可裁剪）
│   ├── 14_release/         # CI/CD 打包分发（可选）
│   └── _shared/
├── v2_isa/             # ISA 异步模式
│   ├── 00_global_manager/
│   ├── 01_pm/
│   ├── 02_architect/
│   ├── 03_dba/
│   ├── 04_uiux/
│   ├── 05_backend/
│   ├── 06_frontend/
│   ├── 07_devops/
│   ├── 08_tester_write/
│   ├── 09_tester_run/
│   ├── 10_security/
│   ├── 11_reviewer/
│   ├── 12_doc/
│   ├── 13_integration/     # 集成合成（铁三角，不可裁剪）
│   ├── 14_release/         # CI/CD 打包分发（可选）
│   └── _shared/
│       └── _isa/
└── README.md           # 本文件
```
