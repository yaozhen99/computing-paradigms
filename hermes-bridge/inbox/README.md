# inbox/

**最后更新**：2026-04-23 11:20

## 用途
存放 Hermes → Claude Code 的推送消息。Hermes 通过 `POST /message` 写入，Claude Code 通过 `GET /inbox` 读取。

## 内容概览
| 文件 | 职责说明 |
|:---|:---|
| `*.json` | 单条消息，格式为 `{id, from, subject, body, created, read}` |

## 对外接口
- 消息由 bridge.py 的 `BridgeHandler.do_POST(/message)` 写入
- 消息由 `BridgeHandler.do_GET(/inbox)` 列出、`do_GET(/inbox/<id>)` 读取、`do_DELETE(/inbox/<id>)` 删除

## 依赖
- **外部依赖**：无
- **内部依赖**：bridge.py

## 约定与规范
- 文件名即消息 ID，格式为 `<msg_id>.json`
- 消息读取后应通过 DELETE 端点清理

## 更新记录
- **2026-04-23 11:20**：初始化 README
