---
name: hermes-identity-lesson
description: Hermes Bridge 身份混淆教训 — 违反 R3 的案例
type: feedback
originSessionId: 43c16b9c-1ff9-402f-baba-0f4ceff9d7d1
---
# Hermes Bridge 身份混淆教训

扩展 hermes-bridge 时没有搞清楚两个 Hermes 的区别（OpenClaw 内部已删除的 Hermes vs WSL1 真正的 Hermes），直接在原有基础上加了双向通信和 MCP，加剧了命名混乱。

**违反了 R3（架构变更先问 Atlas）。**

**Why:** 盲目扩展现有代码而不理清架构归属，导致命名冲突和通道错位
**How to apply:** 涉及多智能体通信架构的变更，必须先向 Atlas 确认身份和归属再动手
