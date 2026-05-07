"""call_codex tool implementation.

Accessible by coder and integrator roles only.
Generates code via the OpenAI Codex CLI subprocess.

REQ-008: Null bytes validation per reviewer rules RR-004.
         Returns error dict with error_code=SK_TR_004 if prompt
         contains null bytes.
REQ-006: Uses CodexTimeoutError(SK_CX_003) for timeout classification.
"""

from __future__ import annotations

from typing import Any

from statekanban.adapters.codex_adapter import CodexAdapter
from statekanban.core.kanban import LLMMessage


def create_call_codex_tool(codex_adapter: CodexAdapter) -> Any:
    """Create the call_codex tool bound to a CodexAdapter.

    Returns:
        Async callable that accepts params dict and returns result dict.

    Tool parameters:
        prompt: str (required) -- Code generation prompt
        context_files: list[str] (optional) -- File paths for Codex context
        output_path: str (optional) -- Target file path for generated code
        max_tokens: int (optional, default=4096) -- Max output tokens

    Returns:
        {
            "success": bool,
            "content": str | None,       # Generated code snippet
            "output_path": str | None,   # Same as input output_path
            "finish_reason": str,
        }
    """

    async def call_codex(params: dict[str, Any]) -> dict[str, Any]:
        """Generate code via Codex CLI.

        Args:
            params: Must contain 'prompt'.
                    May contain 'context_files', 'output_path', 'max_tokens'.

        Returns:
            Dict with success, content, output_path, and finish_reason.
        """
        prompt = params.get("prompt", "")
        context_files = params.get("context_files", [])
        output_path = params.get("output_path", "")
        max_tokens = params.get("max_tokens", 4096)

        # REQ-008: Null bytes validation
        if "\x00" in prompt:
            return {
                "success": False,
                "content": None,
                "output_path": output_path,
                "finish_reason": "error",
                "error": "Null byte detected in prompt",
                "error_code": "SK_TR_004",
            }

        # Also check context_files paths for null bytes
        for cf in context_files:
            if isinstance(cf, str) and "\x00" in cf:
                return {
                    "success": False,
                    "content": None,
                    "output_path": output_path,
                    "finish_reason": "error",
                    "error": "Null byte detected in context file path",
                    "error_code": "SK_TR_004",
                }

        if not prompt:
            return {
                "success": False,
                "content": None,
                "output_path": output_path,
                "finish_reason": "error",
                "error": "No prompt specified",
            }

        # Build a single-turn message for Codex
        content = prompt
        if context_files:
            content += "\n\nContext files: " + ", ".join(context_files)

        messages = [LLMMessage(role="user", content=content)]

        try:
            response = await codex_adapter.complete(
                messages=messages,
                max_tokens=max_tokens,
            )

            # Codex output is code -- wrap as artifact candidate
            return {
                "success": True,
                "content": response.content,
                "output_path": output_path,
                "finish_reason": response.finish_reason,
            }

        except Exception as exc:
            from statekanban.core.errors import (
                CodexNotAvailableError,
                CodexExecutionError,
                CodexTimeoutError,
                ToolRegistryError,
            )

            # REQ-008: Propagate null bytes errors as-is
            if isinstance(exc, ToolRegistryError) and exc.error_code == "SK_TR_004":
                return {
                    "success": False,
                    "content": None,
                    "output_path": output_path,
                    "finish_reason": "error",
                    "error": str(exc),
                    "error_code": "SK_TR_004",
                }

            # REQ-006: Classify timeout vs other errors
            if isinstance(exc, CodexTimeoutError):
                return {
                    "success": False,
                    "content": None,
                    "output_path": output_path,
                    "finish_reason": "error",
                    "error": str(exc),
                    "error_code": "SK_CX_003",
                }

            if isinstance(exc, (CodexNotAvailableError, CodexExecutionError)):
                raise  # Propagate to ToolRegistry for proper error handling

            return {
                "success": False,
                "content": None,
                "output_path": output_path,
                "finish_reason": "error",
                "error": str(exc),
                "error_code": "SK_CX_002",
            }

    return call_codex