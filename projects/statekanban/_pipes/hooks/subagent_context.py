#!/usr/bin/env python3
"""SubagentStart hook: injects pipe isolation context into subagents.

Reads the pipe manifest for the currently active role and injects
a context reminder about allowed read/write paths into the subagent's
conversation before its first prompt.
"""

from __future__ import annotations

import json
import os
import sys


def _load_manifest(role: str) -> dict | None:
    """Load the pipe manifest for the given role."""
    manifest_path = f"_pipes/pipe_manifest_{role}.json"
    try:
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main() -> None:
    hook_input = json.load(sys.stdin)

    role = os.environ.get("ACTIVE_ROLE", "")
    if not role:
        # No active role: no context to inject
        sys.exit(0)

    manifest = _load_manifest(role)
    if manifest is None:
        sys.exit(0)

    inputs = manifest.get("inputs", [])
    outputs = manifest.get("outputs", [])

    additional_context = (
        f"## Physical Isolation Notice\n"
        f"You are the '{role}' role. File read/write pipes are ACTIVE:\n"
        f"- Readable: {inputs} + _system/ + _skills/ (read-only)\n"
        f"- Writable: {outputs}\n"
        f"Unauthorized access will be automatically DENIED by the pipe guard.\n"
        f"Strictly comply with these boundaries."
    )

    result = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": additional_context,
        }
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    sys.exit(0)


if __name__ == "__main__":
    main()