"""run_shell tool implementation.

Accessible by integrator and tester roles only.
"""

from __future__ import annotations

import asyncio
from typing import Any


async def run_shell(params: dict[str, Any]) -> dict[str, Any]:
    """Execute a shell command.

    Args:
        params: Must contain 'command'.
                May contain 'timeout' (default: 60 seconds).
                May contain 'cwd' (working directory).

    Returns:
        Dict with 'success', 'stdout', 'stderr', 'exit_code'.
    """
    command = params.get("command", "")
    timeout = params.get("timeout", 60)
    cwd = params.get("cwd", None)

    if not command:
        return {
            "success": False,
            "error": "No command specified",
        }

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode,
        }

    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Command timed out after {timeout}s",
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to execute command: {exc}",
        }
