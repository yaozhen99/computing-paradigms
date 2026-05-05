"""Claude CLI subprocess adapter.

Transitional adapter using `claude -p` subprocess.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from typing import Any

from statekanban.adapters.base import LLMAdapter
from statekanban.core.errors import LLMAuthError, LLMResponseParseError
from statekanban.core.kanban import LLMMessage, LLMResponse


class ClaudeCLIAdapter(LLMAdapter):
    """Transitional adapter using `claude -p` subprocess."""

    def __init__(self, cli_path: str = "claude") -> None:
        """
        Args:
            cli_path: Path to the claude CLI executable.
        """
        self._cli_path = cli_path

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send a completion request via the Claude CLI subprocess."""
        # Build the prompt from messages
        prompt_parts: list[str] = []
        for msg in messages:
            if msg.content:
                prompt_parts.append(f"[{msg.role}]: {msg.content}")
        prompt = "\n".join(prompt_parts)

        if not shutil.which(self._cli_path):
            raise LLMAuthError(
                f"Claude CLI not found at: {self._cli_path}"
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path,
                "-p",
                prompt,
                "--output-format",
                "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=120.0
            )

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                raise LLMResponseParseError(
                    f"Claude CLI failed (exit {proc.returncode}): {error_msg}"
                )

            raw_output = stdout.decode("utf-8", errors="replace")

            try:
                parsed = json.loads(raw_output)
                content = parsed.get("content", raw_output)
            except json.JSONDecodeError:
                content = raw_output

            return LLMResponse(
                content=content,
                finish_reason="end_turn",
                raw={"stdout": raw_output},
            )

        except asyncio.TimeoutError:
            raise LLMResponseParseError("Claude CLI subprocess timed out")
        except (LLMAuthError, LLMResponseParseError):
            raise
        except Exception as exc:
            raise LLMResponseParseError(f"Claude CLI error: {exc}") from exc
