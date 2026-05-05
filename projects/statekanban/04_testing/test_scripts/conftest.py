"""conftest.py: shared fixtures for StateKanban tests."""

from __future__ import annotations

import os
import tempfile

import pytest

from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    ErrorSignal,
    FluidZone,
    CrystalZone,
    AuditZone,
    IntentSignal,
    ProcessState,
    SignalType,
    StateKanban,
    VetoSignal,
    ViewportSpec,
    make_signal_id,
    now_utc,
    compute_checksum,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.config import Config


# ---------------------------------------------------------------------------
# Signal factory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def make_intent():
    """Factory for IntentSignal."""
    def _make(
        target_id: str = "target_A",
        author_role: str = "coder",
        round_number: int = 0,
        signal_id: str | None = None,
        payload: dict | None = None,
    ) -> IntentSignal:
        return IntentSignal(
            signal_id=signal_id or make_signal_id(),
            author_role=author_role,
            target_id=target_id,
            payload=payload or {"action": "approve"},
            timestamp=now_utc(),
            round_number=round_number,
        )
    return _make


@pytest.fixture
def make_veto():
    """Factory for VetoSignal."""
    def _make(
        target_id: str = "target_A",
        author_role: str = "reviewer",
        reason: str = "bug found",
        round_number: int = 0,
        signal_id: str | None = None,
    ) -> VetoSignal:
        return VetoSignal(
            signal_id=signal_id or make_signal_id(),
            author_role=author_role,
            target_id=target_id,
            payload={"action": "reject"},
            timestamp=now_utc(),
            round_number=round_number,
            reason=reason,
        )
    return _make


@pytest.fixture
def make_error_signal():
    """Factory for ErrorSignal."""
    def _make(
        target_id: str = "target_A",
        author_role: str = "OutputValve",
        error_code: str = "SK_OV_001",
        error_detail: str = "syntax error",
    ) -> ErrorSignal:
        return ErrorSignal(
            signal_id=make_signal_id(),
            author_role=author_role,
            target_id=target_id,
            payload={},
            timestamp=now_utc(),
            round_number=0,
            error_code=error_code,
            error_detail=error_detail,
        )
    return _make


# ---------------------------------------------------------------------------
# Zone fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fluid():
    """Fresh FluidZone."""
    return FluidZone()


@pytest.fixture
def crystal():
    """Fresh CrystalZone."""
    return CrystalZone()


@pytest.fixture
def audit():
    """Fresh AuditZone."""
    return AuditZone()


@pytest.fixture
def kanban():
    """Fresh StateKanban."""
    return StateKanban()


# ---------------------------------------------------------------------------
# Artifact factory
# ---------------------------------------------------------------------------

@pytest.fixture
def make_artifact():
    """Factory for Artifact."""
    counter = 0

    def _make(
        artifact_type: ArtifactType = ArtifactType.CODE,
        path: str = "output.py",
        content: str = "x = 1",
        author_role: str = "coder",
        seq_no: int = 0,
    ) -> Artifact:
        nonlocal counter
        counter += 1
        return Artifact(
            seq_no=seq_no,
            artifact_type=artifact_type,
            path=path,
            content=content,
            checksum=compute_checksum(content),
            author_role=author_role,
            created_at=now_utc(),
            metadata={"counter": counter},
        )
    return _make


# ---------------------------------------------------------------------------
# ViewportSpec fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def coder_spec():
    """ViewportSpec for coder role."""
    return ViewportSpec(
        role="coder",
        visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
        visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG],
        visible_target_patterns=["*"],
        max_tokens=2000,
    )


@pytest.fixture
def reviewer_spec():
    """ViewportSpec for reviewer role."""
    return ViewportSpec(
        role="reviewer",
        visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
        visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG, ArtifactType.DOC],
        visible_target_patterns=["*"],
        max_tokens=2000,
    )


@pytest.fixture
def tester_spec():
    """ViewportSpec for tester role."""
    return ViewportSpec(
        role="tester",
        visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
        visible_artifact_types=[ArtifactType.CODE, ArtifactType.TEST],
        visible_target_patterns=["*"],
        max_tokens=2000,
    )


# ---------------------------------------------------------------------------
# Infrastructure fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bus(kanban):
    """MessageBus bound to kanban."""
    return MessageBus(kanban)


@pytest.fixture
def registry(kanban):
    """ToolRegistry bound to kanban."""
    return ToolRegistry(kanban)


@pytest.fixture
def valve(kanban):
    """OutputValve bound to kanban."""
    return OutputValve(kanban=kanban)


@pytest.fixture
def pm(kanban, bus):
    """ProcessManager bound to kanban and bus."""
    return ProcessManager(kanban, bus)


@pytest.fixture
def slicer(kanban, coder_spec, reviewer_spec, tester_spec):
    """ViewportSlicer with default specs."""
    specs = {
        "coder": coder_spec,
        "reviewer": reviewer_spec,
        "tester": tester_spec,
    }
    for spec in specs.values():
        kanban.register_viewport(spec)
    return ViewportSlicer(kanban, specs)


@pytest.fixture
def tmp_dir():
    """Temporary directory for file writes."""
    with tempfile.TemporaryDirectory(prefix="sk_test_") as d:
        yield d


@pytest.fixture
def config():
    """Default Config."""
    return Config()