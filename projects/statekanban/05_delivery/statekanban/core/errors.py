"""Error hierarchy for StateKanban.

Matches the architecture specification section 4.1 and
API contracts section 3 (error codes).
"""

from __future__ import annotations


class StateKanbanError(Exception):
    """Base error for all StateKanban errors."""

    error_code: str = "SK_ERR_000"
    http_analogy: int = 500

    def __init__(self, message: str = "", *, error_code: str | None = None) -> None:
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


# ---------------------------------------------------------------------------
# FluidZone errors
# ---------------------------------------------------------------------------


class FluidZoneError(StateKanbanError):
    """Base error for FluidZone operations."""


class InvalidSignalError(FluidZoneError):
    """Signal fails schema validation."""

    error_code = "SK_FZ_001"
    http_analogy = 400


class SignalCollisionError(FluidZoneError):
    """Signal collision detected."""

    error_code = "SK_FZ_002"
    http_analogy = 409


class ConvergenceTimeoutError(FluidZoneError):
    """Convergence exceeded maximum rounds (>10)."""

    error_code = "SK_FZ_003"
    http_analogy = 408


# ---------------------------------------------------------------------------
# CrystalZone errors
# ---------------------------------------------------------------------------


class CrystalZoneError(StateKanbanError):
    """Base error for CrystalZone operations."""


class ArtifactConflictError(CrystalZoneError):
    """Duplicate sequence number."""

    error_code = "SK_CZ_001"
    http_analogy = 409


class AppendOnlyViolationError(CrystalZoneError):
    """Attempted modify or delete on append-only zone."""

    error_code = "SK_CZ_002"
    http_analogy = 405


# ---------------------------------------------------------------------------
# AuditZone errors
# ---------------------------------------------------------------------------


class AuditZoneError(StateKanbanError):
    """Base error for AuditZone operations."""


class AuditWriteError(AuditZoneError):
    """Audit write failure."""

    error_code = "SK_AZ_001"
    http_analogy = 500


# ---------------------------------------------------------------------------
# Viewport errors
# ---------------------------------------------------------------------------


class ViewportError(StateKanbanError):
    """Base error for ViewportSlicer operations."""


class InvalidViewportSpecError(ViewportError):
    """Invalid viewport specification."""

    error_code = "SK_VS_001"
    http_analogy = 400


class SliceOverflowError(ViewportError):
    """Slice exceeds token budget even after truncation."""

    error_code = "SK_VS_002"
    http_analogy = 413


# ---------------------------------------------------------------------------
# OutputValve errors
# ---------------------------------------------------------------------------


class OutputValveError(StateKanbanError):
    """Base error for OutputValve operations."""


class ValidationFailedError(OutputValveError):
    """Validation chain failed."""


class SyntaxCheckError(ValidationFailedError):
    """Syntax check failed."""

    error_code = "SK_OV_001"
    http_analogy = 422


class TypeCheckError(ValidationFailedError):
    """Type check failed."""

    error_code = "SK_OV_002"
    http_analogy = 422


class TestExecutionError(ValidationFailedError):
    """Test execution failed."""

    error_code = "SK_OV_003"
    http_analogy = 422


class AtomicWriteError(OutputValveError):
    """Atomic write failed (disk/permission)."""

    error_code = "SK_OV_004"
    http_analogy = 500


class ValvePathViolationError(OutputValveError):
    """OutputValve write path escapes the output directory sandbox.

    Error code: SK_VS_005
    REQ-601: Triggered by OutputValve._validate_path() when a path
    traversal or out-of-bounds write is detected.
    """

    error_code = "SK_VS_005"
    http_analogy = 403

    def __init__(
        self,
        message: str = "",
        *,
        attempted_path: str = "",
        output_dir: str = "",
        error_code: str | None = None,
    ) -> None:
        if not message:
            message = (
                f"Path violation: '{attempted_path}' "
                f"resolves outside output directory '{output_dir}'"
            )
        super().__init__(message, error_code=error_code)
        self.attempted_path = attempted_path
        self.output_dir = output_dir


class HumanGateRejectedError(OutputValveError):
    """Human gate rejected the write."""

    error_code = "SK_OV_005"
    http_analogy = 403


# ---------------------------------------------------------------------------
# ToolRegistry errors
# ---------------------------------------------------------------------------


class ToolRegistryError(StateKanbanError):
    """Base error for ToolRegistry operations."""


class PermissionDeniedError(ToolRegistryError):
    """Caller lacks permission for this tool."""

    error_code = "SK_TR_001"
    http_analogy = 403


class ToolNotFoundError(ToolRegistryError):
    """Tool name not registered."""

    error_code = "SK_TR_002"
    http_analogy = 404


class ToolTimeoutError(ToolRegistryError):
    """Tool execution exceeded timeout."""

    error_code = "SK_TR_003"
    http_analogy = 408


class ToolPathViolationError(ToolRegistryError):
    """Tool path escapes the project root sandbox.

    Error code: SK_TR_005
    REQ-602: Triggered by read_file._validate_path() when a path
    traversal or out-of-bounds read is detected.
    """

    error_code = "SK_TR_005"
    http_analogy = 403

    def __init__(
        self,
        message: str = "",
        *,
        attempted_path: str = "",
        project_root: str = "",
        error_code: str | None = None,
    ) -> None:
        if not message:
            message = (
                f"Path violation: '{attempted_path}' "
                f"resolves outside project root '{project_root}'"
            )
        super().__init__(message, error_code=error_code)
        self.attempted_path = attempted_path
        self.project_root = project_root


# Note: SK_TR_004 is raised as ToolRegistryError with error_code="SK_TR_004"
# for null bytes in tool input (REQ-008). No new class is needed; the
# existing ToolRegistryError is used with the specific error_code.


# ---------------------------------------------------------------------------
# ProcessManager errors
# ---------------------------------------------------------------------------


class ProcessManagerError(StateKanbanError):
    """Base error for ProcessManager operations."""


class InvalidStateTransitionError(ProcessManagerError):
    """Invalid state transition attempted."""

    error_code = "SK_PM_001"
    http_analogy = 409


class SelfTerminationError(ProcessManagerError):
    """Process attempted to terminate itself."""

    error_code = "SK_PM_002"
    http_analogy = 403


class HeartbeatTimeoutError(ProcessManagerError):
    """Heartbeat timeout detected."""

    error_code = "SK_PM_003"
    http_analogy = 408


class HandoffError(ProcessManagerError):
    """Handoff from predecessor failed."""

    error_code = "SK_PM_004"
    http_analogy = 409


# ---------------------------------------------------------------------------
# MessageBus errors
# ---------------------------------------------------------------------------


class MessageBusError(StateKanbanError):
    """Base error for MessageBus operations."""


class SubscriptionError(MessageBusError):
    """Invalid subscription."""

    error_code = "SK_MB_001"
    http_analogy = 400


class SyncCallTimeoutError(MessageBusError):
    """Sync call timed out."""

    error_code = "SK_MB_002"
    http_analogy = 408


# ---------------------------------------------------------------------------
# LLM Adapter errors
# ---------------------------------------------------------------------------


class LLMAdapterError(StateKanbanError):
    """Base error for LLM adapter operations."""


class LLMRateLimitError(LLMAdapterError):
    """API rate limit hit."""

    error_code = "SK_LLM_001"
    http_analogy = 429


class LLMAuthError(LLMAdapterError):
    """Authentication failure."""

    error_code = "SK_LLM_002"
    http_analogy = 401


class LLMResponseParseError(LLMAdapterError):
    """Response parse error."""

    error_code = "SK_LLM_003"
    http_analogy = 500


# ---------------------------------------------------------------------------
# Snapshot errors
# ---------------------------------------------------------------------------


class SnapshotError(StateKanbanError):
    """Base error for snapshot operations."""


class SnapshotIntegrityError(SnapshotError):
    """Snapshot integrity check failed."""

    error_code = "SK_SN_001"
    http_analogy = 422


class SnapshotWriteError(SnapshotError):
    """Snapshot write failed."""

    error_code = "SK_SN_002"
    http_analogy = 500


class SnapshotPathViolationError(SnapshotError):
    """Snapshot path escapes the project root sandbox.

    Error code: SK_SN_003
    REQ-604: Triggered by load_snapshot() when a path traversal
    or out-of-bounds read is detected.
    """

    error_code = "SK_SN_003"
    http_analogy = 403

    def __init__(
        self,
        message: str = "",
        *,
        attempted_path: str = "",
        project_root: str = "",
        error_code: str | None = None,
    ) -> None:
        if not message:
            message = (
                f"Snapshot path violation: '{attempted_path}' "
                f"resolves outside project root '{project_root}'"
            )
        super().__init__(message, error_code=error_code)
        self.attempted_path = attempted_path
        self.project_root = project_root


# ---------------------------------------------------------------------------
# CodexAdapter errors (NEW)
# ---------------------------------------------------------------------------


class CodexAdapterError(StateKanbanError):
    """Base error for CodexAdapter operations."""


class CodexNotAvailableError(CodexAdapterError):
    """Codex CLI not available on PATH."""

    error_code = "SK_CX_001"
    http_analogy = 503


class CodexExecutionError(CodexAdapterError):
    """Codex execution error (non-zero exit code)."""

    error_code = "SK_CX_002"
    http_analogy = 500


class CodexTimeoutError(CodexAdapterError):
    """Codex API call timed out (REQ-006)."""

    error_code = "SK_CX_003"
    http_analogy = 408


# ---------------------------------------------------------------------------
# Engine errors (NEW)
# ---------------------------------------------------------------------------


class EngineError(StateKanbanError):
    """Base error for Engine operations."""


class CircuitBreakerError(EngineError):
    """Circuit breaker fired (max rounds exceeded)."""

    error_code = "SK_EN_001"
    http_analogy = 408


class SignalRoutingError(EngineError):
    """Signal routing error (no matching role)."""

    error_code = "SK_EN_002"
    http_analogy = 400


class ParseRecoveryError(EngineError):
    """Parse recovery failed (consecutive parse errors)."""

    error_code = "SK_EN_003"
    http_analogy = 500


class ValveReworkLoopError(EngineError):
    """Consecutive valve failures detected -- infinite rework loop (REQ-006)."""

    error_code = "SK_EN_004"
    http_analogy = 500


class EngineExternalError(EngineError):
    """External exception converted to internal ErrorSignal.

    Error code: SK_EN_006
    REQ-605: Triggered by Engine._call_llm_for_role() when an
    external API exception is caught and converted to an ErrorSignal
    instead of propagating to the drive loop.
    """

    error_code = "SK_EN_006"
    http_analogy = 500


# ---------------------------------------------------------------------------
# Path errors (REQ-602)
# ---------------------------------------------------------------------------


class PathEscapeError(StateKanbanError):
    """Resolved path escapes the project root sandbox.

    Error code: SK_06_001
    Triggered by Config.resolve_path() when a path traversal is detected.
    """

    error_code = "SK_06_001"
    http_analogy = 403

    def __init__(
        self,
        message: str = "",
        *,
        attempted_path: str = "",
        project_root: str = "",
        error_code: str | None = None,
    ) -> None:
        if not message:
            message = (
                f"Path escape detected: '{attempted_path}' "
                f"resolves outside project root '{project_root}'"
            )
        super().__init__(message, error_code=error_code)
        self.attempted_path = attempted_path
        self.project_root = project_root
