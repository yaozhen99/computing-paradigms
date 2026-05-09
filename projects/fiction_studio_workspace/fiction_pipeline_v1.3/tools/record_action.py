import argparse
import json

from studio_core import ROOT, find_window, load_window_registry, now_iso


LOG_PATHS = {
    "window": ROOT / "_logs/window_actions.md",
    "editorial": ROOT / "_logs/editorial_log.md",
    "canon": ROOT / "_logs/canon_change_log.md",
    "asset": ROOT / "_logs/asset_usage_log.md",
    "publication": ROOT / "_logs/publication_log.md",
}


ACTION_LOG_TARGET = {
    "enter": "window",
    "collect": "window",
    "propose": "window",
    "write": "window",
    "approve": "window",
    "editorial_report": "editorial",
    "canon_change_request": "canon",
    "canonize": "canon",
    "asset_used": "asset",
    "freeze": "publication",
}


def ensure_window(window_id):
    registry = load_window_registry()
    window = find_window(registry, window_id)
    if not window:
        raise SystemExit(f"Unknown window_id: {window_id}")
    return window


def validate_action_allowed(window, action):
    if action in ["enter", "collect", "propose", "write", "approve"]:
        allowed_paths = window["effective_permissions"].get(action, [])
        if not allowed_paths:
            raise SystemExit(
                f"Action `{action}` is not allowed for window `{window['window_id']}`."
            )


def append_log(log_path, entry):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(f"# {log_path.stem.replace('_', ' ').title()}\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(
            "\n"
            f"[{entry['time']}] `{entry['window_id']}` "
            f"({entry['role']} in {entry['room']}) "
            f"{entry['action']} `{entry['target']}`.\n"
        )
        if entry["result"]:
            f.write(f"Result: {entry['result']}\n")
        if entry["reason"]:
            f.write(f"Reason: {entry['reason']}\n")


def record_action(args):
    window = ensure_window(args.window_id)
    validate_action_allowed(window, args.action)

    entry = {
        "time": now_iso(),
        "window_id": args.window_id,
        "room": window["room"],
        "role": window["role"],
        "action": args.action,
        "target": args.target,
        "result": args.result or "",
        "reason": args.reason or "",
    }

    log_key = args.log or ACTION_LOG_TARGET.get(args.action, "window")
    if log_key not in LOG_PATHS:
        known = ", ".join(sorted(LOG_PATHS))
        raise SystemExit(f"Unknown log: {log_key}\nKnown logs: {known}")
    append_log(LOG_PATHS[log_key], entry)
    return entry


def main():
    parser = argparse.ArgumentParser(description="Record an audited window action.")
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--result")
    parser.add_argument("--reason")
    parser.add_argument("--log", choices=sorted(LOG_PATHS))
    args = parser.parse_args()
    print(json.dumps(record_action(args), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

