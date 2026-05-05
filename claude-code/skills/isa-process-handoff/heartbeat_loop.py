"""
heartbeat_loop.py — ISA 心跳保活循环
=====================================
从 quant_system_v1.1_ths/heartbeat_loop.py 提炼。

新进程交接后持续运行，定期更新心跳保持存活。
看门狗检测到心跳正常就不会再唤醒新进程。
"""

import json
import os
import time
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
SYSTEM_STATE_FILE = PROJECT_DIR / "_system" / "system_state.json"
ROLE_TOKEN_FILE = PROJECT_DIR / "audit" / "role_token.json"

HEARTBEAT_INTERVAL = 60   # 秒
HEARTBEAT_TIMEOUT = 600   # 与看门狗一致


def update_heartbeat(pid: int):
    """更新双心跳文件"""
    now = datetime.now().isoformat()
    data = {"pid": pid, "role": "global_ai", "last_heartbeat": now, "status": "alive"}

    # _system/system_state.json（watchdog.ps1 读）
    SYSTEM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SYSTEM_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # audit/heartbeat.json（watchdog.py 读）
    hb = PROJECT_DIR / "audit" / "heartbeat.json"
    hb.parent.mkdir(parents=True, exist_ok=True)
    with open(hb, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_primary_pid():
    if not ROLE_TOKEN_FILE.exists():
        return None
    try:
        with open(ROLE_TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("primary_pid")
    except Exception:
        return None


def main():
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else os.getpid()
    print(f"[heartbeat_loop] PID={pid} starting (interval={HEARTBEAT_INTERVAL}s)")

    while True:
        # 检查自己是否还是 primary
        primary = get_primary_pid()
        if primary and primary != pid:
            print(f"[heartbeat_loop] No longer primary (current={primary}), exiting")
            break

        update_heartbeat(pid)
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[heartbeat_loop] {now} heartbeat updated")

        time.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    main()
