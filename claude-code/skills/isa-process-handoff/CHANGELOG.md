# ISA Process Handoff — 实战踩坑与修复记录

## 2026-05-03 主备交接完整验证通过

### 7 个断点修复

| # | 断点 | 根因 | 修复 |
|:--|:---|:---|:---|
| 1 | claim_primary() 需要手动传 PID | identify_self() 内存最大策略对新进程反了 | claim_primary() 无参数版本 + _find_own_claude_pid() 5级策略 |
| 2 | handoff_executor 等待错误 PID | subprocess.Popen 返回 cmd.exe 包装 PID | 等待条件改为时间戳：claimed_at >= handoff_start_time |
| 3 | watchdog.ps1 用 cmd.exe 包装 | 多一层 cmd 导致 PID 不对 | 直接 Start-Process claude.exe |
| 4 | watchdog --update-heartbeat 被阻断 | 新进程未 claim，am_i_primary() 返回 False | --update-heartbeat 跳过 am_i_primary 检查 |
| 5 | wake_me.py 同步阻塞 | subprocess.run 卡住看门狗 | 改用 subprocess.Popen 异步 |
| 6 | 心跳双文件不同步 | watchdog.py 写 audit/heartbeat.json，PS 看门狗读 _system/system_state.json | 同步更新两个文件 |
| 7 | 新进程内存最小，identify_self() 返回旧 PID | 启发式策略不适用交接场景 | ISA_HANDOFF_ID 环境变量 + 排除旧 PID 策略 |

### 交接模式修复：-p → 交互模式

- `-p` 模式：执行完提示词就退出，新进程无法持续运行
- 修复：改为 PowerShell -NoExit 窗口 + 交互模式，Claude 执行完 prompt 后进入交互模式，进程持续存活

### wmic → PowerShell CIM 迁移

- wmic 在 Python 3.14 / Windows 11 上 FileNotFoundError
- 迁移到 Get-CimInstance Win32_Process

### 窗口激活修复

- **问题**：AppActivate 找不到 Claude 进程窗口（Claude CLI 没有自己的窗口，运行在 PowerShell 终端内）
- **修复**：
  1. 启动脚本设置 `$host.ui.RawUI.WindowTitle = "ISA-Handoff-{handoff_id}"`
  2. AppActivate 用窗口标题精确匹配
  3. 回退：按启动时间找最新 PowerShell 窗口，用 SetForegroundWindow 激活

### 中文编码崩溃

- PowerShell 默认 GBK 编码损坏中文提示词
- 新 Claude 进程看到乱码拒绝执行（误判 prompt injection）
- 修复：交接提示词全部用英文

### handoff_start_time 时序修复

- handoff_start_time 在启动新进程之后才赋值
- 如果新进程 claim 得快，claimed_at < handoff_start_time，交接误判失败
- 修复：handoff_start_time 移到启动新进程之前

### 实测结果

- 完整交接循环：14 秒完成
- 交接链：启动 → claim → 存活 → 心跳更新 → 旧进程死亡
- 新进程 PID=11324 正确 claim_primary + 持续存活

## 通用经验

1. **Windows 进程管理不要用 wmic** — 已废弃，用 PowerShell CIM
2. **Claude CLI 交互模式是唯一能让进程存活的方式** — -p 模式执行完就退出
3. **PowerShell 编码陷阱** — 默认 GBK，中文必乱码，用英文或 UTF-8 BOM .ps1 文件
4. **窗口激活要找 PowerShell 窗口而非 Claude 进程** — Claude 没有自己的窗口
5. **时间戳比较比 PID 匹配更可靠** — 避免 cmd.exe 包装 PID 问题
6. **心跳双文件必须同步** — Python 和 PowerShell 看门狗读不同文件
7. **信号文件即写即消** — 避免重复处理
