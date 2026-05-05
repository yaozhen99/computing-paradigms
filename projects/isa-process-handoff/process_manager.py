"""
process_manager.py — ISA 进程管理核心（通用版）
================================================
CC 主备热切换的进程管理组件。任何项目需要 CC 进程持续运行+交接时，
将此文件复制到项目目录或通过 sys.path 引用即可使用。

核心能力：
1. claim_primary() — 声明自己是主进程（无参数版本自动发现 PID）
2. signal_kill(pid) — 请求看门狗杀掉指定进程
3. find_claude_processes() — 发现所有 Claude 进程
4. _find_own_claude_pid() — 5 级策略自动发现当前进程的 claude.exe PID
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime


# ── 项目根目录（可配置）─────────────────────────────────────────────
# 默认：此文件所在目录。使用时可通过 set_project_root() 指定目标项目。
_PROJECT_ROOT: Path = Path(__file__).resolve().parent

AUDIT_DIR = _PROJECT_ROOT / "audit"
ROLE_TOKEN_FILE = AUDIT_DIR / "role_token.json"
SIGNAL_DIR = _PROJECT_ROOT / "_system"


def set_project_root(root: str | Path):
    """设置项目根目录（影响 AUDIT_DIR、SIGNAL_DIR 等所有路径）。"""
    global _PROJECT_ROOT, AUDIT_DIR, ROLE_TOKEN_FILE, SIGNAL_DIR
    _PROJECT_ROOT = Path(root).resolve()
    AUDIT_DIR = _PROJECT_ROOT / "audit"
    ROLE_TOKEN_FILE = AUDIT_DIR / "role_token.json"
    SIGNAL_DIR = _PROJECT_ROOT / "_system"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── PowerShell CIM 查询（替代已废弃的 wmic）──────────────────────

def _ps_get_claude_procs() -> list[dict]:
    """用 PowerShell Get-CimInstance 查询所有 claude.exe 进程。
    返回 [{"pid": int, "mem": str, "creation_date": str, "command_line": str}, ...]
    """
    cmd = (
        'Get-CimInstance Win32_Process -Filter "Name=\'claude.exe\'" | '
        'Select-Object ProcessId, WorkingSetSize, CreationDate, CommandLine | '
        'ConvertTo-Json -Compress'
    )
    try:
        r = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=10
        )
        if not r.stdout.strip():
            return []
        data = json.loads(r.stdout)
        if isinstance(data, dict):
            data = [data]
        return [{
            "pid": p["ProcessId"],
            "mem": str(p["WorkingSetSize"]),
            "creation_date": p.get("CreationDate", ""),
            "command_line": p.get("CommandLine", ""),
        } for p in data]
    except Exception:
        return []


# ── 进程发现 ──────────────────────────────────────────────────────

def find_claude_processes() -> list[dict]:
    """发现所有 Claude CLI 进程（PID + 内存）。
    返回 [{"pid": int, "mem": str}, ...]
    """
    procs = _ps_get_claude_procs()
    return [{"pid": p["pid"], "mem": p["mem"]} for p in procs]


def identify_self() -> int | None:
    """通过内存大小识别当前进程（内存最大 = 上下文最长 = 当前活跃进程）。
    注意：新进程内存最小，此函数不适用于交接场景。
    """
    procs = find_claude_processes()
    if not procs:
        return None
    procs.sort(key=lambda p: int(p["mem"]), reverse=True)
    return procs[0]["pid"]


def _find_own_claude_pid() -> int | None:
    """5 级策略自动发现当前进程的 claude.exe PID。

    策略优先级：
    1. ISA_HANDOFF_ID 环境变量匹配 CommandLine
    2. 排除旧 PID（从 handoff.json），选内存最小的
    3. PowerShell CIM 按启动时间排序，选最新的
    4. identify_self() 内存最大
    5. os.getpid() 回退
    """
    # 策略 1：ISA_HANDOFF_ID 匹配
    handoff_id = os.environ.get("ISA_HANDOFF_ID")
    if handoff_id:
        procs = _ps_get_claude_procs()
        for p in procs:
            if handoff_id in p.get("command_line", ""):
                return p["pid"]

    # 策略 2：排除旧 PID，选内存最小的（新进程刚启动内存最小）
    handoff = _read_json(AUDIT_DIR / "handoff.json")
    old_pid = handoff.get("old_primary", {}).get("pid") if handoff else None
    if old_pid:
        procs = find_claude_processes()
        candidates = [p for p in procs if p["pid"] != old_pid]
        if candidates:
            candidates.sort(key=lambda p: int(p["mem"]))
            return candidates[0]["pid"]

    # 策略 3：PowerShell CIM 按启动时间排序
    procs = _ps_get_claude_procs()
    if procs:
        # CreationDate 格式：20260503210356.000000+480
        dated = [p for p in procs if p.get("creation_date")]
        if dated:
            dated.sort(key=lambda p: p["creation_date"], reverse=True)
            return dated[0]["pid"]

    # 策略 4：identify_self() 内存最大
    pid = identify_self()
    if pid:
        return pid

    # 策略 5：os.getpid() 回退
    return os.getpid()


# ── 角色管理 ──────────────────────────────────────────────────────

def claim_primary(pid: int | None = None) -> dict:
    """声明自己是主进程。无参数时自动发现 PID。"""
    if pid is None:
        pid = _find_own_claude_pid()
    if pid is None:
        return {"success": False, "error": "cannot_find_pid"}

    token = {
        "primary_pid": pid,
        "role": "global_ai",
        "claimed_at": datetime.now().isoformat(),
    }
    _write_json(ROLE_TOKEN_FILE, token)
    return {"success": True, "pid": pid}


def am_i_primary() -> bool:
    """检查自己是否是主进程。"""
    token = _read_json(ROLE_TOKEN_FILE)
    my_pid = _find_own_claude_pid() or os.getpid()
    return token.get("primary_pid") == my_pid


# ── 信号机制 ──────────────────────────────────────────────────────

def signal_kill(pid: int):
    """请求看门狗杀掉指定进程（写信号文件，即写即消）。"""
    signal_file = SIGNAL_DIR / f"signal_kill_{pid}.json"
    _write_json(signal_file, {
        "target_pid": pid,
        "requested_at": datetime.now().isoformat(),
        "reason": "handoff",
    })


def signal_start(task: str = ""):
    """请求看门狗启动新进程。"""
    signal_file = SIGNAL_DIR / f"signal_start_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    _write_json(signal_file, {
        "task": task,
        "requested_at": datetime.now().isoformat(),
    })


# ── 心跳 ──────────────────────────────────────────────────────────

def update_heartbeat(pid: int | None = None):
    """更新心跳文件（双文件同步）。"""
    if pid is None:
        pid = _find_own_claude_pid() or os.getpid()
    now = datetime.now().isoformat()

    # audit/heartbeat.json（watchdog.py 读）
    _write_json(AUDIT_DIR / "heartbeat.json", {
        "pid": pid,
        "status": "alive",
        "last_heartbeat": now,
    })

    # _system/system_state.json（watchdog.ps1 读）
    _write_json(SIGNAL_DIR / "system_state.json", {
        "pid": pid,
        "role": "global_ai",
        "last_heartbeat": now,
        "status": "alive",
    })


# ── 一键交接 ──────────────────────────────────────────────────────

def handoff(task: str = "继续待办任务"):
    """一键交接：压缩上下文 → 启动新进程 → 退休旧进程。"""
    # 1. 压缩上下文
    from utils_common.session_state import save_session_state
    save_session_state(task=task, progress=50, next_step="新进程读取 trading_memory.md 恢复上下文")

    # 2. 启动交接执行器
    my_pid = _find_own_claude_pid() or os.getpid()
    subprocess.Popen(
        [sys.executable, "handoff_executor.py", "--from-pid", str(my_pid), "--task", task],
        cwd=str(Path(__file__).resolve().parent.parent),
    )

    # 3. 标记自己准备退休
    token = _read_json(ROLE_TOKEN_FILE)
    token["role"] = "retired"
    _write_json(ROLE_TOKEN_FILE, token)
