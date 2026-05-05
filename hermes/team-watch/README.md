# Team-Watch：herwin 独立守护

herwin 是 Windows 原生环境上独立运行的 Hermes 实例，不依赖 WSL2，与 Team-1 完全隔离。

## 实例信息

| 属性 | 值 |
|------|-----|
| 角色 | Windows 守护 |
| 飞书名 | 130herwin |
| App ID | cli_a97aceb3a8b89bd4 |
| HERMES_HOME | C:\hermes-win\home\ |
| 源码 | C:\hermes-win\src\ (v0.11.0) |
| Python | C:\hermes-win\venv\ (3.12.13) |
| 启动脚本 | C:\hermes-win\hermes.bat |

## 隔离机制

| 隔离维度 | herwin (Windows) | Team-1 (WSL2) |
|----------|-----------------|---------------|
| HERMES_HOME | C:\hermes-win\home\ | /home/yz01/.hermes/ |
| Python venv | C:\hermes-win\venv\ (3.12.13) | /home/yz01/hermes-venv/ (3.12.3) |
| 源码 | C:\hermes-win\src\ (v0.11.0) | site-packages (v0.10.0) |
| 配置文件 | C:\hermes-win\home\config.yaml | /home/yz01/.hermes/config.yaml |
| 用户级环境变量 | HERMES_HOME=C:\hermes-win\home | 无（使用默认 ~/.hermes） |

## 命令

```powershell
# 聊天
C:\hermes-win\hermes.bat chat

# Gateway
C:\hermes-win\hermes.bat gateway

# 直接调用
$env:HERMES_HOME = "C:\hermes-win\home"
C:\hermes-win\venv\Scripts\hermes.exe chat
```

## Windows 已知问题

### 1. 文件读取返回空内容（已修复 2026-05-01）

**根因**：`_wait_for_process` 中的非阻塞 `os.read()` 排空循环在 Windows 上与进程退出存在竞争条件。

**修复**（`C:\hermes-win\src\tools\` 下）：
- `file_operations.py`：shell 管道返回空输出时，自动回退到 Python `open()` / `os.path.getsize()` 直接读取
- `terminal_tool.py`：终端命令返回 `exit_code=0` 但 `output=""` 时，自动重试一次

### 2. Checkpoint 扫描整个 C:\ 盘（已修复 2026-04-30）

**根因**：`C:\hermes-win` 没有 `.git` 目录，git 向上查找到 `C:\` 作为 repo root。

**修复**：在 `C:\hermes-win` 执行 `git init`，添加 `.gitignore`，创建初始 commit。

### 3. Checkpoint `git add -A` 因 Windows 特殊文件失败（已修复 2026-05-02）

**根因**：checkpoint_manager 的 shadow git repo 执行 `git add -A` 时遇到 Windows 特殊文件：
- `nul`（Windows 设备名，git 无法 stat）
- `cloudflared.msi`（权限拒绝）
- `gateway.lock`/`gateway_state.json`（运行时锁定文件）

每次失败阻塞 agent 数秒，累积导致"死机"。

**修复**：
1. 更新 `checkpoint_manager.py` 的 `DEFAULT_EXCLUDES`，添加 Windows 特殊文件排除规则
2. 更新 shadow repo 的 `info/exclude`（`C:\hermes-win\home\checkpoints\2bc4156037f9b9ef\info\exclude`）
3. 更新 `.gitignore` 同步排除规则

### 4. Plugin YAML GBK 解码警告（未修复，不影响功能）

4 个 plugin.yaml 因 Windows 默认 GBK 编码无法解析，插件加载失败但不影响核心功能。

### 5. config.yaml GBK 解码导致 cron job 失败（已修复 2026-05-02）

**根因**：config.yaml 末尾注释使用 Unicode box-drawing 字符（─），Windows 默认 GBK 编码无法解析。

**修复**：将 Unicode 字符替换为 ASCII（`--`）。

## 注意事项

- herwin 独立运行，不与 WSL2 实例共享任何运行时资源
- HERMES_GIT_BASH_PATH 必须设置为 `C:\Program Files\Git\bin\bash.exe`
- herwin 不走 Bridge，不占用 team 端口
