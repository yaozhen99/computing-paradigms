"""StateKanban core: FluidZone, CrystalZone, AuditZone, and StateKanban facade.

Single source of truth for the entire system.
Kernel module -- zero I/O.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from statekanban.core.errors import (
    ArtifactConflictError,
    AppendOnlyViolationError,
    AuditWriteError,
    ConvergenceTimeoutError,
    InvalidSignalError,
    SignalCollisionError,
    SnapshotIntegrityError,
)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SignalType(Enum):
    INTENT = "intent"
    VETO = "veto"
    ERROR = "error"


class ArtifactType(Enum):
    CODE = "code"
    CONFIG = "config"
    DOC = "doc"
    TEST = "test"


class ProcessState(Enum):
    CREATED = "created"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


# ---------------------------------------------------------------------------
# Signal dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Signal:
    """Base signal stored in FluidZone."""

    signal_id: str
    signal_type: SignalType
    author_role: str
    target_id: str
    payload: dict[str, Any]
    timestamp: datetime.datetime
    round_number: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value,
            "author_role": self.author_role,
            "target_id": self.target_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "round_number": self.round_number,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Signal:
        return cls(
            signal_id=data["signal_id"],
            signal_type=SignalType(data["signal_type"]),
            author_role=data["author_role"],
            target_id=data["target_id"],
            payload=data["payload"],
            timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
            round_number=data["round_number"],
        )


@dataclass(frozen=True)
class IntentSignal(Signal):
    """Positive assertion signal."""

    signal_type: SignalType = field(default=SignalType.INTENT, init=False)


@dataclass(frozen=True)
class VetoSignal(Signal):
    """Rejection signal with mandatory reason."""

    signal_type: SignalType = field(default=SignalType.VETO, init=False)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["reason"] = self.reason
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VetoSignal:
        return cls(
            signal_id=data["signal_id"],
            author_role=data["author_role"],
            target_id=data["target_id"],
            payload=data["payload"],
            timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
            round_number=data["round_number"],
            reason=data.get("reason", ""),
        )


@dataclass(frozen=True)
class ErrorSignal(Signal):
    """Error feedback from OutputValve or ToolRegistry."""

    signal_type: SignalType = field(default=SignalType.ERROR, init=False)
    error_code: str = ""
    error_detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["error_code"] = self.error_code
        d["error_detail"] = self.error_detail
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ErrorSignal:
        return cls(
            signal_id=data["signal_id"],
            author_role=data["author_role"],
            target_id=data["target_id"],
            payload=data["payload"],
            timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
            round_number=data["round_number"],
            error_code=data.get("error_code", ""),
            error_detail=data.get("error_detail", ""),
        )


# ---------------------------------------------------------------------------
# Artifact
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Artifact:
    """Immutable artifact stored in CrystalZone."""

    seq_no: int
    artifact_type: ArtifactType
    path: str
    content: str
    checksum: str
    author_role: str
    created_at: datetime.datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq_no": self.seq_no,
            "artifact_type": self.artifact_type.value,
            "path": self.path,
            "content": self.content,
            "checksum": self.checksum,
            "author_role": self.author_role,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Artifact:
        return cls(
            seq_no=data["seq_no"],
            artifact_type=ArtifactType(data["artifact_type"]),
            path=data["path"],
            content=data["content"],
            checksum=data["checksum"],
            author_role=data["author_role"],
            created_at=datetime.datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuditEntry:
    """Append-only audit log entry."""

    entry_id: int
    event_type: str
    actor: str
    action: str
    details: dict[str, Any]
    timestamp: datetime.datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEntry:
        return cls(
            entry_id=data["entry_id"],
            event_type=data["event_type"],
            actor=data["actor"],
            action=data["action"],
            details=data["details"],
            timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
        )


# ---------------------------------------------------------------------------
# ViewportSpec
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ViewportSpec:
    """Defines what a role can see in the kanban."""

    role: str
    visible_signal_types: list[SignalType]
    visible_artifact_types: list[ArtifactType]
    visible_target_patterns: list[str]
    max_tokens: int = 2000
    priority_order: list[str] = field(default_factory=lambda: [
        "role_relevant", "dependency_upstream", "global_summary",
    ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "visible_signal_types": [st.value for st in self.visible_signal_types],
            "visible_artifact_types": [at.value for at in self.visible_artifact_types],
            "visible_target_patterns": self.visible_target_patterns,
            "max_tokens": self.max_tokens,
            "priority_order": self.priority_order,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ViewportSpec:
        return cls(
            role=data["role"],
            visible_signal_types=[SignalType(v) for v in data["visible_signal_types"]],
            visible_artifact_types=[ArtifactType(v) for v in data["visible_artifact_types"]],
            visible_target_patterns=data["visible_target_patterns"],
            max_tokens=data.get("max_tokens", 2000),
            priority_order=data.get("priority_order", [
                "role_relevant", "dependency_upstream", "global_summary",
            ]),
        )


# ---------------------------------------------------------------------------
# ProcessInfo
# ---------------------------------------------------------------------------

@dataclass
class ProcessInfo:
    """Runtime information about a managed process."""

    process_id: str
    role: str
    state: ProcessState
    tool_permits: set[str]
    viewport_spec: ViewportSpec
    heartbeat_at: datetime.datetime | None = None
    last_signal_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "process_id": self.process_id,
            "role": self.role,
            "state": self.state.value,
            "tool_permits": sorted(self.tool_permits),
            "viewport_spec": self.viewport_spec.to_dict(),
            "heartbeat_at": self.heartbeat_at.isoformat() if self.heartbeat_at else None,
            "last_signal_id": self.last_signal_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessInfo:
        return cls(
            process_id=data["process_id"],
            role=data["role"],
            state=ProcessState(data["state"]),
            tool_permits=set(data["tool_permits"]),
            viewport_spec=ViewportSpec.from_dict(data["viewport_spec"]),
            heartbeat_at=(
                datetime.datetime.fromisoformat(data["heartbeat_at"])
                if data.get("heartbeat_at")
                else None
            ),
            last_signal_id=data.get("last_signal_id"),
        )


# ---------------------------------------------------------------------------
# ToolDef
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolDef:
    """Registered tool specification."""

    name: str
    description: str
    param_schema: dict[str, Any]
    required_permissions: set[str]
    timeout_seconds: float = 60.0
    max_retries: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "param_schema": self.param_schema,
            "required_permissions": sorted(self.required_permissions),
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }


# ---------------------------------------------------------------------------
# LLM types
# ---------------------------------------------------------------------------

@dataclass
class LLMMessage:
    """A single message in an LLM conversation."""

    role: str
    content: str | None = None
    tool_use: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None


@dataclass
class LLMResponse:
    """Response from an LLM completion call."""

    content: str | None = None
    tool_use_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# CollisionResult
# ---------------------------------------------------------------------------

@dataclass
class CollisionResult:
    """Result of a collision detection check."""

    has_collision: bool
    signals: list[Signal]
    is_resolved: bool


# ---------------------------------------------------------------------------
# ConvergenceResult
# ---------------------------------------------------------------------------

@dataclass
class ConvergenceResult:
    """Result of a convergence loop."""

    target_id: str
    rounds: int
    converged: bool
    final_signals: list[Signal]
    forced_terminate: bool


# ---------------------------------------------------------------------------
# FluidZone
# ---------------------------------------------------------------------------

class FluidZone:
    """Mutable signal area with collision detection.

    Signals are keyed by (target_id, signal_type, author_role).
    """

    def __init__(self) -> None:
        self._signals: list[Signal] = []
        self._signal_index: dict[tuple[str, str, str], Signal] = {}

    def write_signal(self, signal: Signal) -> None:
        """Write a signal to the fluid zone.

        Args:
            signal: The signal to write.

        Raises:
            InvalidSignalError: Signal fails schema validation.
        """
        self._validate_signal(signal)
        key = (signal.target_id, signal.signal_type.value, signal.author_role)
        self._signal_index[key] = signal
        self._signals.append(signal)

    def read_signals(
        self,
        target_id: str | None = None,
        signal_type: SignalType | None = None,
        author_role: str | None = None,
    ) -> list[Signal]:
        """Read signals matching optional filters.

        Returns:
            List of matching signals, ordered by timestamp ascending.
        """
        results: list[Signal] = []
        for sig in self._signals:
            if target_id is not None and sig.target_id != target_id:
                continue
            if signal_type is not None and sig.signal_type != signal_type:
                continue
            if author_role is not None and sig.author_role != author_role:
                continue
            results.append(sig)
        return results

    def detect_collision(self, target_id: str) -> CollisionResult:
        """Check for conflicting signals on a target.

        A collision exists when there are both INTENT and VETO signals
        for the same target from different authors.

        Returns:
            CollisionResult with collided signals and whether they agree.
        """
        target_signals = self.read_signals(target_id=target_id)
        if not target_signals:
            return CollisionResult(has_collision=False, signals=[], is_resolved=True)

        intent_signals = [s for s in target_signals if s.signal_type == SignalType.INTENT]
        veto_signals = [s for s in target_signals if s.signal_type == SignalType.VETO]

        if not veto_signals:
            return CollisionResult(
                has_collision=False,
                signals=target_signals,
                is_resolved=True,
            )

        has_collision = bool(intent_signals and veto_signals)
        is_resolved = not has_collision

        return CollisionResult(
            has_collision=has_collision,
            signals=target_signals,
            is_resolved=is_resolved,
        )

    def clear_signals(self, target_id: str, round_number_ge: int) -> None:
        """Remove signals for a target at or above a round number.

        Used during convergence to clear stale signals before re-injection.
        """
        self._signals = [
            s for s in self._signals
            if not (s.target_id == target_id and s.round_number >= round_number_ge)
        ]
        # Rebuild index
        self._signal_index = {
            (s.target_id, s.signal_type.value, s.author_role): s
            for s in self._signals
        }

    def _validate_signal(self, signal: Signal) -> None:
        """Validate a signal before writing."""
        if not signal.signal_id:
            raise InvalidSignalError("signal_id is required")
        if not signal.author_role:
            raise InvalidSignalError("author_role is required")
        if not signal.target_id:
            raise InvalidSignalError("target_id is required")
        if not isinstance(signal.signal_type, SignalType):
            raise InvalidSignalError("invalid signal_type")

    def _to_json(self) -> list[dict[str, Any]]:
        """Serialize signals to JSON-serializable list."""
        return [s.to_dict() for s in self._signals]

    def _from_json(self, data: list[dict[str, Any]]) -> None:
        """Reconstruct signals from serialized data."""
        self._signals.clear()
        self._signal_index.clear()
        for item in data:
            sig = self._reconstruct_signal(item)
            self._signals.append(sig)
            key = (sig.target_id, sig.signal_type.value, sig.author_role)
            self._signal_index[key] = sig

    @staticmethod
    def _reconstruct_signal(data: dict[str, Any]) -> Signal:
        """Reconstruct the appropriate Signal subclass from dict data."""
        st = SignalType(data["signal_type"])
        if st == SignalType.VETO:
            return VetoSignal.from_dict(data)
        if st == SignalType.ERROR:
            return ErrorSignal.from_dict(data)
        return Signal.from_dict(data)


# ---------------------------------------------------------------------------
# CrystalZone
# ---------------------------------------------------------------------------

class CrystalZone:
    """Append-only artifact store.

    No update or delete operations are permitted.
    """

    def __init__(self) -> None:
        self._artifacts: dict[int, Artifact] = {}
        self._next_seq_no: int = 1

    def append(self, artifact: Artifact) -> int:
        """Append an artifact.

        Args:
            artifact: The artifact to append. seq_no is auto-assigned if 0.

        Returns:
            The assigned sequence number.

        Raises:
            ArtifactConflictError: seq_no already exists.
            AppendOnlyViolationError: Attempted to modify/delete.
        """
        if artifact.seq_no != 0 and artifact.seq_no in self._artifacts:
            raise ArtifactConflictError(
                f"Sequence number {artifact.seq_no} already exists"
            )

        assigned_seq_no = artifact.seq_no if artifact.seq_no != 0 else self._next_seq_no

        if assigned_seq_no < self._next_seq_no and assigned_seq_no in self._artifacts:
            raise ArtifactConflictError(
                f"Sequence number {assigned_seq_no} already exists"
            )

        # Build artifact with assigned seq_no
        final_artifact = Artifact(
            seq_no=assigned_seq_no,
            artifact_type=artifact.artifact_type,
            path=artifact.path,
            content=artifact.content,
            checksum=artifact.checksum,
            author_role=artifact.author_role,
            created_at=artifact.created_at,
            metadata=artifact.metadata,
        )

        self._artifacts[assigned_seq_no] = final_artifact
        if assigned_seq_no >= self._next_seq_no:
            self._next_seq_no = assigned_seq_no + 1

        return assigned_seq_no

    def read_artifact(self, seq_no: int) -> Artifact | None:
        """Read a single artifact by sequence number."""
        return self._artifacts.get(seq_no)

    def read_artifacts(
        self,
        artifact_type: ArtifactType | None = None,
        author_role: str | None = None,
    ) -> list[Artifact]:
        """Read artifacts matching optional filters."""
        results: list[Artifact] = []
        for seq_no in sorted(self._artifacts.keys()):
            artifact = self._artifacts[seq_no]
            if artifact_type is not None and artifact.artifact_type != artifact_type:
                continue
            if author_role is not None and artifact.author_role != author_role:
                continue
            results.append(artifact)
        return results

    def latest_seq_no(self) -> int:
        """Return the highest sequence number."""
        if not self._artifacts:
            return 0
        return max(self._artifacts.keys())

    def _to_json(self) -> dict[str, Any]:
        """Serialize to JSON-serializable dict."""
        return {
            "artifacts": [a.to_dict() for a in self.read_artifacts()],
            "next_seq_no": self._next_seq_no,
        }

    def _from_json(self, data: dict[str, Any]) -> None:
        """Reconstruct from serialized data."""
        self._artifacts.clear()
        for item in data["artifacts"]:
            artifact = Artifact.from_dict(item)
            self._artifacts[artifact.seq_no] = artifact
        self._next_seq_no = data.get("next_seq_no", max(self._artifacts.keys(), default=0) + 1)


# ---------------------------------------------------------------------------
# AuditZone
# ---------------------------------------------------------------------------

class AuditZone:
    """Append-only audit log."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._next_entry_id: int = 1

    def log(
        self,
        event_type: str,
        actor: str,
        action: str,
        details: dict[str, Any],
    ) -> int:
        """Append an audit entry.

        Returns:
            The assigned entry ID.

        Raises:
            AuditWriteError: If logging fails (should not happen in-memory).
        """
        try:
            entry = AuditEntry(
                entry_id=self._next_entry_id,
                event_type=event_type,
                actor=actor,
                action=action,
                details=details,
                timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
            )
            self._entries.append(entry)
            self._next_entry_id += 1
            return entry.entry_id
        except Exception as exc:
            raise AuditWriteError(f"Audit write failed: {exc}") from exc

    def read_entries(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        since_entry_id: int = 0,
    ) -> list[AuditEntry]:
        """Read audit entries matching optional filters."""
        results: list[AuditEntry] = []
        for entry in self._entries:
            if entry.entry_id <= since_entry_id:
                continue
            if event_type is not None and entry.event_type != event_type:
                continue
            if actor is not None and entry.actor != actor:
                continue
            results.append(entry)
        return results

    def _to_json(self) -> dict[str, Any]:
        """Serialize to JSON-serializable dict."""
        return {
            "entries": [e.to_dict() for e in self._entries],
            "next_entry_id": self._next_entry_id,
        }

    def _from_json(self, data: dict[str, Any]) -> None:
        """Reconstruct from serialized data."""
        self._entries.clear()
        for item in data["entries"]:
            self._entries.append(AuditEntry.from_dict(item))
        self._next_entry_id = data.get("next_entry_id", len(self._entries) + 1)


# ---------------------------------------------------------------------------
# StateKanban (facade)
# ---------------------------------------------------------------------------

class StateKanban:
    """Facade over FluidZone + CrystalZone + AuditZone + ViewportIndex."""

    MAX_CONVERGENCE_ROUNDS = 10

    def __init__(self) -> None:
        self.fluid: FluidZone = FluidZone()
        self.crystal: CrystalZone = CrystalZone()
        self.audit: AuditZone = AuditZone()
        self._viewport_specs: dict[str, ViewportSpec] = {}

    def register_viewport(self, spec: ViewportSpec) -> None:
        """Register a viewport specification for a role."""
        self._viewport_specs[spec.role] = spec

    def get_viewport_spec(self, role: str) -> ViewportSpec | None:
        """Get the viewport specification for a role."""
        return self._viewport_specs.get(role)

    def to_json(self) -> dict[str, Any]:
        """Serialize entire kanban to a JSON-serializable dict.

        Includes a SHA-256 checksum for integrity verification.
        """
        payload = {
            "fluid": self.fluid._to_json(),
            "crystal": self.crystal._to_json(),
            "audit": self.audit._to_json(),
            "viewport_specs": {
                role: spec.to_dict() for role, spec in self._viewport_specs.items()
            },
        }
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        checksum = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        return {
            "data": payload,
            "checksum": checksum,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> StateKanban:
        """Reconstruct kanban from serialized data.

        Args:
            data: Dict produced by to_json().

        Returns:
            Fully reconstructed StateKanban instance.

        Raises:
            SnapshotIntegrityError: Checksum validation failed.
        """
        payload = data.get("data", data)
        stored_checksum = data.get("checksum")

        # Verify checksum if present
        if stored_checksum is not None:
            payload_str = json.dumps(payload, sort_keys=True, default=str)
            computed_checksum = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
            if computed_checksum != stored_checksum:
                raise SnapshotIntegrityError(
                    "Snapshot integrity check failed: checksum mismatch"
                )

        kanban = cls()

        # Reconstruct FluidZone
        if "fluid" in payload:
            kanban.fluid._from_json(payload["fluid"])

        # Reconstruct CrystalZone
        if "crystal" in payload:
            kanban.crystal._from_json(payload["crystal"])

        # Reconstruct AuditZone
        if "audit" in payload:
            kanban.audit._from_json(payload["audit"])

        # Reconstruct ViewportSpecs
        if "viewport_specs" in payload:
            for role, spec_data in payload["viewport_specs"].items():
                kanban._viewport_specs[role] = ViewportSpec.from_dict(spec_data)

        return kanban

    def run_convergence(self, target_id: str) -> ConvergenceResult:
        """Execute convergence loop for a target.

        Drives the cycle of collision detection until signals agree
        or max rounds exceeded.

        Returns:
            ConvergenceResult with round count and outcome.
        """
        for round_num in range(1, self.MAX_CONVERGENCE_ROUNDS + 1):
            collision = self.fluid.detect_collision(target_id)

            if not collision.has_collision:
                return ConvergenceResult(
                    target_id=target_id,
                    rounds=round_num,
                    converged=True,
                    final_signals=collision.signals,
                    forced_terminate=False,
                )

            if collision.is_resolved:
                return ConvergenceResult(
                    target_id=target_id,
                    rounds=round_num,
                    converged=True,
                    final_signals=collision.signals,
                    forced_terminate=False,
                )

        # Max rounds exceeded -- force terminate
        final_signals = self.fluid.read_signals(target_id=target_id)
        self.audit.log(
            event_type="convergence_timeout",
            actor="StateKanban",
            action="force_terminate",
            details={
                "target_id": target_id,
                "rounds": self.MAX_CONVERGENCE_ROUNDS,
            },
        )
        return ConvergenceResult(
            target_id=target_id,
            rounds=self.MAX_CONVERGENCE_ROUNDS,
            converged=False,
            final_signals=final_signals,
            forced_terminate=True,
        )


# ---------------------------------------------------------------------------
# Utility: create signals
# ---------------------------------------------------------------------------

def make_signal_id() -> str:
    """Generate a new UUID4 signal ID."""
    return str(uuid.uuid4())


def now_utc() -> datetime.datetime:
    """Return current UTC datetime."""
    return datetime.datetime.now(tz=datetime.timezone.utc)


def compute_checksum(content: str) -> str:
    """Compute SHA-256 checksum of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
