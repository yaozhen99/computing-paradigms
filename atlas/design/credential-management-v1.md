# 凭据管理方案 v1.0

> 制定者：Atlas
> 日期：2026-04-21
> 状态：待 Tony 确认

---

## 现状盘点

### 凭据分布

| 凭据 | 存放位置 | 安全等级 | 风险 |
|------|----------|----------|------|
| XUNFEI_API_KEY | 用户环境变量 | 中 | 明文，进程可读 |
| DEEPSEEK_API_KEY | 用户环境变量 | 中 | 明文，进程可读 |
| OLLAMA_API_KEY | 用户环境变量 | 低 | 本地服务，风险低 |
| ANTHROPIC_AUTH_TOKEN | Claude Code settings.json | 中 | 明文，文件可读 |
| OpenClaw API Key | openclaw.json | 中 | 明文，文件可读 |
| GitHub Token | Windows凭据管理器 | 高 ✅ | DPAPI加密，安全 |
| 讯飞+DeepSeek Key | CiviBBS config.yaml | 低 | 本地文件，.gitignore已排除 |
| xunfei_ket -2.txt | 桌面 | 极低 ⚠️ | 明文，任何人可见 |

### 问题

1. **桌面明文文件**：`xunfei_ket -2.txt` 必须删除（key已在环境变量中）
2. **配置文件明文**：config.yaml 含明文key（.gitignore已排除，不会泄露到GitHub）
3. **环境变量明文**：所有key对当前用户的所有进程可见
4. **无统一管理**：每个应用各自存放，没有中心化凭据管理

## 方案：环境变量 + .env 文件 + 访问审计

### 原则

1. **凭据不落地明文文件**（R4红线）
2. **代码中绝不硬编码**
3. **.gitignore 排除所有含凭据的文件**
4. **环境变量是当前最实用的方案**（Windows DPAPI vault需要C#代码，成本高）
5. **审计谁用了什么key**

### 具体措施

#### 立即执行

| # | 操作 | 状态 |
|---|------|------|
| 1 | 删除桌面 `xunfei_ket -2.txt` | 待Tony确认 |
| 2 | 确认 `.gitignore` 排除所有含key文件 | ✅ 已确认 |
| 3 | 确认 `config.example.yaml` 只有占位符 | 需验证 |
| 4 | 建立凭据清单（本文件） | ✅ |

#### 中期改进

| # | 操作 | 说明 |
|---|------|------|
| 5 | CiviBBS config.yaml 改为从环境变量读取 | `os.environ.get('DEEPSEEK_API_KEY')` |
| 6 | 建立 `.env` 文件规范 | `.env` 在 .gitignore 中，应用启动时加载 |
| 7 | 凭据使用审计日志 | 记录哪个智能体在什么时候用了哪个key |

#### 远期（CiviBBS 引擎就绪后）

| # | 操作 | 说明 |
|---|------|------|
| 8 | KeyKeeper 智能体 | 专门管理凭据的智能体，通过邮件总线分发临时token |
| 9 | DPAPI 加密存储 | Windows原生加密，需要C#工具或PowerShell模块 |
| 10 | 凭据轮换机制 | 定期更换API Key |

### 凭据-智能体映射

| 智能体 | 使用的凭据 | 用途 |
|--------|-----------|------|
| Atlas (OpenClaw) | XUNFEI_API_KEY (6852cd32...) | 讯飞星火模型 |
| Claude Code | ANTHROPIC_AUTH_TOKEN (2eb8e6c...) | Xunfei Coding Plan |
| NanoBot | DEEPSEEK_API_KEY (sk-4b266...) | DeepSeek-chat |
| CiviBBS | DEEPSEEK_API_KEY + XUNFEI_API_KEY | AI聊天/讨论 |

### .env 文件规范

位置：`C:\tower-of-babel\public\.env`（已 .gitignore 排除）

```env
# Tower of Babel 凭据（不提交到任何仓库）
XUNFEI_API_KEY=6852cd32...
DEEPSEEK_API_KEY=sk-4b266...
OLLAMA_API_KEY=ollama-local
```

应用启动时：
```python
from dotenv import load_dotenv
load_dotenv("C:/tower-of-babel/public/.env")
```

---

*版本：v1.0 | 2026-04-21 | Atlas 🏛️*
*待确认后执行*
