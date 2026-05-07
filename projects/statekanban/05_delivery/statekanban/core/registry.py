"""ToolRegistry: permission-gated tool dispatch with audit.

Every tool call passes through dispatch() which checks the caller's
permit set before execution. All invocations are logged to AuditZone.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from statekanban.core.errors import (
    PermissionDeniedError,
    ToolNotFoundError,
    ToolTimeoutError,
)
from statekanban.core.kanban import (
    ErrorSignal,
    StateKanban,
    ToolDef,
    make_signal_id,
    now_utc,
)

# Type alias for tool implementations
ToolImplementation = Callable[..., Awaitable[Any]]


@dataclass
class ToolResult:
    """Result of a tool dispatch call."""

    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class ToolRegistry:
    """Permission-gated tool dispatch with audit."""

    def __init__(self, kanban: StateKanban) -> None:
        """
        Args:
            kanban: StateKanban instance for audit logging.
        """
        self._kanban = kanban
        self._tools: dict[str, tuple[ToolDef, ToolImplementation]] = {}

    def register(
        self,
        tool_def: ToolDef,
        implementation: ToolImplementation,
    ) -> None:
        """Register a tool.

        Args:
            tool_def: Tool specification.
            implementation: Async callable that implements the tool.

        Raises:
            ToolNotFoundError: Tool name already registered (duplicate).
        """
        if tool_def.name in self._tools:
            raise ToolNotFoundError(f"Tool already registered: {tool_def.name}")
        self._tools[tool_def.name] = (tool_def, implementation)

        self._kanban.audit.log(
            event_type="tool_registered",
            actor="ToolRegistry",
            action="register",
            details={"tool_name": tool_def.name},
        )

    async def dispatch(
        self,
        tool_name: str,
        caller_role: str,
        params: dict[str, Any],
    ) -> ToolResult:
        """Dispatch a tool call after permission check.

        Args:
            tool_name: Name of the tool to call.
            caller_role: Role of the calling process.
            params: Tool parameters.

        Returns:
            ToolResult with output or error.

        Raises:
            PermissionDeniedError: Caller lacks permission for this tool.
            ToolNotFoundError: Tool name not registered.
            ToolTimeoutError: Tool execution exceeded timeout.
        """
        # Check tool exists
        entry = self._tools.get(tool_name)
        if entry is None:
            raise ToolNotFoundError(f"Tool not found: {tool_name}")

        tool_def, implementation = entry

        # Permission check
        if (
            caller_role not in tool_def.required_permissions
            and "all_roles" not in tool_def.required_permissions
        ):
            self._kanban.audit.log(
                event_type="permission_denied",
                actor="ToolRegistry",
                action="dispatch",
                details={
                    "tool_name": tool_name,
                    "caller_role": caller_role,
                },
            )
            raise PermissionDeniedError(
                f"Role '{caller_role}' lacks permission for tool '{tool_name}'"
            )

        # Hash params for audit (content hashing for sensitive ops)
        params_hash = self._hash_params(params)

        # Execute with timeout
        start_time = time.monotonic()
        try:
            result = await asyncio.wait_for(
                implementation(params),
                timeout=tool_def.timeout_seconds,
            )
            duration_ms = (time.monotonic() - start_time) * 1000

            self._kanban.audit.log(
                event_type="tool_call",
                actor=caller_role,
                action=f"dispatch:{tool_name}",
                details={
                    "tool_name": tool_name,
                    "params_hash": params_hash,
                    "result_status": "success",
                    "duration_ms": duration_ms,
                },
            )

            return ToolResult(
                success=True,
                output=result,
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            duration_ms = (time.monotonic() - start_time) * 1000

            self._kanban.audit.log(
                event_type="tool_timeout",
                actor=caller_role,
                action=f"dispatch:{tool_name}",
                details={
                    "tool_name": tool_name,
                    "params_hash": params_hash,
                    "timeout_seconds": tool_def.timeout_seconds,
                    "duration_ms": duration_ms,
                },
            )

            # Inject timeout error signal into FluidZone
            self._inject_timeout_signal(tool_name, caller_role, params)

            raise ToolTimeoutError(
                f"Tool '{tool_name}' timed out after {tool_def.timeout_seconds}s"
            )

        except (PermissionDeniedError, ToolNotFoundError):
            raise

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000

            self._kanban.audit.log(
                event_type="tool_error",
                actor=caller_role,
                action=f"dispatch:{tool_name}",
                details={
                    "tool_name": tool_name,
                    "params_hash": params_hash,
                    "result_status": "error",
                    "error": str(exc),
                    "duration_ms": duration_ms,
                },
            )

            return ToolResult(
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )

    def get_tool_def(self, tool_name: str) -> ToolDef | None:
        """Get the tool definition for a registered tool."""
        entry = self._tools.get(tool_name)
        return entry[0] if entry else None

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _hash_params(params: dict[str, Any]) -> str:
        """Hash parameters for audit (content hashing for sensitive ops)."""
        params_str = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(params_str.encode("utf-8")).hexdigest()[:16]

    def _inject_timeout_signal(
        self,
        tool_name: str,
        caller_role: str,
        params: dict[str, Any],
    ) -> None:
        """Inject a timeout error signal into FluidZone."""
        error_signal = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="ToolRegistry",
            target_id=tool_name,
            payload={"caller_role": caller_role, "tool_name": tool_name},
            timestamp=now_utc(),
            round_number=0,
            error_code="SK_TR_003",
            error_detail=f"Tool '{tool_name}' execution timed out",
        )
        try:
            self._kanban.fluid.write_signal(error_signal)
        except Exception:
            # Never crash the kernel -- swallow error signal injection failures
            pass
