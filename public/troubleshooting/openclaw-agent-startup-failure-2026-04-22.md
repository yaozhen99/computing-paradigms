# OpenClaw 代理启动故障排查记录

**日期**: 2026-04-22
**环境**: Windows 10 (x64), Node 24.14.0, OpenClaw 2026.4.15
**配置路径**: `C:\Users\yz01\.openclaw\`

---

## 故障现象

添加新代理后，OpenClaw 整体无法正常工作：
- Gateway 报 `token_mismatch` 错误，连接超时
- Puck (default-agent) 收到原 hermes 代理的微信消息后无法启动，session 卡住
- Atlas 给 hermes（WSL1 上的 zhienngti 智能体）的消息被路由到 Puck，Puck 收到但无法回复到微信
- 终端输出中存在 ANSI 转义码残留

---

## 根因分析

### 问题一：幽灵代理目录

`agents/` 目录下存在 `hermes` 和 `windows-admin` 两个代理目录，但 `openclaw.json` 的 `agents.list` 中并未注册它们。这两个目录是之前创建后未清理的残留，其中：

- `hermes/agent/models.json` 为 0 字节空文件，即使注册也无法工作
- `windows-admin/` 同样是未完成的配置

这些残留目录不会直接导致崩溃，但会干扰路由和 session 管理。

### 问题二：Gateway Token Mismatch

日志中出现：
```
unauthorized: gateway token mismatch
(open the dashboard URL and paste the token in Control UI settings)
```

**原因**: Gateway 重启后 token 刷新，但客户端缓存的旧 token 与新 token 不匹配。

**解决**: 执行 `openclaw gateway restart`，等待约 60-70 秒让 Gateway 完全启动后，token 自动同步。

### 问题三：Session 路由混乱（核心问题）

**重要澄清**: hermes 不是 OpenClaw 的 agent，而是 WSL1 上独立运行的 zhienngti 智能体。

问题链条：
1. Atlas 通过 `sessions_send`（agent-to-agent 通信）给 Puck 发消息，消息来源标记为 `provenance.kind: "inter_session"`
2. Puck 的微信 session（`agent:default-agent:openclaw-weixin:group:o9cq80xavpnuqbfxmu8mmvjifhgy@im.wechat`）的 `deliveryContext` **缺少 `to` 和 `accountId` 字段**
3. Puck 收到消息后能生成回复，但回复无法投递到微信，因为不知道发到哪个用户、用哪个 bot 账号
4. `cron-delivery` 持续报错：`Delivering to openclaw-weixin requires target`

**对比正常 session**:
```json
// 正常的 deliveryContext（agent:default-agent:main）
{
  "channel": "openclaw-weixin",
  "to": "o9cq80xavpNUQBFxmU8MMvjifhgY@im.wechat",
  "accountId": "2a9e145195c6-im-bot"
}

// 损坏的 deliveryContext（微信 group session）
{
  "channel": "openclaw-weixin"
  // 缺少 to 和 accountId！
}
```

**同时 `origin` 字段也有问题**:
```json
// 损坏的 origin
{ "provider": "webchat", "surface": "webchat", "chatType": "direct" }
// 应该是
{ "provider": "openclaw-weixin", "surface": "openclaw-weixin", "chatType": "direct" }
```

### 问题四：ANSI 转义码残留

Session 历史文件中存在大量 ANSI 转义码：
- `[32;1m` — 绿色加粗（PowerShell 的 `Get-ChildItem` 输出）
- `[31;1m` — 红色加粗（PowerShell 错误信息）
- `[7m` — 反色显示
- `[0m` — 重置颜色

**原因**: OpenClaw 的 `exec` 工具在 Windows 上执行 PowerShell 命令时，未 strip ANSI 转义码，将原始输出存入 session 历史。这些转义码在终端中正常显示颜色，但通过微信等渠道发送时会变成乱码。

**影响范围**: 24 个 session 文件受影响，主要集中在 `agents/main/sessions/` 目录。

**状态**: 这是 OpenClaw 上游的 bug，非配置问题，暂无本地修复方案。

---

## 修复步骤

### Step 1: 删除幽灵代理目录

```powershell
Remove-Item -Recurse -Force "C:\Users\yz01\.openclaw\agents\hermes"
Remove-Item -Recurse -Force "C:\Users\yz01\.openclaw\agents\windows-admin"
```

### Step 2: 清理 Puck 的残留 session

1. 删除 lock 文件和 session 数据文件：
```powershell
Remove-Item -Force "C:\Users\yz01\.openclaw\agents\default-agent\sessions\c7abbc3c-312f-4ab1-a90d-d4687e82e5f2.jsonl.lock"
Remove-Item -Force "C:\Users\yz01\.openclaw\agents\default-agent\sessions\c7abbc3c-312f-4ab1-a90d-d4687e82e5f2.jsonl"
```

2. 从 `sessions.json` 中移除残留的 session 条目（key: `agent:default-agent:openclaw-weixin:group:o9cq80xavpnuqbfxmu8mmvjifhgy@im.wechat`），只保留 `agent:default-agent:main`。

### Step 3: 修复 Puck 微信 session 的 deliveryContext

在 `sessions.json` 中，Puck 的微信 group session 的 `deliveryContext` 缺少 `to` 和 `accountId`，`origin` 的 provider/surface 也错误。

修复前：
```json
"deliveryContext": { "channel": "openclaw-weixin" },
"origin": { "provider": "webchat", "surface": "webchat", "chatType": "direct" }
```

修复后：
```json
"deliveryContext": {
  "channel": "openclaw-weixin",
  "to": "o9cq80xavpNUQBFxmU8MMvjifhgY@im.wechat",
  "accountId": "2a9e145195c6-im-bot"
},
"origin": { "provider": "openclaw-weixin", "surface": "openclaw-weixin", "chatType": "direct" }
```

**关键**: `to` 是微信用户的 OpenID，`accountId` 是微信 bot 的账号 ID。这两个字段决定了 Puck 的回复能否投递到微信。

### Step 4: 重启 Gateway

```powershell
openclaw gateway restart
```

等待 60-70 秒后验证：
```powershell
openclaw gateway probe
# 期望输出: Reachable: yes, Connect: ok, RPC: ok
```

### Step 5: 验证整体状态

```powershell
openclaw status
openclaw agents list
```

确认：
- Gateway: `reachable`
- Agents: 只有 `main` (Atlas) 和 `default-agent` (Puck)
- Sessions: 无卡住的 session
- cron-delivery: 不再报 `requires target` 错误

---

## 预防措施

1. **删除代理前先清理 session**: 删除代理目录前，先检查并清理该代理的所有 session 数据，避免路由 fallback 导致其他代理卡死。

2. **检查 lock 文件**: 如果代理无法启动，检查 `sessions/` 目录下是否有 `.lock` 文件残留，手动删除即可。

3. **Gateway 启动时间**: Gateway 重启后需要约 60-70 秒才能完全就绪，期间 `probe` 会超时，属于正常现象。

4. **ANSI 转义码**: 在 Windows 上使用 `exec` 工具时，可以在命令前加 `$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8` 来减少 ANSI 输出，或在 PowerShell 7+ 中设置 `$PSStyle.OutputRendering = 'PlainText'`。

5. **微信 session 的 deliveryContext**: 当通过 `sessions_send` 给另一个 agent 发消息时，确保目标 agent 的 session 有完整的 `deliveryContext`（包含 `channel`、`to`、`accountId`），否则回复无法投递到微信。

6. **hermes 不是 OpenClaw agent**: hermes 是 WSL1 上独立运行的 zhienngti 智能体，与 OpenClaw 的 agent 系统无关。如果 Atlas 需要与 hermes 通信，应通过微信渠道而非 agent-to-agent 路由。

---

## 当前状态

| 项目 | 状态 |
|------|------|
| Gateway | ✅ reachable, RPC ok |
| Atlas (main) | ✅ 正常运行 |
| Puck (default-agent) | ✅ 正常运行，微信投递已修复 |
| hermes (WSL1 zhienngti) | 🔵 独立运行，非 OpenClaw agent |
| 幽灵代理目录 | 🗑️ 已删除 |
| Puck deliveryContext | ✅ 已补全 to + accountId |
| Puck origin | ✅ 已修正为 openclaw-weixin |
| ANSI 转义码 | ⚠️ 上游 bug，暂无本地修复 |
| cron-delivery | ✅ 不再报 requires target |
