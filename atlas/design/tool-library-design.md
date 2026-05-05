# Tower of Babel 统一工具库设计

> 设计者：Atlas
> 日期：2026-04-21
> 状态：草案，待讨论

---

## 问题

当前每个智能体调用外部 API 的方式不同：

| 智能体 | 语言 | 调用方式 | 问题 |
|--------|------|----------|------|
| Atlas | PowerShell | Invoke-RestMethod | 每次手写headers/body |
| NanoBot | PowerShell | Invoke-RestMethod | 同上，还重复写认证 |
| Claude Code | CLI | claude --print | 只能调 Anthropic 协议 |
| CiviBBS | Python | spark_model.py / ai_model.py | 已有适配器，但独立于工具库 |

**痛点**：
1. 每次调 API 都要重写认证逻辑
2. 不同协议（OpenAI/Anthropic/WebSocket）各自实现
3. 没有统一的错误处理和重试
4. 没有统一的调用审计

## 设计目标

1. **一个接口，多种协议** — 调用者不关心底层是 OpenAI/Anthropic/WebSocket
2. **凭据自动注入** — 从环境变量/配置文件自动读取，调用者不碰 Key
3. **跨语言可用** — Python + PowerShell 双版本，覆盖所有智能体
4. **调用审计** — 谁在什么时候调了什么 API，记录到 Tower of Babel 日志

## 架构

```
tower-of-babel/tools/
├── README.md              # 使用文档
├── python/
│   ├── babel_chat.py      # 统一聊天接口
│   ├── providers/
│   │   ├── deepseek.py    # DeepSeek (OpenAI协议)
│   │   ├── xunfei_maaS.py # 讯飞MaaS (Anthropic协议)
│   │   ├── xunfei_spark.py# 讯飞星火 (WebSocket协议)
│   │   └── ollama.py      # Ollama (本地HTTP)
│   ├── credentials.py     # 凭据管理（从环境变量/配置读取）
│   └── audit.py           # 调用审计
├── powershell/
│   ├── Babel-Chat.ps1     # 统一聊天接口
│   ├── providers/
│   │   ├── DeepSeek.ps1   # DeepSeek
│   │   ├── XunfeiMaaS.ps1 # 讯飞MaaS
│   │   └── Ollama.ps1     # Ollama
│   ├── Credentials.ps1    # 凭据管理
│   └── Audit.ps1          # 调用审计
└── config.yaml            # 工具库配置（provider列表、默认模型等）
```

## 核心接口

### Python

```python
from babel_chat import chat

# 最简调用 — 自动选provider和凭据
reply = chat("你好")

# 指定provider
reply = chat("你好", provider="deepseek")

# 指定模型
reply = chat("写个排序算法", provider="xunfei", model="astron-code-latest")

# 带系统提示
reply = chat("分析这段代码", system="你是代码审查专家", provider="deepseek")

# 带上下文（多轮）
reply = chat("继续", context=[{"role": "user", "content": "..."}, ...])
```

### PowerShell

```powershell
# 最简调用
$reply = Babel-Chat "你好"

# 指定provider
$reply = Babel-Chat "你好" -Provider "deepseek"

# 指定模型
$reply = Babel-Chat "写个排序算法" -Provider "xunfei" -Model "astron-code-latest"

# 带系统提示
$reply = Babel-Chat "分析这段代码" -System "你是代码审查专家"
```

## 凭据管理

```python
# credentials.py — 自动从以下位置读取，调用者无需关心
# 1. 环境变量（优先）
# 2. C:\tower-of-babel\tools\config.yaml
# 3. C:\tower-of-babel\public\.env

# 凭据映射
CREDENTIAL_MAP = {
    "deepseek": "DEEPSEEK_API_KEY",
    "xunfei_maas": "XUNFEI_API_KEY",      # Anthropic协议
    "xunfei_spark": "XUNFEI_API_KEY",     # WebSocket协议，额外需要APP_ID
    "ollama": "OLLAMA_API_KEY",
}
```

## 调用审计

```python
# audit.py — 记录到 Tower of Babel 日志
# 格式：timestamp | caller | provider | model | tokens_in | tokens_out | latency_ms

# 写入 C:\tower-of-babel\atlas\logs\api-audit.jsonl
{"ts":"2026-04-21T17:50:00","caller":"nanobot","provider":"deepseek","model":"deepseek-chat","tokens_in":15,"tokens_out":8,"latency_ms":2146}
```

## 降级策略

```python
# 如果主provider不可用，自动降级
FALLBACK_CHAIN = {
    "deepseek": ["ollama:qwen2.5:7b", "ollama:qwen2.5:3b"],
    "xunfei_maas": ["deepseek:deepseek-chat"],
    "xunfei_spark": ["deepseek:deepseek-chat"],
}
```

## 实现计划

| 阶段 | 内容 | 负责者 |
|------|------|--------|
| P1 | Python版 babel_chat + deepseek + ollama provider | Claude Code |
| P2 | PowerShell版 Babel-Chat + deepseek provider | Atlas |
| P3 | xunfei_spark provider (WebSocket) | Claude Code |
| P4 | xunfei_maas provider (Anthropic协议) | Claude Code |
| P5 | 凭据管理 + 审计日志 | Claude Code |
| P6 | 降级策略 + 健康检查 | Claude Code |

## 与 CiviBBS 的关系

CiviBBS 已有 `ai_model.py` + `spark_model.py`，功能与本工具库重叠。
**策略**：工具库稳定后，CiviBBS 改为依赖工具库，而不是自己实现 provider。
这是"Tower of Babel 是基础设施，CiviBBS 是应用"的体现。

---

*设计者：Atlas 🏛️*
*版本：v0.1 草案*
*待 Tony 和 Hermes 审阅*
