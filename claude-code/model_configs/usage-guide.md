# Claude Code 使用说明

> 最后更新：2026-05-06

## 切换模型

通过替换配置文件切换提供商，两种配置位置：

| 场景 | 配置文件位置 | 作用范围 |
|------|------------|---------|
| 全局默认 | `C:\Users\yz01\.claude\settings.json` | 所有项目 |
| 项目级 | `<项目目录>\.claude\settings.local.json` | 仅当前项目 |

**优先级：项目级 > 全局**

### 使用方法

1. 从 `C:\tower-of-babel\claude-code\model_configs\` 选择对应文件
2. 复制到目标位置，替换 `env` 部分（全局）或整个文件（项目级）
3. 启动 `claude --dangerously-skip-permissions`

### 配置文件清单

| 文件名 | 提供商 | 用途 |
|--------|--------|------|
| `global-settings-xfyun.json` | 讯飞 MaaS | 复制到 `~/.claude/settings.json` 的 env |
| `global-settings-acw.json` | AI Code With | 复制到 `~/.claude/settings.json` 的 env |
| `global-settings-deepseek.json` | DeepSeek | 复制到 `~/.claude/settings.json` 的 env |
| `project-settings-xfyun.json` | 讯飞 MaaS | 复制到 `<项目>/.claude/settings.local.json` |
| `project-settings-acw.json` | AI Code With | 复制到 `<项目>/.claude/settings.local.json` |
| `project-settings-deepseek.json` | DeepSeek | 复制到 `<项目>/.claude/settings.local.json` |

> **全局配置**：只需替换 `env` 字段内容，保留 `permissions`、`hooks` 等其他字段。
> **项目配置**：直接覆盖整个文件，`settings.local.json` 不会提交 git。

## 提供商详情

### 讯飞 MaaS（当前全局默认）

- 模型：**astron-code-latest**（云端配置）
- API：`https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic`

### AI Code With

- 缺省模型：**claude-sonnet-4-6**
- 可选模型：`claude-opus-4-7`、`claude-opus-4-6`、`claude-sonnet-4-6`、`claude-haiku-4-5-20251001`
- API：`https://api.aicodewith.com`
- 切模型：改配置文件中 `ANTHROPIC_MODEL` 的值

### DeepSeek 官方（1M 上下文）

- 缺省模型：**deepseek-v4-pro**
- 可选模型：`deepseek-v4-flash`
- API：`https://api.deepseek.com/anthropic`
- 已设 `ANTHROPIC_MAX_CONTEXT_TOKENS=1000000`，无需手动配置

## 多实例并行

开多个终端窗口，每个在不同项目目录下用不同配置启动：

| 终端 | 目录 | 配置 | 用途 |
|------|------|------|------|
| 1 | 任意 | 全局讯飞 | 讯飞主力 |
| 2 | 项目A | 项目级 ACW | Opus 架构/评审 |
| 3 | 项目B | 项目级 DeepSeek | 1M 上下文 |

Windows Terminal 分屏：`Alt+Shift+D`

## 避免文件冲突

多实例同时改同一文件会冲突，解决方法：
- 用 worktree 隔离（Claude Code 内置 `EnterWorktree`）
- 或让每个实例负责不同文件/模块

## 常用命令

```bash
claude --dangerously-skip-permissions    # 默认启动（走全局配置）
claude -p "问题"                         # 单次提问
claude -c                                # 继续上次对话
claude --resume                          # 恢复会话
```

## 限制

- Claude Code 只支持 Anthropic API 格式，不支持 OpenAI 格式模型（GPT/Gemini 等）
- DeepSeek 官方同时支持 Anthropic 和 OpenAI 两种格式，所以可以接入
- ACW 代理的 DeepSeek 只支持 OpenAI 格式，不能接入 Claude Code（需用 Codex）
- 每个实例独立消耗 API 额度，并行越多消耗越大

## 项目守则

- 全局守则：`C:\tower-of-babel\CLAUDE.md` → `C:\Users\yz01\.claude\CLAUDE.md`
- 专属守则：`C:\tower-of-babel\claude-code\MY-RULES.md`
- 入职手册：`C:\tower-of-babel\public\announcements\ONBOARDING.md`
- 完整制度：`C:\tower-of-babel\public\policies\development-policy.md`
