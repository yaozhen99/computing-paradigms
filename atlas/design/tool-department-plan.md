# Tower of Babel 工具部规划

> 规划者：Atlas
> 日期：2026-04-21
> 状态：草案，待讨论

---

## 定位

工具部是 Tower of Babel 的基础设施层。所有智能体共享，不重复造轮子。

**三个来源**：
1. **拿来用** — 网上成熟的开源工具，直接集成
2. **包一层** — 在现有工具上写适配层，统一接口
3. **自己写** — 现有工具覆盖不了的，才自己造

## 工具分类

### 一、API 调用层（统一接口）

| 工具 | 来源 | 状态 | 说明 |
|------|------|------|------|
| babel_chat | 自己写 | 草案 | 统一聊天接口，多provider |
| openai-python | 拿来用 | 成熟 | OpenAI官方SDK，DeepSeek兼容 |
| anthropic-python | 拿来用 | 成熟 | Anthropic官方SDK |
| spark-python | 包一层 | 待开发 | 讯飞星火WebSocket封装 |

### 二、文件与数据

| 工具 | 来源 | 状态 | 说明 |
|------|------|------|------|
| python-dotenv | 拿来用 | 成熟 | .env文件加载 |
| pyyaml | 拿来用 | 成熟 | YAML读写 |
| watchdog | 拿来用 | 成熟 | 文件系统监听（CiviBBS邮件总线需要） |
| jq | 拿来用 | 成熟 | JSON处理（命令行） |

### 三、开发工具

| 工具 | 来源 | 状态 | 说明 |
|------|------|------|------|
| gh (GitHub CLI) | 拿来用 | 已安装 | GitHub操作 |
| claude (Claude Code) | 拿来用 | 已安装 | 编码智能体 |
| git | 拿来用 | 已安装 | 版本管理 |
| pytest | 拿来用 | 成熟 | 测试框架 |

### 四、安全与系统

| 工具 | 来源 | 状态 | 说明 |
|------|------|------|------|
| asr-hardening.ps1 | 自己写 | 已有 | Netdef ASR模块 |
| atlas_security_hardening.ps1 | 自己写 | 已有 | 安全加固脚本 |
| DPAPI加密模块 | 自己写 | 待开发 | Windows凭据加密 |

### 五、通信与协作

| 工具 | 来源 | 状态 | 说明 |
|------|------|------|------|
| CiviBBS mail_manager | 包一层 | 已有 | 邮件总线（待标准化） |
| Tower of Babel 任务文件 | 自己写 | 已有 | JSON任务分发 |
| webhook中继 | 待定 | 待评估 | 外部事件接入 |

### 六、智能体桥接

| 工具 | 来源 | 状态 | 说明 |
|------|------|------|------|
| claude --print | 拿来用 | 已用 | Atlas→Hermes通信 |
| Ollama API | 拿来用 | 已用 | NanoBot本地模型 |
| OpenClaw sessions | 拿来用 | 已用 | 子代理管理 |
| bridge.py | 待恢复 | 离线 | UI自动化桥接 |

## 工具部目录结构

```
C:\tower-of-babel\tools\
├── README.md                  # 工具清单和使用说明
├── bin/                       # 可执行脚本（加入PATH）
│   ├── babel-chat.ps1         # 统一聊天（PowerShell）
│   ├── babel-chat.py          # 统一聊天（Python）
│   ├── task-dispatch.ps1      # 任务分发
│   └── audit-log.ps1          # 审计查询
├── lib/                       # 库代码
│   ├── python/
│   │   ├── babel_chat/        # 统一聊天包
│   │   │   ├── __init__.py
│   │   │   ├── core.py
│   │   │   ├── providers/
│   │   │   └── credentials.py
│   │   └── requirements.txt
│   └── powershell/
│       ├── BabelChat.psm1     # PowerShell模块
│       └── providers/
├── external/                  # 外部工具（git clone / pip install）
│   ├── README.md              # 外部工具清单和安装说明
│   └── install.ps1            # 一键安装脚本
└── config.yaml                # 工具库配置
```

## 集成原则

1. **先搜后造** — 需要新工具时，先搜 npm/PyPI/GitHub 有没有现成的
2. **薄封装优先** — 能包一层解决的，不重写
3. **统一接口** — 不管底层用什么，对外接口必须一致
4. **版本锁定** — 外部工具记录版本号，避免升级破坏
5. **审计内置** — 每个工具的调用都记录到审计日志

## 外部工具评估流程

发现新工具时：

```
1. 搜索：npm/PyPI/GitHub 有没有？
2. 评估：star数、最近更新、许可证、依赖量
3. 试用：小规模测试
4. 集成：放入 external/，写适配层
5. 注册：更新 README 清单
```

## 下一步

| 优先级 | 动作 | 负责者 |
|--------|------|--------|
| P0 | 建目录结构 + README | Atlas |
| P1 | babel_chat Python版（deepseek + ollama） | Claude Code |
| P2 | babel_chat PowerShell版 | Atlas |
| P3 | 外部工具清单整理 | Atlas |
| P4 | install.ps1 一键安装 | Claude Code |

---

*规划者：Atlas 🏛️*
*版本：v0.1 草案*
