"""Tests for Error hierarchy: codes, HTTP analogies, inheritance."""

from __future__ import annotations

import pytest

from statekanban.core.errors import (
    ArtifactConflictError,
    AppendOnlyViolationError,
    AuditWriteError,
    AuditZoneError,
    AtomicWriteError,
    ConvergenceTimeoutError,
    CrystalZoneError,
    FluidZoneError,
    HandoffError,
    HeartbeatTimeoutError,
    HumanGateRejectedError,
    InvalidSignalError,
    InvalidStateTransitionError,
    InvalidViewportSpecError,
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseParseError,
    LLMAdapterError,
    MessageBusError,
    PermissionDeniedError,
    ProcessManagerError,
    SelfTerminationError,
    SignalCollisionError,
    SliceOverflowError,
    SnapshotIntegrityError,
    SnapshotWriteError,
    StateKanbanError,
    SubscriptionError,
    SyncCallTimeoutError,
    SyntaxCheckError,
    TestExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    TypeCheckError,
    ValidationFailedError,
    ViewportError,
    OutputValveError,
    ToolRegistryError,
    SnapshotError,
)


# Mapping of error class -> (expected_code, expected_http)
ERROR_CONTRACT = {
    InvalidSignalError: ("SK_FZ_001", 400),
    SignalCollisionError: ("SK_FZ_002", 409),
    ConvergenceTimeoutError: ("SK_FZ_003", 408),
    ArtifactConflictError: ("SK_CZ_001", 409),
    AppendOnlyViolationError: ("SK_CZ_002", 405),
    AuditWriteError: ("SK_AZ_001", 500),
    InvalidViewportSpecError: ("SK_VS_001", 400),
    SliceOverflowError: ("SK_VS_002", 413),
    SyntaxCheckError: ("SK_OV_001", 422),
    TypeCheckError: ("SK_OV_002", 422),
    TestExecutionError: ("SK_OV_003", 422),
    AtomicWriteError: ("SK_OV_004", 500),
    HumanGateRejectedError: ("SK_OV_005", 403),
    PermissionDeniedError: ("SK_TR_001", 403),
    ToolNotFoundError: ("SK_TR_002", 404),
    ToolTimeoutError: ("SK_TR_003", 408),
    InvalidStateTransitionError: ("SK_PM_001", 409),
    SelfTerminationError: ("SK_PM_002", 403),
    HeartbeatTimeoutError: ("SK_PM_003", 408),
    HandoffError: ("SK_PM_004", 409),
    SubscriptionError: ("SK_MB_001", 400),
    SyncCallTimeoutError: ("SK_MB_002", 408),
    LLMRateLimitError: ("SK_LLM_001", 429),
    LLMAuthError: ("SK_LLM_002", 401),
    LLMResponseParseError: ("SK_LLM_003", 500),
    SnapshotIntegrityError: ("SK_SN_001", 422),
    SnapshotWriteError: ("SK_SN_002", 500),
}

# Inheritance contract from architecture section 4.1
INHERITANCE_CONTRACT = {
    InvalidSignalError: [FluidZoneError, StateKanbanError],
    SignalCollisionError: [FluidZoneError, StateKanbanError],
    ConvergenceTimeoutError: [FluidZoneError, StateKanbanError],
    ArtifactConflictError: [CrystalZoneError, StateKanbanError],
    AppendOnlyViolationError: [CrystalZoneError, StateKanbanError],
    AuditWriteError: [AuditZoneError, StateKanbanError],
    InvalidViewportSpecError: [ViewportError, StateKanbanError],
    SliceOverflowError: [ViewportError, StateKanbanError],
    SyntaxCheckError: [ValidationFailedError, OutputValveError, StateKanbanError],
    TypeCheckError: [ValidationFailedError, OutputValveError, StateKanbanError],
    TestExecutionError: [ValidationFailedError, OutputValveError, StateKanbanError],
    AtomicWriteError: [OutputValveError, StateKanbanError],
    HumanGateRejectedError: [OutputValveError, StateKanbanError],
    PermissionDeniedError: [ToolRegistryError, StateKanbanError],
    ToolNotFoundError: [ToolRegistryError, StateKanbanError],
    ToolTimeoutError: [ToolRegistryError, StateKanbanError],
    InvalidStateTransitionError: [ProcessManagerError, StateKanbanError],
    SelfTerminationError: [ProcessManagerError, StateKanbanError],
    HeartbeatTimeoutError: [ProcessManagerError, StateKanbanError],
    HandoffError: [ProcessManagerError, StateKanbanError],
    SubscriptionError: [MessageBusError, StateKanbanError],
    SyncCallTimeoutError: [MessageBusError, StateKanbanError],
    LLMRateLimitError: [LLMAdapterError, StateKanbanError],
    LLMAuthError: [LLMAdapterError, StateKanbanError],
    LLMResponseParseError: [LLMAdapterError, StateKanbanError],
    SnapshotIntegrityError: [SnapshotError, StateKanbanError],
    SnapshotWriteError: [SnapshotError, StateKanbanError],
}


class TestErrorCodes:
    """TC-EC-001 ~ TC-EC-027: Error code matches API contract."""

    @pytest.mark.parametrize(
        "error_class,expected_code,expected_http",
        [(cls, code, http) for cls, (code, http) in ERROR_CONTRACT.items()],
        ids=[cls.__name__ for cls in ERROR_CONTRACT],
    )
    def test_error_code(self, error_class, expected_code, expected_http):
        # TC-EC-001..027
        instance = error_class("test")
        assert instance.error_code == expected_code
        assert instance.http_analogy == expected_http


class TestErrorInheritance:
    """TC-EC-029: Error inheritance chain matches architecture 4.1."""

    @pytest.mark.parametrize(
        "error_class,expected_ancestors",
        list(INHERITANCE_CONTRACT.items()),
        ids=[cls.__name__ for cls in INHERITANCE_CONTRACT],
    )
    def test_inheritance(self, error_class, expected_ancestors):
        for ancestor in expected_ancestors:
            assert issubclass(error_class, ancestor), \
                f"{error_class.__name__} is not a subclass of {ancestor.__name__}"