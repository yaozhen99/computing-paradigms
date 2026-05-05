# ISA Process Handoff — CC 主备热切换（通用武器库组件）

> 归档位置：`C:\tower-of-babel\projects\isa-process-handoff\`
> 任何项目需要 CC 进程持续运行+交接时，直接引用此目录下的模块。

## 快速接入

```python
# 方式1：复制到目标项目
# 将 process_manager.py, handoff_executor.py, heartbeat_loop.py, watchdog.ps1
# 复制到目标项目目录

# 方式2：sys.path 引用
import sys
sys.path.insert(0, r"C:\tower-of-babel\projects\isa-process-handoff")
from process_manager import claim_primary, signal_kill, set_project_root

# 指定目标项目目录（影响 audit/ 和 _system/ 路径）
set_project_root(r"C:\tower-of-babel\projects\Ai_develop_os_exc")

# 声明主进程
claim_primary()

# 请求杀掉旧进程
signal_kill(old_pid)
```

## watchdog.ps1 配置

```powershell
# 设置环境变量指定项目目录
$env:ISA_PROJECT_DIR = "C:\tower-of-babel\projects\Ai_develop_os_exc"
# 或在 Task Scheduler 的 action 参数中设置
```

## 问题背景

Claude Code CLI 是一个交互式终端程序。当 AI 代理需要"重启"（上下文压缩、版本升级、进程恢复）时，必须启动新进程并让旧进程退出。核心挑战：

1. **新进程必须存活** — Claude CLI 的 `-p` 模式执行完就退出，无法持续运行
2. **新进程必须找到自己** — Python 子进程的 `os.getpid()` 返回的是 Python PID，不是 claude.exe PID
3. **旧进程必须被杀掉** — Claude CLI 进程有保护机制，`taskkill /F /T` 不一定能杀掉
4. **命令必须送达** — 新进程在交互模式下等待输入，需要把交接命令"打"进去
5. **Windows 编码陷阱** — PowerShell 默认 GBK 编码，中文提示词会被损坏

## 架构概览

```
┌─────────────┐     signal files      ┌──────────────┐
│  AI Process │ ─────────────────────► │ watchdog.ps1 │
│  (claude.exe│  signal_kill_*.json    │ (Task Sched) │
│   + Python) │  signal_start_*.json   │  2min cycle  │
│             │  system_state.json     │              │
└──────┬──────┘                        └──────────────┘
       │
       │ handoff_executor.py
       │ (独立子进程)
       │
       ▼
┌──────────────────────────────────────────────┐
│ 1. 写 .ps1 启动脚本（设置窗口标题）           │
│ 2. Start-Process powershell -NoExit          │
│ 3. 等待 claude.exe 出现                      │
│ 4. 剪贴板 ← 交接命令                         │
│ 5. AppActivate(PowerShell窗口) + Ctrl+V      │
│ 6. 等待 claim_primary 时间戳                  │
│ 7. 等待旧进程死亡                             │
└──────────────────────────────────────────────┘
```

## 关键设计决策

### 1. "像人一样操作" — PowerShell 窗口 + 剪贴板 + SendKeys

**不用**：stdin pipe、subprocess 传参、底层注入

**原因**：
- Claude CLI 在交互模式下从终端 stdin 读取，`subprocess.Popen(stdin=PIPE)` 在 pipe 关闭后进程退出
- `-p` 模式执行完就退出，无法持续运行
- PowerShell GBK 编码会损坏中文，导致 Claude 拒绝命令（误判为 prompt injection）

**做法**：
1. 写 `.ps1` 启动脚本，设置窗口标题 `ISA-Handoff-{uuid}`
2. `Start-Process powershell -NoExit -File launcher.ps1` 打开新窗口
3. Claude 在新窗口中进入交互模式，持续存活
4. 把交接命令写入文件 → 剪贴板 → AppActivate 窗口 → Ctrl+V → Enter

### 2. 窗口激活目标：PowerShell 窗口，不是 Claude 进程

**关键发现**：Claude CLI 没有自己的窗口——它运行在 PowerShell 终端内。`Get-Process claude` 的 `MainWindowTitle` 为空，`AppActivate` 找不到。

**解决**：启动脚本中设置 `$host.ui.RawUI.WindowTitle = "ISA-Handoff-{handoff_id}"`，然后用这个标题激活窗口。

### 3. PID 自发现：5 级策略

新进程需要知道自己的 claude.exe PID 来 claim_primary。`os.getpid()` 返回 Python PID，不是 claude.exe PID。

| 优先级 | 策略 | 场景 |
|:---|:---|:---|
| 1 | ISA_HANDOFF_ID 环境变量匹配 CommandLine | 交接时 handoff_executor 传入唯一 ID |
| 2 | 排除旧 PID，选内存最小的 | 交接场景，新进程内存最小 |
| 3 | PowerShell CIM 按启动时间排序 | 新进程启动时间最新 |
| 4 | identify_self() 内存最大 | 长期运行进程 |
| 5 | os.getpid() 回退 | 最后手段 |

### 4. 交接确认：时间戳比较，不是 PID 匹配

旧问题：`subprocess.Popen` 返回 cmd.exe 包装进程的 PID，不是 claude.exe。等特定 PID 出现在 role_token 中永远等不到。

**解决**：`handoff_start_time` 在启动新进程**之前**记录，然后等待 `role_token.claimed_at >= handoff_start_time`。只要有人 claim 了就算成功。

### 5. 提示词用英文

PowerShell GBK 编码会损坏中文。新 Claude 进程看到乱码会拒绝执行（误判为 prompt injection）。交接提示词全部用英文。

### 6. 心跳双文件同步

- `audit/heartbeat.json` — watchdog.py 读写
- `_system/system_state.json` — watchdog.ps1 读写
- 两个文件必须同步更新，否则看门狗误判 AI 死亡

## 文件清单

| 文件 | 职责 |
|:---|:---|
| `process_manager.py` | 进程管理核心：claim_primary、signal_kill、find_claude_processes、_find_own_claude_pid、set_project_root |
| `handoff_executor.py` | 交接执行器：启动新进程 + 输入命令 + 等待确认（支持 --project-dir 参数） |
| `heartbeat_loop.py` | 心跳保活循环：新进程完成任务后持续运行 |
| `watchdog.ps1` | 极简看门狗：处理信号文件 + 心跳超时唤醒（通过 ISA_PROJECT_DIR 环境变量配置项目目录） |

## 交接流程时序

```
T+0s   handoff_executor 启动，记录 handoff_start_time
T+1s   写 launcher.ps1（设置窗口标题）
T+1s   Start-Process powershell -NoExit -File launcher.ps1
T+3s   claude.exe 出现（find_claude_processes 检测到新 PID）
T+11s  剪贴板 ← 交接命令
T+16s  AppActivate(窗口标题) + Ctrl+V + Enter
T+20s  新进程执行 claim_primary()，role_token.claimed_at 更新
T+20s  handoff_executor 检测到 claimed_at >= handoff_start_time ✓
T+20s  新进程执行 signal_kill(old_pid)
T+22s  watchdog.ps1 处理 signal_kill，taskkill 旧进程
T+22s  handoff_executor 检测到旧进程死亡 ✓
T+22s  交接完成，handoff_phase = "completed"
```

实测最快 14 秒完成交接。

## 踩坑记录

### wmic 在 Windows 11 + Python 3.14 上不可用
`FileNotFoundError` — wmic 已从 Windows 11 移除。迁移到 PowerShell CIM：`Get-CimInstance Win32_Process`。

### identify_self() 内存最大策略反了
新进程刚启动内存最小，`identify_self()` 返回旧进程 PID。修复：交接场景排除旧 PID 后选内存最小的。

### -p 模式 vs 交互模式
- `-p "prompt"` — 执行完退出，进程不存活
- 无 `-p` — 交互模式，需要 TTY，进程存活
- 位置参数 `claude "prompt"` — 没有 TTY 时也会退出

### PowerShell 引号地狱
嵌套引号在 `-ArgumentList` 中解析错误。解决：写 `.ps1` 脚本文件，不在命令行中嵌套引号。

### Claude CLI 进程无法被 taskkill 杀死
即使 `/F /T`，进程可能有保护。解决：用 watchdog.ps1 的 signal_kill 机制，或新进程直接 `signal_kill()` 让看门狗代杀。

## 适用场景

此方案适用于任何需要 Claude CLI 进程持续运行并支持热交接的场景：
- AI 代理长期运行（交易系统、监控系统）
- 上下文压缩后重启
- 进程异常恢复
- 版本升级切换

## 依赖

- Windows 10/11
- Claude Code CLI（npm 安装）
- PowerShell 5.1+
- Python 3.10+
- Task Scheduler（watchdog.ps1 定时任务）
