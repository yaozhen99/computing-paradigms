# Team-1：开发流水线

WSL2 上的开发-测试-审核流水线。三个子代理共享一套 hermes-agent (v0.10.0)，通过 named profile 隔离，通过飞书群和 bridge 协作。

## 成员

| 实例 | 角色 | 飞书名 | App ID | HERMES_HOME | 人格关键词 |
|------|------|--------|--------|-------------|-----------|
| herdev | 开发岗 | 130Herdev | cli_a979f9666d7c1bb3 | ~/.hermes/profiles/herdev/ | 务实、先跑通再优化 |
| Hertes | 测试岗 | 130Hertes | cli_a97a13108bb85bd5 | ~/.hermes/ (default) | 严谨、追到底 |
| Hermod | 审核岗 | 130hermod | cli_a97ac89d603c5bc3 | ~/.hermes/profiles/hermod/ | 客观、标准明确 |

## 流程

```
herdev（开发）→ Hertes（测试）→ Hermod（审核）→ 人在回路 → 交付
```

1. **herdev** 根据需求编写代码，输出可测试的变更
2. **Hertes** 跑测试验证，输出结构化测试报告（通过/失败/待验证）
3. **Hermod** 审核代码质量，输出审核结论（通过/需修改/驳回）
4. **人在回路** 反馈决策
5. **交付** 合并部署

## 通信

- **Bridge**: http://127.0.0.1:8891（team-1 专用）
- **飞书群**: 三个实例均可接收群消息（GROUP_POLICY=open）
- **同租户不同 App**: 飞书事件按 App ID 路由，同租户不冲突，共用 App ID 才会互踢

## 命令

```bash
# 聊天
herdev              进入 herdev 对话
hertes              进入 Hertes 对话（或直接 hermes，用默认 profile）
hermod              进入 Hermod 对话

# 飞书 Gateway
herdev gateway run          启动 herdev 飞书通道
hertes gateway run          启动 Hertes 飞书通道
hermod gateway run          启动 Hermod 飞书通道

# 一键启停
~/start_gateways.sh all           启动所有 WSL2 实例
~/start_gateways.sh hermod        只启动 Hermod
~/stop_gateways.sh all            停止所有实例
```

## 工作目录

| 实例 | Windows 工作目录 |
|------|-----------------|
| herdev | C:\tower-of-babel\hermes-herdev\ |
| Hertes | C:\tower-of-babel\hermes\ |
| Hermod | C:\tower-of-babel\hermes-hermod\ |

## 规则

- **谁都不碰主环境 env** — `~/.hermes/` 是 Hertes 的，其他实例用 named profile
- **每个实例的飞书应用必须独立** — 共用 App ID 会互踢 WebSocket
- **Bridge 端口 8891** — team-1 专用，其他团队用 8892、8893...
