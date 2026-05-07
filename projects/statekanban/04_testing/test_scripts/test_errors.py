"""
StateKanban Error Code Tests — R3
TC-ERR-01 through TC-ERR-07
Tests for new error codes: SK_CX_003, SK_EN_004, SK_TR_004
Plus regression tests for existing error codes.
"""

from __future__ import annotations

import re

import pytest

from statekanban.core.errors import (
    # Base
    StateKanbanError,
    # FluidZone errors
    FluidZoneError,
    InvalidSignalError,
    SignalCollisionError,
    ConvergenceTimeoutError,
    # CrystalZone errors
    CrystalZoneError,
    ArtifactConflictError,
    AppendOnlyViolationError,
    # AuditZone errors
    AuditZoneError,
    AuditWriteError,
    # Viewport errors
    ViewportError,
    InvalidViewportSpecError,
    SliceOverflowError,
    # Valve errors
    OutputValveError,
    ValidationFailedError,
    SyntaxCheckError,
    TypeCheckError,
    AtomicWriteError,
    HumanGateRejectedError,
    # Registry errors
    ToolRegistryError,
    PermissionDeniedError,
    ToolNotFoundError,
    ToolTimeoutError,
    # Process errors
    ProcessManagerError,
    InvalidStateTransitionError,
    SelfTerminationError,
    HeartbeatTimeoutError,
    HandoffError,
    # Bus errors
    MessageBusError,
    SubscriptionError,
    SyncCallTimeoutError,
    # LLM errors
    LLMAdapterError,
    LLMRateLimitError,
    LLMAuthError,
    LLMResponseParseError,
    # Snapshot errors
    SnapshotError,
    SnapshotIntegrityError,
    SnapshotWriteError,
    # Engine errors
    EngineError,
    CircuitBreakerError,
    SignalRoutingError,
    ParseRecoveryError,
    # Codex errors
    CodexAdapterError,
    CodexNotAvailableError,
    CodexExecutionError,
    CodexTimeoutError,
    # ValveReworkLoopError (R3)
    ValveReworkLoopError,
)
from statekanban.core.kanban import LLMMessage
from statekanban.adapters.codex_adapter import CodexAdapter


# ---------------------------------------------------------------------------
# R1/R2 Error Codes (regression)
# ---------------------------------------------------------------------------

class TestR1R2ErrorCodes:
    """Regression: R1/R2 error codes."""

    @pytest.mark.parametrize("error_class,expected_code", [
        (InvalidSignalError, "SK_FZ_001"),
        (SignalCollisionError, "SK_FZ_002"),
        (ConvergenceTimeoutError, "SK_FZ_003"),
        (ArtifactConflictError, "SK_CZ_001"),
        (AppendOnlyViolationError, "SK_CZ_002"),
        (AuditWriteError, "SK_AZ_001"),
        (InvalidViewportSpecError, "SK_VS_001"),
        (SliceOverflowError, "SK_VS_002"),
        (SyntaxCheckError, "SK_OV_001"),
        (TypeCheckError, "SK_OV_002"),
        (AtomicWriteError, "SK_OV_004"),
        (HumanGateRejectedError, "SK_OV_005"),
        (PermissionDeniedError, "SK_TR_001"),
        (ToolNotFoundError, "SK_TR_002"),
        (ToolTimeoutError, "SK_TR_003"),
        (InvalidStateTransitionError, "SK_PM_001"),
        (SelfTerminationError, "SK_PM_002"),
        (HeartbeatTimeoutError, "SK_PM_003"),
        (HandoffError, "SK_PM_004"),
        (SubscriptionError, "SK_MB_001"),
        (SyncCallTimeoutError, "SK_MB_002"),
        (LLMRateLimitError, "SK_LLM_001"),
        (LLMAuthError, "SK_LLM_002"),
        (LLMResponseParseError, "SK_LLM_003"),
        (SnapshotIntegrityError, "SK_SN_001"),
        (SnapshotWriteError, "SK_SN_002"),
        (CircuitBreakerError, "SK_EN_001"),
        (SignalRoutingError, "SK_EN_002"),
        (ParseRecoveryError, "SK_EN_003"),
        (CodexNotAvailableError, "SK_CX_001"),
        (CodexExecutionError, "SK_CX_002"),
    ])
    def test_error_code(self, error_class, expected_code):
        instance = error_class("test message")
        assert instance.error_code == expected_code


# ---------------------------------------------------------------------------
# TC-ERR-01..02: SK_CX_003 — CodexTimeoutError
# ---------------------------------------------------------------------------

class TestSKCX003:

    def test_codex_timeout_error_code(self):
        """TC-ERR-01: CodexTimeoutError has SK_CX_003."""
        err = CodexTimeoutError("timed out")
        assert err.error_code == "SK_CX_003"

    def test_codex_timeout_http_analogy(self):
        err = CodexTimeoutError("timed out")
        assert err.http_analogy == 408

    def test_codex_timeout_hierarchy(self):
        """TC-ERR-02: CodexTimeoutError inherits from CodexAdapterError."""
        err = CodexTimeoutError("timed out")
        assert isinstance(err, CodexAdapterError)
        assert isinstance(err, StateKanbanError)


# ---------------------------------------------------------------------------
# TC-ERR-03..04: SK_EN_004 — ValveReworkLoopError
# ---------------------------------------------------------------------------

class TestSKEN004:

    def test_valve_rework_loop_error_code(self):
        """TC-ERR-03: ValveReworkLoopError has SK_EN_004."""
        err = ValveReworkLoopError("3 consecutive failures")
        assert err.error_code == "SK_EN_004"

    def test_valve_rework_loop_http_analogy(self):
        err = ValveReworkLoopError("3 consecutive failures")
        assert err.http_analogy == 500

    def test_valve_rework_loop_hierarchy(self):
        """TC-ERR-04: ValveReworkLoopError inherits from EngineError."""
        err = ValveReworkLoopError("3 consecutive failures")
        assert isinstance(err, EngineError)
        assert isinstance(err, StateKanbanError)


# ---------------------------------------------------------------------------
# TC-ERR-05: SK_TR_004
# ---------------------------------------------------------------------------

class TestSKTR004:

    def test_tool_registry_error_sk_tr_004(self):
        """TC-ERR-05: ToolRegistryError with SK_TR_004."""
        err = ToolRegistryError("null bytes detected", error_code="SK_TR_004")
        assert err.error_code == "SK_TR_004"

    def test_tool_registry_error_is_state_kanban_error(self):
        err = ToolRegistryError("unauthorized", error_code="SK_TR_004")
        assert isinstance(err, StateKanbanError)


# ---------------------------------------------------------------------------
# TC-ERR-06: CodexAdapter null bytes
# ---------------------------------------------------------------------------

class TestCodexNullBytes:

    @pytest.mark.asyncio
    async def test_codex_adapter_null_bytes_raises(self):
        """TC-ERR-06: CodexAdapter.complete raises SK_TR_004 on null bytes."""
        adapter = CodexAdapter()
        with pytest.raises(ToolRegistryError) as exc_info:
            await adapter.complete(
                messages=[LLMMessage(role="user", content="bad\x00content")]
            )
        assert exc_info.value.error_code == "SK_TR_004"

    @pytest.mark.asyncio
    async def test_codex_adapter_null_bytes_in_system_message(self):
        adapter = CodexAdapter()
        with pytest.raises(ToolRegistryError) as exc_info:
            await adapter.complete(
                messages=[
                    LLMMessage(role="system", content="system\x00prompt"),
                    LLMMessage(role="user", content="hello"),
                ]
            )
        assert exc_info.value.error_code == "SK_TR_004"


# ---------------------------------------------------------------------------
# TC-ERR-07: call_codex null bytes
# ---------------------------------------------------------------------------

class TestCallCodexNullBytes:

    @pytest.mark.asyncio
    async def test_call_codex_null_bytes_returns_error(self):
        """TC-ERR-07: call_codex returns SK_TR_004 error dict."""
        from statekanban.tools.call_codex import create_call_codex_tool
        adapter = CodexAdapter()
        tool = create_call_codex_tool(adapter)

        result = await tool({"prompt": "bad\x00prompt", "output_path": ""})
        assert result["success"] is False
        assert result["error_code"] == "SK_TR_004"


# ---------------------------------------------------------------------------
# Error code format validation
# ---------------------------------------------------------------------------

class TestErrorCodeFormat:

    def test_error_code_pattern(self):
        """All error codes match SK_XX_NNN pattern."""
        pattern = re.compile(r"^SK_[A-Z]{2}_\d{3}$")
        test_errors = [
            CodexTimeoutError("test"),
            ValveReworkLoopError("test"),
            ToolRegistryError("test", error_code="SK_TR_004"),
        ]
        for err in test_errors:
            assert pattern.match(err.error_code), f"Error code {err.error_code} doesn't match"

    def test_http_analogy_range(self):
        """HTTP analogies are valid status codes."""
        test_errors = [
            CodexTimeoutError("test"),
            ValveReworkLoopError("test"),
        ]
        for err in test_errors:
            assert 100 <= err.http_analogy <= 599