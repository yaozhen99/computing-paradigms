# Hermes Bridge 双向通信渠道开发笔记

**创建时间**：2026-04-23 11:30
**对应计划**：docs/plans/2026-04-23_hermes-bridge.md（ retrospective - 计划文档缺失）

## 1. 本次开发目标
在原有 Hermes Bridge（单向：Atlas → Hermes）基础上扩展为双向通信：
- 新增 `INBOX_DIR` 目录存放 Hermes → Claude Code 的消息
- 新增 `POST /message` 端点接收 Hermes 推送
- 新增 `GET /inbox` 和 `GET /inbox/<id>` 端点读取消息
- 新增 `DELETE /inbox/<id>` 端点删除消息
- 新增 MCP Server 提供原生工具集成
- 扩展 `POST /task` 增加 `from` 字段标识来源

## 2. 实施方案概要
- **HTTP 端点设计**：
  - `POST /message`：接收 JSON `{id, from, subject, body}`，写入 inbox/
  - `GET /inbox`：列出所有未读消息
  - `GET /inbox/<id>`：读取单条消息
  - `DELETE /inbox/<id>`：删除已读消息
- **MCP Server**：提供 7 个 tools 供 Claude Code 调用
- **数据存储**：文件系统 JSON 持久化

## 3. 涉及文件清单（预期）
- `bridge.py` — 扩展 HTTP 端点
- `mcp_server.py` — 新建 MCP Server
- `.mcp.json` — 新建 MCP 配置
- `inbox/*.json` — 消息存储

## 4. 注意事项
- WSL 调用 Hermes CLI 的路径和环境变量
- 消息 ID 的唯一性（使用 uuid）
- 并发写入 inbox 的文件锁问题（Python 单线程处理 HTTP 请求，无此问题）

## 5. 待确认问题
- [ ] Hermes 端是否需要适配新的 `/message` 端点格式
- [ ] 是否需要消息已读/未读状态标记
