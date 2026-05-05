"""
handoff_executor.py — ISA 交接执行器
====================================
从 quant_system_v1.1_ths/handoff_executor.py 提炼。

被主进程触发后独立运行，负责：
1. 启动新的 Claude CLI 进程（在 PowerShell 窗口中交互模式）
2. 通过剪贴板 + SendKeys 输入交接命令
3. 等待新进程 claim_primary
4. 确认新进程杀掉旧进程
5. 退出

关键约束：新进程必须杀掉旧进程才算交接完成。
"""

import subprocess
import sys
import os
import json
import time
import uuid
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.join(PROJECT_DIR, "audit")
ROLE_TOKEN_FILE = os.path.join(AUDIT_DIR, "role_token.json")
HANDOFF_FILE = os.path.join(AUDIT_DIR, "handoff.json")
LOG_FILE = os.path.join(PROJECT_DIR, "logs", "handoff_executor.log")


def _log(msg: str):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def _read_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_claude_cli() -> str:
    """找到 Claude CLI 可执行文件"""
    cli = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming")),
        "npm", "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe"
    )
    if os.path.exists(cli):
        return cli
    return "claude"


def build_handoff_prompt(old_pid: int, task: str) -> str:
    """Build handoff prompt in English to avoid GBK encoding corruption in PowerShell.

    old_pid must be the Claude CLI PID (not Python subprocess PID).
    The new process auto-discovers its own PID via claim_primary().
    After completing tasks, starts heartbeat_loop.py to stay alive.
    """
    return (
        f"ISA Handoff — {datetime.now().isoformat()}\n\n"
        f"You are the new primary ISA process. Old process PID={old_pid}.\n\n"
        f"Execute these steps in order:\n"
        f"1. from utils_common.process_manager import claim_primary, signal_kill\n"
        f"2. claim_primary()  # auto-discover PID and claim primary role\n"
        f"3. signal_kill({old_pid})  # ask watchdog to kill old process\n"
        f"4. Read memory/trading_memory.md to restore context\n"
        f"5. Update watchdog heartbeat: python watchdog.py --update-heartbeat\n"
        f"6. Check pending tasks and continue execution\n"
        f"7. After tasks done, run: python heartbeat_loop.py  # keep process alive, do NOT exit\n\n"
        f"Current task: {task}\n"
    )


def _is_pid_alive(pid: int) -> bool:
    """检查 PID 是否还活着"""
    try:
        r = subprocess.run(
            ["cmd.exe", "//c", f"tasklist /FI \"PID eq {pid}\""],
            capture_output=True, text=True, timeout=5
        )
        return str(pid) in r.stdout
    except Exception:
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ISA Handoff Executor")
    parser.add_argument("--from-pid", type=int, required=True, help="Old process PID to terminate")
    parser.add_argument("--task", type=str, default="Continue pending tasks", help="Task for new process")
    args = parser.parse_args()

    old_pid = args.from_pid
    task = args.task

    _log(f"Handoff executor started: old_pid={old_pid}, task={task}")

    # 记录交接开始时间（必须在启动新进程之前）
    handoff_start_time = datetime.now().isoformat()

    # 1. 启动新的 Claude CLI 进程
    cli = find_claude_cli()
    prompt = build_handoff_prompt(old_pid, task)
    handoff_id = f"isa_{uuid.uuid4().hex[:8]}"

    _log(f"Starting new process: {cli}, handoff_id={handoff_id}")
    try:
        full_prompt = f"[HANDOFF_ID={handoff_id}] {prompt}"

        # 写交接命令到文件（供剪贴板读取）
        handoff_cmd_file = os.path.join(PROJECT_DIR, "_system", "handoff_command.txt")
        os.makedirs(os.path.dirname(handoff_cmd_file), exist_ok=True)
        with open(handoff_cmd_file, "w", encoding="utf-8") as f:
            f.write(full_prompt)
        _log(f"Handoff command written: {handoff_cmd_file}")

        # 写 .ps1 启动脚本：设置窗口标题 + 启动 claude 交互模式
        window_title = f"ISA-Handoff-{handoff_id}"
        launcher_ps1 = os.path.join(PROJECT_DIR, "_system", "handoff_launcher.ps1")
        with open(launcher_ps1, "w", encoding="utf-8-sig") as f:
            f.write(f'$host.ui.RawUI.WindowTitle = "{window_title}"\n')
            f.write(f'Set-Location "{PROJECT_DIR}"\n')
            f.write(f'& "{cli}" --dangerously-skip-permissions\n')
        _log(f"Launcher script written: {launcher_ps1}, window_title={window_title}")

        # 打开 PowerShell 窗口执行启动脚本（-NoExit 保证窗口不关闭）
        subprocess.Popen(
            ["powershell", "-Command",
             f'Start-Process powershell '
             f'-ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-File","{launcher_ps1}"'],
            cwd=PROJECT_DIR,
        )
        _log("PowerShell window opened, Claude interactive mode starting...")

        # 2. 等 Claude 进程出现
        from utils_common.process_manager import find_claude_processes
        procs_before = {p["pid"] for p in find_claude_processes()}
        new_pid = None
        for attempt in range(30):
            time.sleep(2)
            procs_now = find_claude_processes()
            new_procs = [p for p in procs_now if p["pid"] not in procs_before]
            if new_procs:
                new_procs.sort(key=lambda p: int(p["mem"]))
                new_pid = new_procs[0]["pid"]
                break

        if new_pid is None:
            raise RuntimeError("New process did not appear within 60 seconds")

        _log(f"Claude process started: PID={new_pid}")

        # 3. 等 Claude 交互模式稳定，然后通过剪贴板+SendKeys 输入交接命令
        time.sleep(8)

        # 把交接命令复制到剪贴板
        clip_ps1 = os.path.join(PROJECT_DIR, "_system", "set_clipboard.ps1")
        with open(clip_ps1, "w", encoding="utf-8-sig") as f:
            f.write(f'$text = Get-Content -Path "{handoff_cmd_file}" -Raw -Encoding UTF8\n')
            f.write('Set-Clipboard -Value $text\n')
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", clip_ps1],
            capture_output=True, text=True, timeout=5
        )
        time.sleep(0.5)

        # 激活 PowerShell 窗口（用窗口标题精确匹配）
        activate_ps1 = os.path.join(PROJECT_DIR, "_system", "activate_window.ps1")
        with open(activate_ps1, "w", encoding="utf-8-sig") as f:
            f.write(f'$title = "{window_title}"\n')
            f.write('$shell = New-Object -ComObject WScript.Shell\n')
            f.write('$result = $shell.AppActivate($title)\n')
            f.write('if ($result) {\n')
            f.write('    Write-Output "activated_by_title"\n')
            f.write('} else {\n')
            f.write('    # Fallback: find newest PowerShell window\n')
            f.write('    $ps = Get-Process powershell -ErrorAction SilentlyContinue | ')
            f.write('Sort-Object StartTime -Descending | Select-Object -First 1\n')
            f.write('    if ($ps -and $ps.MainWindowHandle -ne 0) {\n')
            f.write('        Add-Type @"\n')
            f.write('        using System;\n')
            f.write('        using System.Runtime.InteropServices;\n')
            f.write('        public class Win32Helper {\n')
            f.write('            [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);\n')
            f.write('            [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);\n')
            f.write('        }\n')
            f.write('@@\n')
            f.write('        [Win32Helper]::ShowWindow([IntPtr]$ps.MainWindowHandle, 9)\n')
            f.write('        [Win32Helper]::SetForegroundWindow([IntPtr]$ps.MainWindowHandle)\n')
            f.write('        Write-Output "activated_by_hwnd"\n')
            f.write('    } else {\n')
            f.write('        Write-Output "activation_failed"\n')
            f.write('    }\n')
            f.write('}\n')
        r = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", activate_ps1],
            capture_output=True, text=True, timeout=10
        )
        _log(f"Window activation result: {r.stdout.strip()}")
        time.sleep(1)

        # Ctrl+V 粘贴
        subprocess.run(
            ["powershell", "-Command",
             '(New-Object -ComObject WScript.Shell).SendKeys("^v")'],
            capture_output=True, text=True, timeout=5
        )
        time.sleep(0.5)

        # 回车提交
        subprocess.run(
            ["powershell", "-Command",
             '(New-Object -ComObject WScript.Shell).SendKeys("{ENTER}")'],
            capture_output=True, text=True, timeout=5
        )
        _log(f"Handoff command entered, handoff_id={handoff_id}")
    except Exception as e:
        _log(f"Failed to start new process: {e}")
        sys.exit(1)

    # 4. 写 handoff.json
    state = {
        "primary": {
            "pid": new_pid,
            "role": "primary",
            "status": "spawning",
            "registered_at": handoff_start_time,
            "took_over_from": old_pid,
            "handoff_id": handoff_id,
        },
        "old_primary": {
            "pid": old_pid,
            "status": "waiting_to_be_killed",
        },
        "handoff_phase": "new_process_spawned",
        "handoff_executor_pid": os.getpid(),
        "handoff_start_time": handoff_start_time,
    }
    _write_json(HANDOFF_FILE, state)

    # 5. 等待新进程 claim_primary（最多60秒）
    _log("Waiting for new process to claim_primary...")
    claim_timeout = 60
    claim_start = time.time()
    claimed = False

    while time.time() - claim_start < claim_timeout:
        token = _read_json(ROLE_TOKEN_FILE)
        claimed_at = token.get("claimed_at", "")
        if claimed_at and claimed_at >= handoff_start_time and token.get("role") != "retired":
            claimed = True
            _log(f"New process claimed primary (claimed_at={claimed_at})")
            break
        time.sleep(2)

    if not claimed:
        _log(f"New process PID={new_pid} did not claim_primary within {claim_timeout}s")
        state["handoff_phase"] = "claim_timeout"
        _write_json(HANDOFF_FILE, state)
        sys.exit(1)

    # 6. 等待新进程杀掉旧进程（最多60秒）
    _log(f"Waiting for old process PID={old_pid} to be killed...")
    kill_timeout = 60
    kill_start = time.time()
    killed = False

    while time.time() - kill_start < kill_timeout:
        if not _is_pid_alive(old_pid):
            killed = True
            _log(f"Old process PID={old_pid} terminated")
            break
        time.sleep(2)

    if not killed:
        _log(f"Old process PID={old_pid} not terminated, handoff failed!")
        state["handoff_phase"] = "kill_failed"
        state["old_primary"]["status"] = "still_alive"
        _write_json(HANDOFF_FILE, state)
        sys.exit(1)

    # 7. 交接完成
    state["handoff_phase"] = "completed"
    state["handoff_completed_at"] = datetime.now().isoformat()
    state["old_primary"]["status"] = "killed"
    _write_json(HANDOFF_FILE, state)

    _log(f"Handoff completed: new_pid={new_pid}, old_pid={old_pid} terminated")
    print(f"Handoff completed: new_pid={new_pid}, old_pid={old_pid} terminated")


if __name__ == "__main__":
    main()
