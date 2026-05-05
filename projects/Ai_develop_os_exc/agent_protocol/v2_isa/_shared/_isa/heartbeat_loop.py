"""
heartbeat_loop.py — ISA 心跳保活循环（通用版）
====================================

从 C:\\AI_exchange\\skills\\isa-process-handoff\\ 提炼并参数化。

被 Claude 进程调用后，以独立线程持续更新心跳文件。
主进程退出后心跳自动停止，看门狗据此判断进程存活。
"""

import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime


_this_dir = Path(__file__).resolve().parent
PROJECT_DIR = _this_dir.parent

CONFIG_FILE = PROJECT_DIR / "_system" / "project_config.json"


def _get_project_dir() -> Path:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            if "project_space" in config:
                return Path(config["project_space"])
    return PROJECT_DIR


PROJECT_DIR = _get_project_dir()
AUDIT_DIR = PROJECT_DIR / "audit"
SIGNAL_DIR = PROJECT_DIR / "_system"


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


_heartbeat_thread = None
_stop_event = threading.Event()


def _heartbeat_loop(pid: int, interval: int = 30):
    """后台线程：每 interval 秒更新一次心跳。"""
    while not _stop_event.is_set():
        now = datetime.now().isoformat()
        _write_json(AUDIT_DIR / "heartbeat.json", {
            "pid": pid,
            "status": "alive",
            "last_heartbeat": now,
        })
        _write_json(SIGNAL_DIR / "system_state.json", {
            "pid": pid,
            "role": "global_ai",
            "last_heartbeat": now,
            "status": "alive",
        })
        _stop_event.wait(interval)


def start_heartbeat(pid: int | None = None, interval: int = 30):
    """启动心跳保活线程。"""
    global _heartbeat_thread, _stop_event

    if pid is None:
        pid = os.getpid()

    _stop_event.clear()
    _heartbeat_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(pid, interval),
        daemon=True,
    )
    _heartbeat_thread.start()


def stop_heartbeat():
    """停止心跳保活线程。"""
    _stop_event.set()
    if _heartbeat_thread:
        _heartbeat_thread.join(timeout=5)


if __name__ == "__main__":
    # 直接运行时启动心跳循环（阻塞模式）
    pid = int(os.environ.get("ISA_PID", os.getpid()))
    interval = int(os.environ.get("ISA_HEARTBEAT_INTERVAL", "30"))
    print(f"Heartbeat loop started: pid={pid}, interval={interval}s")
    try:
        _heartbeat_loop(pid, interval)
    except KeyboardInterrupt:
        print("Heartbeat loop stopped")