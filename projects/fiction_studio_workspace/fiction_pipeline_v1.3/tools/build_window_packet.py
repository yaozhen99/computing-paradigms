import argparse
import json
from pathlib import Path

from studio_core import (
    PACKET_DIR,
    ROOT,
    find_window as find_window_in_registry,
    load_policy_bundle,
    load_window_registry,
    now_iso,
    resolve_project_path,
    write_json,
    write_text,
)


READS_BY_ROOM = {
    "author_room": [
        "README.md",
        "_policy/roles.md",
        "_policy/room_permissions.md",
        "author_room/ROOM_PROMPT.md",
        "author_room/author_premise.md",
        "author_room/author_outline.md",
    ],
    "notebook": [
        "README.md",
        "_policy/roles.md",
        "_policy/room_permissions.md",
        "notebook/ROOM_PROMPT.md",
        "author_room/author_premise.md",
        "author_room/author_outline.md",
        "notebook/raw_notes.md",
    ],
    "ammo_bank": [
        "README.md",
        "_policy/roles.md",
        "_policy/room_permissions.md",
        "ammo_bank/ROOM_PROMPT.md",
        "author_room/author_premise.md",
        "author_room/author_outline.md",
        "notebook/raw_notes.md",
        "ammo_bank/index.md",
        "ammo_bank/usage_ledger.md",
        "ammo_bank/MIGRATION_SPEC.md",
    ],
    "asset_room": [
        "README.md",
        "_policy/roles.md",
        "_policy/room_permissions.md",
        "asset_room/ROOM_PROMPT.md",
        "author_room/author_premise.md",
        "author_room/author_outline.md",
        "ammo_bank/index.md",
        "asset_room/asset_index.md",
    ],
    "canon_room": [
        "README.md",
        "_policy/roles.md",
        "_policy/room_permissions.md",
        "canon_room/ROOM_PROMPT.md",
        "author_room/author_premise.md",
        "author_room/author_outline.md",
        "canon_room/project_canon.md",
        "canon_room/continuity_ledger.md",
    ],
    "editorial_room": [
        "README.md",
        "_policy/roles.md",
        "_policy/room_permissions.md",
        "editorial_room/ROOM_PROMPT.md",
        "author_room/author_premise.md",
        "author_room/author_outline.md",
        "canon_room/project_canon.md",
        "canon_room/continuity_ledger.md",
        "editorial_room/README.md",
    ],
    "revision_room": [
        "README.md",
        "_policy/roles.md",
        "_policy/room_permissions.md",
        "revision_room/ROOM_PROMPT.md",
        "author_room/author_premise.md",
        "author_room/author_outline.md",
        "canon_room/project_canon.md",
        "canon_room/continuity_ledger.md",
        "editorial_room/README.md",
        "revision_room/README.md",
    ],
    "publication_room": [
        "README.md",
        "_policy/roles.md",
        "_policy/room_permissions.md",
        "publication_room/ROOM_PROMPT.md",
        "author_room/author_premise.md",
        "author_room/author_outline.md",
        "canon_room/project_canon.md",
        "canon_room/continuity_ledger.md",
        "publication_room/README.md",
        "publication_room/release_log.md",
    ],
}


AGENT_RULES_BY_ROLE = {
    "Chief Author": "_policy/agent_rules/chief_author.md",
    "Idea Assistant": "_policy/agent_rules/idea_assistant.md",
    "Research Assistant": "_policy/agent_rules/research_assistant.md",
    "Ammo Librarian": "_policy/agent_rules/ammo_librarian.md",
    "Canon Keeper": "_policy/agent_rules/canon_keeper.md",
    "Development Editor": "_policy/agent_rules/development_editor.md",
    "Continuity Editor": "_policy/agent_rules/continuity_editor.md",
    "Line Editor": "_policy/agent_rules/line_editor.md",
    "Copy Editor": "_policy/agent_rules/copy_editor.md",
    "Proofreader": "_policy/agent_rules/proofreader.md",
    "Publisher": "_policy/agent_rules/publisher.md",
}


def find_window(window_id):
    registry = load_window_registry()
    window = find_window_in_registry(registry, window_id)
    if window:
        return window
    raise SystemExit(f"Unknown window_id: {window_id}")

def build_packet(window):
    room = window["room"]
    role = window["role"]
    policy = load_policy_bundle()
    rooms = policy["rooms"]
    roles = policy["roles"]

    room_policy = rooms["rooms"][room]
    role_policy = roles["roles"][role]

    must_read = list(READS_BY_ROOM.get(room, ["README.md", "_policy/roles.md", "_policy/room_permissions.md"]))
    agent_rule = AGENT_RULES_BY_ROLE.get(role)
    if agent_rule and agent_rule not in must_read:
        must_read.insert(3, agent_rule)

    packet = {
        "packet_version": "0.1.0",
        "created_at": now_iso(),
        "window_id": window["window_id"],
        "room": room,
        "role": role,
        "parent_window_id": window["parent_window_id"],
        "task": window.get("task"),
        "task_file": window.get("task_file"),
        "room_purpose": room_policy["purpose"],
        "role_purpose": role_policy["purpose"],
        "must_read": must_read,
        "effective_permissions": window["effective_permissions"],
        "denied_permissions": window["denied_permissions"],
        "operating_rules": [
            "Stay inside the owning room unless permissions explicitly allow otherwise.",
            "Do not write to denied rooms.",
            "Do not canonize raw material without approval.",
            "Log write, approve, and freeze actions.",
            "Stop after completing this room-scoped task.",
        ],
        "default_output_room": room,
        "policy_versions": window["inherited_policy_versions"],
    }
    return packet


def render_markdown(packet):
    def bullet(items):
        if not items:
            return "- none"
        return "\n".join(f"- `{item}`" for item in items)

    perms = packet["effective_permissions"]
    return f"""# AI Window Startup Packet

Window: `{packet["window_id"]}`

Room: `{packet["room"]}`

Role: `{packet["role"]}`

Parent window: `{packet["parent_window_id"] or "none"}`

Policy versions: {", ".join(packet["policy_versions"])}

## Room Purpose

{packet["room_purpose"]}

## Role Purpose

{packet["role_purpose"]}

## Task

{packet["task"] or "No inline task was provided."}

Task file: `{packet["task_file"] or "none"}`

## Must Read

{bullet(packet["must_read"])}

## Effective Permissions

enter:
{bullet(perms["enter"])}

collect:
{bullet(perms["collect"])}

propose:
{bullet(perms["propose"])}

write:
{bullet(perms["write"])}

approve:
{bullet(perms["approve"])}

Denied actions:
{bullet(packet["denied_permissions"])}

## Operating Rules

{bullet(packet["operating_rules"])}

## Output Rule

Default output room: `{packet["default_output_room"]}`

Stop after completing this room-scoped task.
"""


def main():
    parser = argparse.ArgumentParser(description="Build an AI window startup packet.")
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--output")
    parser.add_argument("--markdown-output")
    args = parser.parse_args()

    window = find_window(args.window_id)
    packet = build_packet(window)
    output = Path(args.output) if args.output else PACKET_DIR / f"{args.window_id}.json"
    if not output.is_absolute():
        output = resolve_project_path(output)
    write_json(output, packet)
    if args.markdown_output:
        markdown_output = Path(args.markdown_output)
        if not markdown_output.is_absolute():
            markdown_output = resolve_project_path(markdown_output)
        write_text(markdown_output, render_markdown(packet))
    print(json.dumps(packet, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
