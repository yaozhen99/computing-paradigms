# 项目备案 — Hermes Bridge

> 备案日期: 2026-04-22 | 开发者: Claude Code

## 项目信息

| 字段 | 值 |
|------|-----|
| 项目名 | Hermes Bridge |
| 类型 | 基础设施 / 通信桥接 |
| 状态 | 已开发，待部署 |
| 运行目录 | C:\tower-of-babel\hermes-bridge\ |
| 归档目录 | C:\tower-of-babel\projects\hermes-bridge\ |
| 端口 | 8898 |

## 开发历史

### 第一阶段：单向桥接 (2026-04-22 14:10–15:06)

由之前的 Claude Code 会话开发：
- bridge.py：Atlas → Hermes 单向 HTTP 桥接
- POST /task：派任务给 Hermes
- GET /result/{id}：查任务结果
- GET /result：列出所有结果
- GET /status：服务状态
- test_capture.py：测试脚本
- hermes-soul.md：Hermes 身份文件

### 第二阶段：双向通信 (2026-04-22 16:00–17:00)

本次会话开发：
- bridge.py 扩展：新增 inbox 机制，POST /task 增加 from 字段
- mcp_server.py：MCP Server，7 个 tools
- .mcp.json：MCP 配置
- 修复 error 变量未定义 bug

## 通信架构

```
Claude Code ←MCP→ Hermes Bridge (8898) ←HTTP→ Hermes
Claude Code ←Atlas→ (原有渠道保留)
Atlas ←HTTP→ Hermes Bridge (8898) ←HTTP→ Hermes (原有渠道保留)
```

## 文件清单

| 文件 | 说明 |
|------|------|
| bridge.py | HTTP 桥接服务（双向） |
| mcp_server.py | MCP Server |
| .mcp.json | MCP 配置 |
| hermes-soul.md | Hermes 身份文件 |
| test_capture.py | 测试脚本 |
| tasks/ | 任务目录 |
| results/ | 结果目录 |
| inbox/ | 收件箱目录 |

## 依赖

- Python 3.x
- httpx
- mcp SDK
- Hermes (运行在 WSL Alpine，通过 hermes chat -q 调用)

---
*Claude Code | 2026-04-22*