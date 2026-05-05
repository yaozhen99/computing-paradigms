# Tower of Babel 工具部

> 所有智能体共享的工具基础设施

## 使用方式

### Python
```python
from lib.python.babel_chat import chat

reply = chat("你好")                          # 默认provider
reply = chat("你好", provider="deepseek")      # 指定provider
reply = chat("写代码", provider="xunfei", model="astron-code-latest")
```

### PowerShell
```powershell
. C:\tower-of-babel\tools\bin\babel-chat.ps1
$reply = Babel-Chat "你好"
$reply = Babel-Chat "你好" -Provider "deepseek"
```

## 工具清单

| 工具 | 语言 | 位置 | 说明 | 状态 |
|------|------|------|------|------|
| babel-chat | Python/PS | bin/ | 统一聊天接口 | 🚧 开发中 |
| task-dispatch | PS | bin/ | 任务分发 | 📋 待开发 |
| audit-log | PS | bin/ | 审计查询 | 📋 待开发 |

## 外部工具

| 工具 | 版本 | 用途 | 安装方式 |
|------|------|------|----------|
| openai | latest | DeepSeek API | pip install openai |
| anthropic | latest | 讯飞MaaS | pip install anthropic |
| python-dotenv | latest | .env加载 | pip install python-dotenv |
| pyyaml | latest | YAML处理 | pip install pyyaml |
| watchdog | latest | 文件监听 | pip install watchdog |
| websocket-client | latest | 讯飞星火 | pip install websocket-client |

## 原则

1. **先搜后造** — 需要工具先搜现有方案
2. **薄封装优先** — 包一层比例重写好
3. **统一接口** — 对外接口必须一致
4. **审计内置** — 调用都记录日志

---

*维护者：Atlas 🏛️*
