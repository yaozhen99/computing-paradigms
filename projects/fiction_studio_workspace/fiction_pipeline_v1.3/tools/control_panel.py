import argparse
import json

from studio_core import find_window, load_policy_bundle, load_window_registry


def build_window_chain(registry, window):
    chain = []
    current = window
    seen = set()
    while current and current["window_id"] not in seen:
        chain.append(current)
        seen.add(current["window_id"])
        parent_id = current.get("parent_window_id")
        current = find_window(registry, parent_id) if parent_id else None
    return chain


def select_windows(registry, room=None):
    windows = list(registry.get("windows", []))
    if room:
        windows = [window for window in windows if window["room"] == room]
    return sorted(windows, key=lambda window: (window.get("created_at", ""), window["window_id"]))


def build_panel(room=None, window_id=None):
    policy = load_policy_bundle()
    registry = load_window_registry()
    rooms = policy["rooms"]["rooms"]
    roles = policy["roles"]["roles"]
    selected_room = rooms.get(room) if room else None

    if room and not selected_room:
        known = ", ".join(sorted(rooms))
        raise SystemExit(f"Unknown room: {room}\nKnown rooms: {known}")

    selected_window = None
    if window_id:
        selected_window = find_window(registry, window_id)
        if not selected_window:
            raise SystemExit(f"Unknown window_id: {window_id}")
        if room and selected_window["room"] != room:
            raise SystemExit(f"Window {window_id} does not belong to room {room}")

    windows = select_windows(registry, room)
    if selected_window and selected_window not in windows:
        windows = windows + [selected_window]
        windows = sorted(windows, key=lambda window: (window.get("created_at", ""), window["window_id"]))

    panel = {
        "policy_version": policy["versions"]["current"],
        "policy_counts": {
            "rooms": len(rooms),
            "roles": len(roles),
            "actions": len(policy["matrix"]["actions"]),
        },
        "room_filter": room,
        "selected_room": room,
        "selected_room_policy": {
            "name": room,
            **selected_room,
        } if selected_room else None,
        "selected_window_id": window_id,
        "selected_window": selected_window,
        "selected_window_chain": build_window_chain(registry, selected_window) if selected_window else [],
        "windows": windows,
    }
    return panel


def render_window(window):
    parent_id = window.get("parent_window_id") or "none"
    allowed = window.get("effective_permissions", {})
    return [
        f"- {window['window_id']} | room={window['room']} | role={window['role']} | parent={parent_id} | status={window.get('status', 'unknown')}",
        f"  allowed enter={allowed.get('enter', [])} collect={allowed.get('collect', [])} propose={allowed.get('propose', [])} write={allowed.get('write', [])} approve={allowed.get('approve', [])}",
    ]


def render_panel(panel):
    lines = []
    lines.append("Control Panel")
    lines.append(f"Policy version: {panel['policy_version']}")
    counts = panel["policy_counts"]
    lines.append(f"Rooms: {counts['rooms']} | Roles: {counts['roles']} | Actions: {counts['actions']}")
    lines.append("")

    lines.append("Rooms")
    if panel["selected_room_policy"]:
        room = panel["selected_room_policy"]
        outputs = ", ".join(room.get("default_outputs", []))
        lines.append(
            f"- {room['name']} | primary={room['default_primary_role']} | canon_safe={room['canon_safe']} | divergence={room['allows_high_divergence']} | outputs={outputs}"
        )
        lines.append(f"  purpose: {room['purpose']}")
    else:
        lines.append("- no room selected")
    lines.append("")

    lines.append(f"Windows ({len(panel['windows'])})")
    if panel["windows"]:
        for window in panel["windows"]:
            lines.extend(render_window(window))
    else:
        lines.append("- none")
    lines.append("")

    if panel["selected_window"]:
        lines.append(f"Selected window: {panel['selected_window']['window_id']}")
        for window in panel["selected_window_chain"]:
            lines.append(
                f"- {window['window_id']} | room={window['room']} | role={window['role']} | parent={window.get('parent_window_id') or 'none'}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Render a read-only control panel for rooms and windows.")
    parser.add_argument("--room")
    parser.add_argument("--window-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    panel = build_panel(room=args.room, window_id=args.window_id)
    if args.json:
        print(json.dumps(panel, indent=2, ensure_ascii=False))
    else:
        print(render_panel(panel), end="")


if __name__ == "__main__":
    main()
