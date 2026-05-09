import argparse
import json
from uuid import uuid4

from studio_core import (
    WINDOW_DIR,
    find_window,
    load_policy_bundle,
    load_window_registry,
    now_iso,
    validate_member,
    write_window_registry,
)


def validate_room(room, rooms):
    validate_member("room", room, rooms["rooms"])


def validate_role(role, roles):
    validate_member("role", role, roles["roles"])


def get_permissions(role, room, matrix):
    return matrix["matrix"].get(role, {}).get(room, [])


def build_effective_permissions(role, room, matrix):
    allowed = set(get_permissions(role, room, matrix))
    actions = matrix["actions"]
    return {
        "enter": [room] if "enter" in allowed else [],
        "collect": [room] if "collect" in allowed else [],
        "propose": [room] if "propose" in allowed else [],
        "write": [room] if "write" in allowed else [],
        "approve": [room] if "approve" in allowed else [],
        "denied": [action for action in actions if action not in allowed],
    }


def apply_parent_constraints(effective, parent_window):
    if not parent_window:
        return effective

    constrained = {}
    parent_permissions = parent_window["effective_permissions"]
    for action in ["enter", "collect", "propose", "write", "approve"]:
        requested = set(effective[action])
        parent_allowed = set(parent_permissions.get(action, []))
        constrained[action] = sorted(requested & parent_allowed)

    denied = set(effective["denied"])
    for action in ["enter", "collect", "propose", "write", "approve"]:
        if effective[action] and not constrained[action]:
            denied.add(action)
    constrained["denied"] = [action for action in ["enter", "collect", "propose", "write", "approve"] if action in denied]
    return constrained


def create_window(args, persist=True):
    policy = load_policy_bundle()
    rooms = policy["rooms"]
    roles = policy["roles"]
    matrix = policy["matrix"]
    policy_versions = policy["versions"]
    registry = load_window_registry()

    validate_room(args.room, rooms)
    validate_role(args.role, roles)
    parent_window = None
    if args.parent_window_id:
        parent_window = find_window(registry, args.parent_window_id)
        if not parent_window:
            raise SystemExit(f"Unknown parent_window_id: {args.parent_window_id}")

    timestamp = now_iso()
    window_id = args.window_id or f"win_{timestamp.replace(':', '').replace('-', '')}_{uuid4().hex[:8]}"
    effective = build_effective_permissions(args.role, args.room, matrix)
    effective = apply_parent_constraints(effective, parent_window)

    record = {
        "window_id": window_id,
        "room": args.room,
        "role": args.role,
        "parent_window_id": args.parent_window_id,
        "created_at": timestamp,
        "source_command": args.source_command or "",
        "task": getattr(args, "task", None),
        "task_file": getattr(args, "task_file", None),
        "inherited_policy_versions": [policy_versions["current"]],
        "inheritance": {
            "parent_constraints_applied": bool(parent_window),
            "parent_room": parent_window["room"] if parent_window else None,
            "parent_role": parent_window["role"] if parent_window else None,
        },
        "effective_permissions": {
            "enter": effective["enter"],
            "collect": effective["collect"],
            "propose": effective["propose"],
            "write": effective["write"],
            "approve": effective["approve"],
        },
        "denied_permissions": effective["denied"],
        "status": "created",
    }

    if persist:
        registry.setdefault("windows", []).append(record)
        write_window_registry(registry)

        log_path = WINDOW_DIR / "window_log.md"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(
                f"\n[{timestamp}] created `{window_id}` in `{args.room}` as `{args.role}`"
            )
            if args.parent_window_id:
                f.write(f", parent `{args.parent_window_id}`")
            f.write(".\n")

    return record


def main():
    parser = argparse.ArgumentParser(description="Create a room-owned AI window record.")
    parser.add_argument("--room", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--parent-window-id")
    parser.add_argument("--source-command")
    parser.add_argument("--window-id")
    parser.add_argument("--task")
    parser.add_argument("--task-file")
    args = parser.parse_args()
    record = create_window(args)
    print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
