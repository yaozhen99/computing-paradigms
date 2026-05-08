#!/usr/bin/env python3
"""Pipe Guard: PreToolUse hook that enforces file read/write isolation per role.

Reads pipe_manifest_<role>.json to determine allowed inputs (read) and
outputs (write) for the currently active role. Denies tool calls that
access paths outside the declared boundaries.

Environment variable ACTIVE_ROLE identifies the current role.
If ACTIVE_ROLE is unset, all operations are allowed (global AI mode).
"""

from __future__ import annotations

import json
import os
import re
import sys

# Paths shared across all roles (read-only)
READONLY_SHARED = ["_system/", "_skills/"]

# Tool names that read files
READ_TOOLS = {"Read", "Glob", "Grep"}

# Tool names that write files
WRITE_TOOLS = {"Write", "Edit"}

# Tool name for shell commands
BASH_TOOL = "Bash"


def _normalize_path(path: str) -> str:
    """Normalize a path for prefix matching: strip leading ./ and use / separator."""
    path = path.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    return path


def _path_allowed(path: str, prefixes: list[str]) -> bool:
    """Check if path starts with any of the given prefixes."""
    norm_path = _normalize_path(path)
    for prefix in prefixes:
        norm_prefix = _normalize_path(prefix)
        if norm_path.startswith(norm_prefix):
            return True
    return False


def _deny(role: str, reason: str) -> None:
    """Output a deny decision and exit."""
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    sys.exit(0)


def _allow() -> None:
    """Exit with code 0 to allow the tool call."""
    sys.exit(0)


def _load_manifest(role: str) -> dict | None:
    """Load the pipe manifest for the given role."""
    manifest_path = f"_pipes/pipe_manifest_{role}.json"
    try:
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _check_bash_write_paths(command: str, output_prefixes: list[str]) -> str | None:
    """Heuristic check for file write redirections in Bash commands.

    Detects obvious > and >> redirections to paths outside outputs.
    Returns a reason string if denied, None if allowed.
    """
    # Match > or >> followed by a file path
    # Pattern: > path or >> path (with optional spaces)
    redirect_pattern = r">>\s*([^\s;&|)]+)|>\s*([^\s;&|)]+)"
    matches = re.findall(redirect_pattern, command)

    for match in matches:
        path = match[0] or match[1]
        if not _path_allowed(path, output_prefixes):
            return f"Bash command contains write redirection to {path}, which is outside allowed outputs"

    # Check for tee commands writing to non-output paths
    tee_pattern = r"tee\s+([^\s;&|)]+)"
    tee_matches = re.findall(tee_pattern, command)
    for path in tee_matches:
        if not _path_allowed(path, output_prefixes):
            return f"Bash command contains tee to {path}, which is outside allowed outputs"

    return None


def main() -> None:
    # Read hook input from stdin
    hook_input = json.load(sys.stdin)

    role = os.environ.get("ACTIVE_ROLE", "")
    if not role:
        # No active role = global AI mode, allow everything
        _allow()
        return

    manifest = _load_manifest(role)
    if manifest is None:
        # No manifest found = no pipe restriction active, allow
        _allow()
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    inputs = manifest.get("inputs", [])
    outputs = manifest.get("outputs", [])

    if tool_name in READ_TOOLS:
        # Read operations: check against inputs + shared readonly
        path = tool_input.get("file_path") or tool_input.get("path") or ""
        allowed_prefixes = inputs + READONLY_SHARED
        if not _path_allowed(path, allowed_prefixes):
            _deny(
                role,
                f"Role '{role}' cannot read '{path}'. Allowed inputs: {inputs}",
            )
        _allow()

    elif tool_name in WRITE_TOOLS:
        # Write operations: check against outputs only
        path = tool_input.get("file_path", "")
        if not _path_allowed(path, outputs):
            _deny(
                role,
                f"Role '{role}' cannot write '{path}'. Allowed outputs: {outputs}",
            )
        _allow()

    elif tool_name == BASH_TOOL:
        # Bash: heuristic check for write redirections
        command = tool_input.get("command", "")
        reason = _check_bash_write_paths(command, outputs)
        if reason:
            _deny(role, reason)
        _allow()

    else:
        # Unknown tool: allow (pipe guard only restricts file access tools)
        _allow()


if __name__ == "__main__":
    main()