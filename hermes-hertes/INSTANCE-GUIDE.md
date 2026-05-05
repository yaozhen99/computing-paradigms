# Hermes 实例管理手册

## 概述

Hermes 是基于 hermes-agent 框架的 AI 代理，通过 profile 机制支持多实例并行运行。每个实例有独立的飞书应用、身份定义和会话空间。

## 实例清单

| 实例 | 命令 | 飞书机器人 | 飞书 App ID | HERMES_HOME | 职责 |
|------|------|-----------|-------------|-------------|------|
| Hermes | `hermes` | 130Hermes | cli_a97a13108bb85bd5 | /home/yz01/.hermes | 测试岗（default） |
| Hermod | `hermod` | 130hermod | cli_a97ac89d603c5bc3 | /home/yz01/.hermes/profiles/hermod | 待定 |
| Hertes | `hertes` | Hertes | cli_a97a13108bb85bd5 | /home/yz01/.hermes/profiles/hertes | 待定 |

> ⚠️ Hertes 目前与 Hermes 共用同一个飞书应用，同时运行会冲突。需要分配独立飞书应用后才能并行。

## 目录结构

```
C:\tower-of-babel\
├── hermes\              ← 本文档所在，Hermes 工作目录
├── hermes-hermod\       ← Hermod 工作目录（待创建）
├── hermes-hertes\       ← Hertes 工作目录（待创建）
└── ...

WSL 内部：
/home/yz01/.hermes/                    ← Hermes (default) 配置和会话
/home/yz01/.hermes/profiles/hermod/    ← Hermod 配置和会话
/home/yz01/.hermes/profiles/hertes/    ← Hertes 配置和会话
/home/yz01/hermes-venv/                ← 共享 Python 虚拟环境
/home/yz01/.local/bin/                 ← 快捷命令 (hermes/hermod/hertes)
```

## 常用命令

### 聊天
```
hermes          进入 Hermes 对话
hermod          进入 Hermod 对话
hertes          进入 Hertes 对话
```

### 飞书 Gateway
```
hermes gateway run      启动 Hermes 飞书通道
hermod gateway run      启动 Hermod 飞书通道
hertes gateway run      启动 Hertes 飞书通道
```

### 一键启停
```
~/start_gateways.sh all       启动所有实例
~/start_gateways.sh hermod    只启动 Hermod
~/stop_gateways.sh all        停止所有实例
~/stop_gateways.sh hermes     只停止 Hermes
```

### Profile 管理
```
hermes profile list            查看所有实例状态
hermes profile create NAME --clone     创建新实例（只复制配置）
hermes profile create NAME --clone-all 创建新实例（含会话和记忆）
hermes profile delete NAME     删除实例
```

## 配置文件

每个实例的核心配置：

| 文件 | 说明 |
|------|------|
| .env | 飞书凭证、API Key（**每个实例必须独立**） |
| SOUL.md | 身份定义、职责、风格 |
| config.yaml | 模型、日志级别等运行参数 |

### .env 关键变量

```bash
FEISHU_APP_ID=          # 飞书应用 ID（每个实例不同）
FEISHU_APP_SECRET=      # 飞书应用密钥
FEISHU_BOT_NAME=        # 飞书群内机器人名
FEISHU_BOT_OPEN_ID=     # 机器人 Open ID（可留空，自动获取）
FEISHU_DOMAIN=feishu    # 中国版飞书
FEISHU_CONNECTION_MODE=websocket  # WebSocket 长连接
FEISHU_GROUP_POLICY=open          # 群消息策略（必须设为 open）
GATEWAY_ALLOW_ALL_USERS=true
```

## 新增实例流程

1. 在飞书开放平台创建新应用，获取 App ID 和 App Secret
2. `hermes profile create <name> --clone`
3. 编辑 `~/.hermes/profiles/<name>/.env`，填入飞书凭证
4. 编辑 `~/.hermes/profiles/<name>/SOUL.md`，定义身份
5. 在 `C:\tower-of-babel\` 下创建 `hermes-<name>\` 工作目录
6. `hermes gateway run` 或 `<name> gateway run` 启动

## 踩坑记录

1. **FEISHU_GROUP_POLICY 必须设为 open**，默认 allowlist 为空会导致群消息被丢弃
2. **FEISHU_BOT_NAME/OPEN_ID 建议手动指定**，lark-oapi SDK 兼容问题可能导致自动获取失败
3. **改代码要改 site-packages 路径**（`/home/yz01/hermes-venv/lib/python3.12/site-packages/`），不是源码目录
4. **每个实例的飞书应用必须独立**，共用 App ID 会互相踢掉 WebSocket 连接
5. **wrapper 脚本在 `~/.local/bin/`**，需确保 PATH 包含该目录（已在 .bashrc 中配置）

## 已清理

- nanobot 已于 2026-04-30 完全卸载：进程、服务(NanobotGateway/NanobotMonitor)、计划任务(NanobotWatchdog)、目录、可执行文件全部删除
- /home/yz01/.hermes-nanobot 已删除
