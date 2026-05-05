# Claude Code 使用说明

> 最后更新：2026-05-01

## 直接运行 `claude` 命令

直接运行 `claude` 走全局 `settings.json` 配置：

| | 值 |
|--|--|
| 提供商 | 讯飞 MaaS |
| 模型 | astron-code-latest |
| 上下文长度 | 由讯飞云端决定，Claude Code 侧默认 200K |
| API | `https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic` |

## 当前配置

### 双账号切换（通过启动脚本）

| 脚本 | 提供商 | 缺省模型 | 命令 |
|------|--------|---------|------|
| `claude` / `claude-xfyun` | 讯飞 MaaS | astron-code-latest | `claude-xfyun` |
| `claude-acw` | AI Code With | claude-sonnet-4-6 | `claude-acw` |
| `claude-deepseek` | DeepSeek 官方 | deepseek-v4-pro | `claude-deepseek` |

脚本位置：`C:\Users\yz01\bin\`

### AI Code With 可用模型

缺省：**claude-sonnet-4-6**

```bash
claude-acw                      # 缺省 sonnet-4-6
claude-acw claude-opus-4-7      # Opus 4.7
claude-acw claude-opus-4-6      # Opus 4.6
claude-acw claude-sonnet-4-6    # Sonnet 4.6
claude-acw claude-haiku-4-5-20251001  # Haiku 4.5
```

API Base: `https://api.aicodewith.com`
Key: `sk-acw-901a135d-16d3bff2fdaa7d86`

### DeepSeek 官方（1M 上下文）

缺省：**deepseek-v4-pro**

```bash
claude-deepseek                      # 缺省 deepseek-v4-pro
claude-deepseek deepseek-v4-flash    # Flash 快速版
```

API Base: `https://api.deepseek.com/anthropic`（Anthropic 格式）
Key: `sk-4b266b0d02564bdd8b91bee9e1fb773e`

> **1M 上下文特殊配置：** Claude Code 默认认为模型上下文为 200K，DeepSeek V4 支持 1M。
> 启动脚本已设置 `ANTHROPIC_MAX_CONTEXT_TOKENS=1000000`，无需手动配置。
> 如果不设此变量，Claude Code 会在 200K 处截断上下文，浪费 DeepSeek 的长文本能力。

### 讯飞 MaaS

缺省：**astron-code-latest**（模型在讯飞云端配置）

```bash
claude-xfyun                    # astron-code-latest（模型在讯飞云端配置）
```

API Base: `https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic`
Auth Token: `2eb8e6c687fbb47b855a82e8a5e81533:MjU3ZjM3NjkwZjc0MTViOTFmYmVhNWQx`

## 多实例并行

开多个终端窗口/标签页，每个跑不同脚本和模型即可：

| 终端 | 命令 | 用途 |
|------|------|------|
| 1 | `claude-xfyun` | 讯飞主力 |
| 2 | `claude-acw claude-opus-4-7` | Opus 架构/评审 |
| 3 | `claude-acw claude-sonnet-4-6` | Sonnet 快速编码 |
| 4 | `claude-deepseek` | DeepSeek V4（1M 上下文） |

Windows Terminal 分屏：`Alt+Shift+D`

## 避免文件冲突

多实例同时改同一文件会冲突，解决方法：
- 用 worktree 隔离（Claude Code 内置 `EnterWorktree`）
- 或让每个实例负责不同文件/模块

## 常用命令

```bash
claude                          # 默认启动（走全局 settings.json）
claude --model <model>          # 指定模型
claude -p "问题"                # 单次提问模式
claude -c                       # 继续上次对话
claude --resume                 # 恢复会话
```

## 限制

- Claude Code 只支持 Anthropic API 格式，不支持 OpenAI 格式模型（GPT/Gemini 等）
- DeepSeek 官方同时支持 Anthropic 和 OpenAI 两种格式，所以可以接入 Claude Code
- ACW 代理的 DeepSeek 只支持 OpenAI 格式，不能接入 Claude Code（需用 Codex）
- 每个实例独立消耗 API 额度，并行越多消耗越大
- 全局配置文件：`~/.claude/settings.json`

## 项目守则

- 全局守则：`C:\tower-of-babel\CLAUDE.md` → `C:\Users\yz01\.claude\CLAUDE.md`
- 专属守则：`C:\tower-of-babel\claude-code\MY-RULES.md`
- 入职手册：`C:\tower-of-babel\public\announcements\ONBOARDING.md`
- 完整制度：`C:\tower-of-babel\public\policies\development-policy.md`
