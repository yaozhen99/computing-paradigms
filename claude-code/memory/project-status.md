---
name: project-status
description: 当前项目状态：飞书直连、Hermes Bridge、CiviBBS V2.0
type: project
originSessionId: 43c16b9c-1ff9-402f-baba-0f4ceff9d7d1
---
# 项目状态

## 飞书直连 (2026-04-30)
- **App ID**: cli_a97a0123a59e1bc3 (130-ClaudeCode)
- **P2P chat_id**: oc_30fd17b2e34653f5104576bee320071a
- **Group chat_id**: oc_f16e9f45d7ce40242187fe070267d93e
- **Owner open_id**: ou_5720d55577492ef8732412c0334c5c70
- **模块**: C:\Users\yz01\.openclaw\feishu_direct.py
- **轮询服务**: feishu_listener.py (后台运行)
- **凭据**: C:\Users\yz01\.openclaw\feishu-direct\.app_id / .app_secret

## Hermes Bridge (2026-05-01 修复确认)
- **目录**: C:\tower-of-babel\hermes-bridge\
- **端口**: 8899 (PID 25144)
- **状态**: 全链路通畅，已验证
- **修复历史**:
  1. WSL路径→Windows路径、Alpine-WSL1→Ubuntu、端口8898→8899
  2. 移除 subprocess.run 的 cwd 参数（避免嵌套目录）
  3. 杀掉 WSL 内旧 bridge 进程 (PID 36401) — wslrelay 将 8899 转发到 WSL 旧进程，导致 Windows bridge 收不到请求
  4. 杀掉 Windows 旧 bridge 进程 (PID 4064) — 多进程监听同一端口
- **Token**: BRIDGE_API_TOKEN in .env
- **关键教训**: WSL 端口转发会劫持 Windows 同端口请求，必须确保 WSL 内无同名服务

## CiviBBS V2.0 邮件总线
- **仓库**: C:\civibbs\v1.0
- **分支**: `feature/v2-mailbus`（未提交）
- **进度**: 第一步完成（核心模块 + 30 个测试通过）

## OpenClaw Gateway B1+B2 补丁 (2026-05-02)
- **B1 反转崩溃策略**: `gateway-watchdog.cmd` — 指数退避守护重启（max 10 次，2s-60s 退避，5min 窗口重置）
- **B2 配置原子写入保护**: `gateway-healthcheck.cmd` + `scripts/validate-config.js` — 启动前校验 JSON 完整性，损坏自动从 .last-good 恢复
- **Windows 计划任务**: "OpenClaw Gateway" (ONLOGON) + "OpenClaw Gateway (Startup)" (ONSTART +30s)
- **辅助脚本**: `scripts/timestamp.js`（ISO 时间戳，替代已废弃的 wmic）
- **关键约束**: cmd 脚本中不能用 `node -e "..."`（cmd.exe 引号截断），必须用独立 .js 文件

**Why:** 10 次 clobbered 事件证明配置损坏+崩溃无恢复是系统性问题
**How to apply:** 启动 gateway 时用 watchdog 而非直接 gateway.cmd
