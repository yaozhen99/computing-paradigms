# Codex CLI 使用说明

> 最后更新：2026-05-04

## 启动方式

通过 PowerShell profile 中的 `codex` 函数路由 provider：

```powershell
codex                         # 默认 gpt-5.5 (acw)
codex acw                     # acw → gpt-5.5
codex acw gpt-5.3-codex       # acw → Codex优化版
```

## 安装信息

- 版本：codex-cli 0.128.0
- 安装方式：`npm install -g @openai/codex`

## 配置（已完成）

### config.toml

位置：`~/.codex/config.toml`

```toml
model = "gpt-5.5"
model_provider = "acw"

[model_providers.acw]
name = "acw"
base_url = "https://api.aicodewith.com/v1"
supports_websockets = false
```

### PowerShell profile

位置：`$PROFILE`（`C:\Users\yz01\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`）

定义了 `codex` 函数，拦截第一个参数做 provider 路由。

### Provider 详情

| Provider | 默认模型 | API Base | Key 方式 |
|----------|---------|----------|---------|
| acw | gpt-5.5 | `https://api.aicodewith.com/v1` | codex login |

## 可用模型

| 模型 | Provider | 说明 |
|------|----------|------|
| gpt-5.5 | acw | 最新旗舰 |
| gpt-5.4 | acw | GPT 5.4 |
| gpt-5.3-codex | acw | Codex 编码优化版 |
| gpt-5.2 | acw | GPT 5.2 |

## 常用命令

```powershell
codex                              # 交互模式（默认 gpt-5.5）
codex exec "任务描述"               # 非交互执行
codex exec --skip-git-repo-check   # 非 git 目录中运行
codex -a untrusted                  # 只运行可信命令（默认）
codex -a never                      # 不需确认（谨慎）
```

## 踩坑记录

1. **必须设置 `supports_websockets = false`** — 代理不支持 WebSocket，Codex 默认用 WebSocket 调 Responses API，会报 400 错误
2. **必须用 `model_providers` 而非 `OPENAI_BASE_URL` 环境变量** — Codex 不读这个环境变量
3. **必须用 `codex login --with-api-key` 配置 key** — 仅在 config.toml 写 api_key 无效

## 与 Claude Code 的分工

| 工具 | 协议 | 适用模型 | 适用场景 |
|------|------|---------|---------|
| Claude Code | Anthropic API | Claude 家族 | 日常编码、重构、调试 |
| Codex CLI | OpenAI API | GPT/Codex 家族 | 代码生成、批量任务 |

## 注意事项

- Codex 使用 OpenAI Responses API 格式，与 Claude Code 的 Anthropic 格式不互通
- 代理不支持 WebSocket，`supports_websockets = false` 是必须的
- 多实例并行同样需要注意文件冲突，建议用 git worktree 隔离
- API 额度独立计费，并行越多消耗越大
