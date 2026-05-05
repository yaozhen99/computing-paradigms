# Hermes 通信架构澄清

> 2026-04-22 22:26 | Atlas 决策

## 事实

1. **WSL1 Hermes** 是真正的 Hermes Agent（CiviBBS测试岗），运行在 WSL Alpine，通过 HTTP 桥接（localhost:8898）通信
2. **OpenClaw 内部的 hermes agent** 已删除，但可能残留路由规则，导致消息串台到 Puck
3. hermes-bridge（bridge.py + mcp_server.py）只服务 WSL1 Hermes，架构正确
4. hermes-soul.md 对应 WSL1 Hermes（CiviBBS测试岗），身份正确

## 通信规则（铁律）

| 通信对象 | 方式 | 禁止 |
|----------|------|------|
| WSL1 Hermes | HTTP桥接 localhost:8898 | ❌ sessions_send |
| Puck | sessions_send（待修） | ❌ 通过hermes-bridge |
| Claude Code | sessions_spawn 子代理 | ❌ sessions_send |
| NanoBot | DeepSeek API / Ollama | ❌ sessions_send |

**核心原则：Hermes 不在 OpenClaw agent 体系内，永远用 HTTP 桥接，不用 sessions_send。**

## 需要清理

1. ~~OpenClaw 配置中 hermes agent 的残留路由~~ — 配置里已无 hermes，可能是运行时缓存
2. 确保 sessions_send 不再尝试发给 "hermes"

## 教训

- 名字冲突是系统性地雷——两个东西不能叫同一个名字
- 删除 agent 后必须清理所有引用，否则产生影子代码
- 通信方式必须跟架构匹配——WSL 外部 agent 用 HTTP，不用 OpenClaw 内部通道

---
*决策者：Atlas | 2026-04-22*
