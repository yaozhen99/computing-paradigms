"""Tests for ResultSummarizer (R2).

TC-RS-001..006: Converged, forced terminate, signal counts,
artifact files, empty, duration.
"""

from __future__ import annotations

import datetime

import pytest

from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    IntentSignal,
    LLMResponse,
    SignalType,
    StateKanban,
    VetoSignal,
    ErrorSignal,
    compute_checksum,
    make_signal_id,
    now_utc,
    ViewportSpec,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.engine.result import EngineResult, ResultSummarizer


# ---------------------------------------------------------------------------
# TC-RS-001: Summarize converged
# ---------------------------------------------------------------------------

class TestResultSummarizerConverged:
    """TC-RS-001."""

    def test_summarize_converged_1_round(self, kanban, pm, summarizer):
        result = summarizer.summarize(total_rounds=1, converged=True)
        assert result.converged is True
        assert result.forced_terminate is False
        assert result.total_rounds == 1


# ---------------------------------------------------------------------------
# TC-RS-002: Summarize forced terminate
# ---------------------------------------------------------------------------

class TestResultSummarizerForcedTerminate:
    """TC-RS-002."""

    def test_summarize_forced_terminate(self, kanban, pm, summarizer):
        result = summarizer.summarize(
            total_rounds=10,
            converged=False,
            forced_terminate=True,
        )
        assert result.converged is False
        assert result.forced_terminate is True
        assert result.total_rounds == 10


# ---------------------------------------------------------------------------
# TC-RS-003: Signal counts
# ---------------------------------------------------------------------------

class TestResultSummarizerSignalCounts:
    """TC-RS-003."""

    def test_signal_counts_with_signals(self, kanban, pm, summarizer):
        # Write some signals
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="t1",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        ))
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="t1",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        ))
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="t2",
            payload={},
            timestamp=now_utc(),
            round_number=2,
        ))
        kanban.fluid.write_signal(VetoSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="t1",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            reason="bad",
        ))
        kanban.fluid.write_signal(ErrorSignal(
            signal_id=make_signal_id(),
            author_role="OutputValve",
            target_id="output.py",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            error_code="SK_OV_001",
            error_detail="syntax error",
        ))
        kanban.fluid.write_signal(ErrorSignal(
            signal_id=make_signal_id(),
            author_role="ResponseParser",
            target_id="parse_failure",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            error_code="SK_EN_003",
            error_detail="parse error",
        ))

        result = summarizer.summarize(total_rounds=2, converged=True)
        assert result.signal_summary["intent"] == 3
        assert result.signal_summary["veto"] == 1
        assert result.signal_summary["error"] == 2


# ---------------------------------------------------------------------------
# TC-RS-004: Artifact files
# ---------------------------------------------------------------------------

class TestResultSummarizerArtifactFiles:
    """TC-RS-004."""

    def test_artifact_files_with_artifacts(self, kanban, pm, summarizer):
        kanban.crystal.append(Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path="src/output.py",
            content="x = 1",
            checksum=compute_checksum("x = 1"),
            author_role="coder",
            created_at=now_utc(),
        ))
        kanban.crystal.append(Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path="src/helper.py",
            content="def help(): pass",
            checksum=compute_checksum("def help(): pass"),
            author_role="coder",
            created_at=now_utc(),
        ))

        result = summarizer.summarize(total_rounds=1, converged=True)
        assert "src/output.py" in result.artifact_files
        assert "src/helper.py" in result.artifact_files


# ---------------------------------------------------------------------------
# TC-RS-005: Empty (no signals, no artifacts)
# ---------------------------------------------------------------------------

class TestResultSummarizerEmpty:
    """TC-RS-005."""

    def test_empty_kanban(self, kanban, pm, summarizer):
        result = summarizer.summarize(total_rounds=0, converged=True)
        assert result.signal_summary["intent"] == 0
        assert result.signal_summary["veto"] == 0
        assert result.signal_summary["error"] == 0
        assert result.artifact_files == []


# ---------------------------------------------------------------------------
# TC-RS-006: Duration calculation
# ---------------------------------------------------------------------------

class TestResultSummarizerDuration:
    """TC-RS-006."""

    def test_duration_with_start_time(self, kanban, pm, summarizer):
        start_time = datetime.datetime.now(tz=datetime.timezone.utc)
        result = summarizer.summarize(
            total_rounds=1,
            converged=True,
            start_time=start_time,
        )
        assert result.duration_seconds >= 0.0

    def test_duration_without_start_time(self, kanban, pm, summarizer):
        result = summarizer.summarize(total_rounds=1, converged=True)
        assert result.duration_seconds == 0.0


# ---------------------------------------------------------------------------
# EngineResult contract
# ---------------------------------------------------------------------------

class TestEngineResultContract:
    """Verify all fields of EngineResult exist."""

    def test_engine_result_fields(self):
        result = EngineResult(
            converged=True,
            forced_terminate=False,
            total_rounds=1,
            artifact_files=["a.py"],
            signal_summary={"intent": 1, "veto": 0, "error": 0},
            error_count=0,
            duration_seconds=1.5,
        )
        assert result.converged is True
        assert result.forced_terminate is False
        assert result.total_rounds == 1
        assert result.artifact_files == ["a.py"]
        assert result.signal_summary["intent"] == 1
        assert result.error_count == 0
        assert result.duration_seconds == 1.5

    def test_engine_result_defaults(self):
        result = EngineResult(
            converged=False,
            forced_terminate=True,
            total_rounds=10,
        )
        assert result.artifact_files == []
        assert result.signal_summary == {}
        assert result.error_count == 0
        assert result.duration_seconds == 0.0