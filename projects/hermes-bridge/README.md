# Hermes Bridge

## 概述
Claude Code ↔ Hermes 双向通信桥接服务。

## 架构
- **Bridge** (bridge.py): HTTP 服务，端口 8898
- **MCP Server** (mcp_server.py): Claude Code 原生集成，7 个 tools
- **Inbox**: Hermes → Claude Code 消息推送机制

## API

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /task | 向 Hermes 提交任务 |
| POST | /message | Hermes → Claude Code 推送消息 |
| GET | /result | 列出所有任务结果 |
| GET | /result/{id} | 查询单个任务结果 |
| GET | /inbox | 列出收件箱消息 |
| GET | /inbox/{id} | 读取单条消息 |
| DELETE | /inbox/{id} | 删除消息 |
| GET | /status | 服务状态 |

## MCP Tools

| Tool | 说明 |
|------|------|
| hermes_submit_task | 提交任务给 Hermes |
| hermes_get_result | 查询任务结果 |
| hermes_list_results | 列出所有结果 |
| hermes_check_inbox | 检查 Hermes 发来的消息 |
| hermes_read_message | 读取单条消息 |
| hermes_delete_message | 删除消息 |
| hermes_bridge_status | 桥接服务状态 |

## 通信方向
- **Claude Code → Hermes**: MCP tools → POST /task
- **Hermes → Claude Code**: POST /message → GET /inbox

## 运行
```bash
python bridge.py          # 启动桥接服务
# MCP Server 由 Claude Code 自动加载
```

## 依赖
- Python 3.x
- httpx
- mcp SDK

---
*创建: 2026-04-22 | Claude Code*
