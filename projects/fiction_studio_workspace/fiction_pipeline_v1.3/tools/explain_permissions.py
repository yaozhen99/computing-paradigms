import argparse
import json
from studio_core import load_policy_bundle, validate_member


def validate(name, value, known):
    validate_member(name, value, known)


def explain(room, role, parent_window_id=None):
    policy = load_policy_bundle()
    rooms = policy["rooms"]
    roles = policy["roles"]
    matrix = policy["matrix"]
    versions = policy["versions"]

    validate("room", room, rooms["rooms"])
    validate("role", role, roles["roles"])

    allowed = matrix["matrix"].get(role, {}).get(room, [])
    denied = [action for action in matrix["actions"] if action not in allowed]
    room_policy = rooms["rooms"][room]
    role_policy = roles["roles"][role]

    explanation = {
        "policy_version": versions["current"],
        "room": {
            "name": room,
            "purpose": room_policy["purpose"],
            "canon_safe": room_policy["canon_safe"],
            "allows_high_divergence": room_policy["allows_high_divergence"],
            "default_primary_role": room_policy["default_primary_role"],
        },
        "role": {
            "name": role,
            "purpose": role_policy["purpose"],
            "may_approve": role_policy["may_approve"],
            "default_rooms": role_policy["default_rooms"],
        },
        "parent_window_id": parent_window_id,
        "effective_permissions": {
            "allowed": allowed,
            "denied": denied,
        },
        "rules": {
            "deny_unknown": matrix["defaults"]["deny_unknown"],
            "deny_wins": matrix["defaults"]["deny_wins"],
            "manual_override_requires_audit": matrix["defaults"]["manual_override_requires_audit"],
        },
    }
    return explanation


def main():
    parser = argparse.ArgumentParser(description="Explain effective permissions for a room and role.")
    parser.add_argument("--room", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--parent-window-id")
    args = parser.parse_args()
    print(json.dumps(explain(args.room, args.role, args.parent_window_id), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
