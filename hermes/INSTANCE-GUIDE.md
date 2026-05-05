# Hermes 实例管理手册

## 概述

Hermes 是基于 hermes-agent 框架的 AI 代理，通过 profile 机制支持多实例并行运行。
每个实例有独立的飞书应用、身份定义和会话空间。

## 团队

| 团队 | 文档 | 说明 |
|------|------|------|
| team-1 | `team-1/README.md` | WSL2 开发流水线（herdev/Hertes/Hermod） |
| team-watch | `team-watch/README.md` | herwin Windows 独立守护 |

## 全局实例清单

| 实例 | 角色 | 命令 | 飞书名 | App ID | HERMES_HOME | 环境 |
|------|------|------|--------|--------|-------------|------|
| herdev | 开发岗 | `herdev` | 130Herdev | cli_a979f9666d7c1bb3 | ~/.hermes/profiles/herdev | WSL2 |
| Hertes | 测试岗 | `hertes` | 130Hertes | cli_a97a13108bb85bd5 | ~/.hermes (default) | WSL2 |
| Hermod | 审核岗 | `hermod` | 130hermod | cli_a97ac89d603c5bc3 | ~/.hermes/profiles/hermod | WSL2 |
| herwin | Windows守护 | `hermes-win` | 130herwin | cli_a97aceb3a8b89bd4 | C:\hermes-win\home\ | Windows |

## 端口分配

| 端口 | 用途 | 团队 |
|------|------|------|
| 8891 | Bridge API | team-1 |
| 8892 | Bridge API | team-2（预留） |
| 8893 | Bridge API | team-3（预留） |

## 目录结构

```
WSL：
/home/yz01/.hermes/                       ← Hertes (default)
/home/yz01/.hermes/profiles/herdev/       ← herdev
/home/yz01/.hermes/profiles/hermod/       ← Hermod
/home/yz01/hermes-venv/                   ← 共享 Python 虚拟环境 (3.12.3, v0.10.0)
/home/yz01/.local/bin/                    ← 快捷命令

Windows：
C:\hermes-win\                            ← herwin 独立安装（源码+venv+home）

工作目录：
C:\tower-of-babel\hermes\                 ← Hertes
C:\tower-of-babel\hermes-herdev\          ← herdev
C:\tower-of-babel\hermes-hermod\          ← Hermod
C:\tower-of-babel\hermes-win\             ← herwin
```

## 安装与升级

### WSL2（共享 hermes-agent + named profile）

```bash
# 创建新实例
hermes profile create <name> --clone
# 编辑配置
vi ~/.hermes/profiles/<name>/.env      # 飞书凭证
vi ~/.hermes/profiles/<name>/SOUL.md   # 身份定义
# 创建快捷命令（参考 ~/.local/bin/herdev）
# 创建工作目录
mkdir /mnt/c/tower-of-babel/hermes-<name>
```

### Windows（独立安装）

参考 `team-watch/README.md` 中的隔离机制。

### 升级

- WSL2：升级 site-packages（`/home/yz01/hermes-venv/lib/python3.12/site-packages/`），所有 profile 共享
- Windows：升级 `C:\hermes-win\src\` 和 `C:\hermes-win\venv\`，独立于 WSL2

## .env 关键变量

```bash
FEISHU_APP_ID=          # 飞书应用 ID（每个实例不同）
FEISHU_APP_SECRET=      # 飞书应用密钥
FEISHU_BOT_NAME=        # 飞书群内机器人名
FEISHU_BOT_OPEN_ID=     # 机器人 Open ID（可留空，自动获取）
FEISHU_DOMAIN=feishu    # 中国版飞书
FEISHU_CONNECTION_MODE=websocket
FEISHU_GROUP_POLICY=open          # 必须设为 open
GATEWAY_ALLOW_ALL_USERS=true
BRIDGE_API_URL=http://127.0.0.1:8891  # 按团队端口分配
BRIDGE_API_TOKEN=                  # 按团队分配
```

## 踩坑记录

1. **FEISHU_GROUP_POLICY 必须设为 open**，默认 allowlist 为空会导致群消息被丢弃
2. **FEISHU_BOT_NAME/OPEN_ID 建议手动指定**，lark-oapi SDK 兼容问题可能导致自动获取失败
3. **改代码要改 site-packages 路径**，不是源码目录
4. **每个实例的飞书应用必须独立**，共用 App ID 会互踢 WebSocket
5. **谁都不碰主环境 env** — `~/.hermes/` 是 Hertes 的，其他实例用 named profile
6. **Bridge 端口按团队分配** — team-1 用 8891，team-2 用 8892，以此类推
7. **hermes-win 的 HERMES_GIT_BASH_PATH 必须设置**，否则可能找到 MSYS2 的 bash
8. **同租户不同 App 不冲突**，飞书事件按 App ID 路由，共用 App ID 才会互踢
9. **Windows checkpoint 需排除特殊文件**，`nul`/`*.msi`/`gateway.lock` 等会导致 `git add -A` 失败阻塞 agent
10. **Windows config.yaml 避免非 ASCII 字符**，GBK 默认编码会导致 cron job 无法读取配置

## 已清理

- nanobot 已于 2026-04-30 完全卸载
- Puck/Athena hermes-agent 版已于 2026-05-01 清理，迁移到 OpenClaw
- Hermes老大 profile 已于 2026-05-02 删除，App ID 转给 herdev
