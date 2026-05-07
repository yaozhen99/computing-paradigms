"""CodexAdapter: LLM adapter that executes via the OpenAI Codex CLI subprocess.

Unlike other adapters, Codex is specialized for code generation:
- Input: prompt + context_files
- Output: code snippet (not structured JSON)
- No tool_use support
- No streaming

REQ-006: Uses CodexTimeoutError(SK_CX_003) for timeout instead of
         generic CodexExecutionError(SK_CX_002).
REQ-008: Null bytes validation per reviewer rules RR-004.
"""

from __future__ import annotations

import asyncio
import shutil
from typing import Any

from statekanban.adapters.base import LLMAdapter
from statekanban.core.errors import (
    CodexNotAvailableError,
    CodexExecutionError,
    CodexTimeoutError,
    ToolRegistryError,
)
from statekanban.core.kanban import LLMMessage, LLMResponse


class CodexAdapter(LLMAdapter):
    """LLM adapter that executes via the OpenAI Codex CLI subprocess.

    Codex is specialized for code generation. It does not support
    tool_use blocks or streaming. The output is raw code text.

    REQ-008: Null bytes validation on message content.
    REQ-006: CodexTimeoutError for timeout failures.
    """

    def __init__(self, cli_path: str = "codex", timeout: float = 300.0) -> None:
        """
        Args:
            cli_path: Path to the codex CLI executable.
            timeout: Maximum seconds to wait for Codex response.
        """
        self._cli_path = cli_path
        self._timeout = timeout
        self._available: bool | None = None  # lazy availability check

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Execute via Codex CLI subprocess.

        Extracts prompt from the last user message. Ignores tools parameter
        (Codex does not support tool_use). Returns raw code snippet as content.

        REQ-008: Raises ToolRegistryError(SK_TR_004) if any message
                 content contains null bytes.

        REQ-006: Raises CodexTimeoutError(SK_CX_003) on timeout,
                 instead of generic CodexExecutionError(SK_CX_002).

        Returns:
            LLMResponse with content=code_snippet, finish_reason="end_turn"

        Raises:
            CodexNotAvailableError: Codex CLI not found on PATH
            CodexTimeoutError: Codex timed out (SK_CX_003)
            CodexExecutionError: Codex returned non-zero exit (SK_CX_002)
            ToolRegistryError: Null bytes in message content (SK_TR_004)
        """
        # REQ-008: Null bytes validation
        for msg in messages:
            if msg.content and "\x00" in msg.content:
                raise ToolRegistryError(
                    "Null byte detected in prompt content",
                    error_code="SK_TR_004",
                )

        # Availability check (lazy, cached)
        if not self.check_available():
            raise CodexNotAvailableError(f"Codex CLI not found at '{self._cli_path}'")

        # Extract prompt from last user message
        prompt = ""
        for msg in reversed(messages):
            if msg.role == "user" and msg.content:
                prompt = msg.content
                break

        if not prompt:
            return LLMResponse(
                content="",
                finish_reason="end_turn",
            )

        # Execute Codex CLI subprocess
        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path,
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._timeout,
            )

            if proc.returncode != 0:
                error_detail = stderr.decode("utf-8", errors="replace")[:500]
                raise CodexExecutionError(
                    f"Codex CLI exited with code {proc.returncode}: {error_detail}"
                )

            content = stdout.decode("utf-8", errors="replace")

            return LLMResponse(
                content=content,
                finish_reason="end_turn",
            )

        except CodexNotAvailableError:
            raise
        except CodexExecutionError:
            raise
        except CodexTimeoutError:
            raise
        except ToolRegistryError:
            raise
        except asyncio.TimeoutError:
            # REQ-006: Use CodexTimeoutError instead of CodexExecutionError
            raise CodexTimeoutError(f"Codex CLI timed out after {self._timeout}s")
        except FileNotFoundError:
            raise CodexNotAvailableError(f"Codex CLI not found at '{self._cli_path}'")
        except Exception as exc:
            raise CodexExecutionError(f"Codex execution error: {exc}") from exc

    def check_available(self) -> bool:
        """Check whether the Codex CLI is available on PATH.

        Result is cached after first check.
        """
        if self._available is None:
            self._available = shutil.which(self._cli_path) is not None
        return self._available
