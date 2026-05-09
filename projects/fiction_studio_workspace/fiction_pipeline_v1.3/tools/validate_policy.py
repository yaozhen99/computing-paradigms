import argparse
import json

from build_window_packet import AGENT_RULES_BY_ROLE
from studio_core import POLICY_DIR, ROOT, load_policy_bundle


ROOM_PROMPT_BY_ROOM = {
    "author_room": "author_room/ROOM_PROMPT.md",
    "notebook": "notebook/ROOM_PROMPT.md",
    "ammo_bank": "ammo_bank/ROOM_PROMPT.md",
    "asset_room": "asset_room/ROOM_PROMPT.md",
    "canon_room": "canon_room/ROOM_PROMPT.md",
    "editorial_room": "editorial_room/ROOM_PROMPT.md",
    "revision_room": "revision_room/ROOM_PROMPT.md",
    "publication_room": "publication_room/ROOM_PROMPT.md",
}


def validate_policy():
    policy = load_policy_bundle()
    rooms = policy["rooms"]["rooms"]
    roles = policy["roles"]["roles"]
    matrix = policy["matrix"]

    errors = []

    for room in rooms:
        prompt = ROOM_PROMPT_BY_ROOM.get(room)
        if not prompt:
            errors.append(f"Missing ROOM_PROMPT mapping for room: {room}")
        elif not (ROOT / prompt).exists():
            errors.append(f"Missing room prompt file: {prompt}")

    for role in roles:
        rule = AGENT_RULES_BY_ROLE.get(role)
        if not rule:
            errors.append(f"Missing agent rule mapping for role: {role}")
        elif not (ROOT / rule).exists():
            errors.append(f"Missing agent rule file: {rule}")

    for role, room_permissions in matrix["matrix"].items():
        if role not in roles:
            errors.append(f"Permission matrix has unknown role: {role}")
        for room, actions in room_permissions.items():
            if room not in rooms:
                errors.append(f"Permission matrix role {role} has unknown room: {room}")
            for action in actions:
                if action not in matrix["actions"]:
                    errors.append(f"Permission matrix role {role} room {room} has unknown action: {action}")

    for role in roles:
        if role not in matrix["matrix"]:
            errors.append(f"Permission matrix missing role: {role}")

    result = {
        "ok": not errors,
        "errors": errors,
        "counts": {
            "rooms": len(rooms),
            "roles": len(roles),
            "actions": len(matrix["actions"]),
        },
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Validate studio policy consistency.")
    parser.parse_args()
    result = validate_policy()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

