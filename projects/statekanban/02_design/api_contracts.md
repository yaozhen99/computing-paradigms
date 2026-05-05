# StateKanban -- API Contracts (Round 2)

> Incremental update over Round 1. Adds Engine module, CodexAdapter, call_codex tool,
> LLM response parsing, convergence detection, role scheduling, circuit breaker,
> and result summarizer contracts.

## 1. Core Data Structures (Updated)

### 1.1 Signal Types (Unchanged from Round 1)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import datetime


class SignalType(Enum):
    INTENT = "intent"
    VETO = "veto"
    ERROR = "error"


@dataclass(frozen=True)
class Signal:
    """Base signal stored in FluidZone."""
    signal_id: str                    # UUID4
    signal_type: SignalType
    author_role: str                  # e.g. "coder", "reviewer"
    target_id: str                    # artifact or decision target
    payload: dict[str, Any]           # role-specific data
    timestamp: datetime.datetime      # UTC, monotonic within session
    round_number: int                 # convergence round (0 = initial)

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Signal": ...


@dataclass(frozen=True)
class IntentSignal(Signal):
    """Positive assertion signal."""
    signal_type: SignalType = field(default=SignalType.INTENT, init=False)


@dataclass(frozen=True)
class VetoSignal(Signal):
    """Rejection signal with mandatory reason."""
    signal_type: SignalType = field(default=SignalType.VETO, init=False)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VetoSignal": ...


@dataclass(frozen=True)
class ErrorSignal(Signal):
    """Error feedback from OutputValve, ToolRegistry, or ResponseParser."""
    signal_type: SignalType = field(default=SignalType.ERROR, init=False)
    error_code: str = ""
    error_detail: str = ""

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ErrorSignal": ...
```

### 1.2 Artifact Types (Unchanged from Round 1)

```python
class ArtifactType(Enum):
    CODE = "code"
    CONFIG = "config"
    DOC = "doc"
    TEST = "test"


@dataclass(frozen=True)
class Artifact:
    """Immutable artifact stored in CrystalZone."""
    seq_no: int                       # monotonically increasing
    artifact_type: ArtifactType
    path: str                         # target filesystem path
    content: str                      # file content
    checksum: str                     # SHA-256 of content
    author_role: str
    created_at: datetime.datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Artifact": ...
```

### 1.3 Audit Entry (Unchanged from Round 1)

```python
@dataclass(frozen=True)
class AuditEntry:
    """Append-only audit log entry."""
    entry_id: int                     # monotonically increasing
    event_type: str                   # "tool_call", "signal_write", "parse_attempt", etc.
    actor: str                        # role or module name
    action: str                       # verb describing the action
    details: dict[str, Any]           # event-specific data
    timestamp: datetime.datetime

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditEntry": ...
```

### 1.4 Viewport Specification (Unchanged from Round 1)

```python
@dataclass(frozen=True)
class ViewportSpec:
    """Defines what a role can see in the kanban."""
    role: str
    visible_signal_types: list[SignalType]
    visible_artifact_types: list[ArtifactType]
    visible_target_patterns: list[str]   # glob-like patterns for target_id filtering
    max_tokens: int = 2000
    priority_order: list[str] = field(default_factory=lambda: [
        "role_relevant", "dependency_upstream", "global_summary"
    ])
```

### 1.5 Process State (Unchanged from Round 1)

```python
class ProcessState(Enum):
    CREATED = "created"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


@dataclass
class ProcessInfo:
    """Runtime information about a managed process."""
    process_id: str                   # UUID4
    role: str
    state: ProcessState
    tool_permits: set[str]            # allowed tool names
    viewport_spec: ViewportSpec
    heartbeat_at: datetime.datetime | None = None
    last_signal_id: str | None = None

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessInfo": ...
```

### 1.6 Tool Definition (Unchanged from Round 1)

```python
@dataclass(frozen=True)
class ToolDef:
    """Registered tool specification."""
    name: str                         # e.g. "write_file"
    description: str
    param_schema: dict[str, Any]      # JSON Schema for parameters
    required_permissions: set[str]    # roles that may call this tool
    timeout_seconds: float = 60.0
    max_retries: int = 0
```

### 1.7 LLM Types (Unchanged from Round 1)

```python
@dataclass
class LLMMessage:
    role: str                         # "user", "assistant", "tool_result"
    content: str | None = None
    tool_use: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None


@dataclass
class LLMResponse:
    content: str | None = None
    tool_use_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = ""           # "end_turn", "tool_use", "max_tokens"
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
```

### 1.8 NEW: ParsedResponse Types

```python
class ParsedResponseType(Enum):
    """Types of parsed LLM responses."""
    INTENT = "intent"
    VETO = "veto"
    ARTIFACT = "artifact"
    ERROR = "error"


@dataclass(frozen=True)
class ParsedResponse:
    """Result of parsing an LLM raw response into typed signals."""
    response_type: ParsedResponseType
    target_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    reason: str = ""                  # for veto
    artifact_path: str = ""           # for artifact
    artifact_content: str = ""        # for artifact
    artifact_type: str = "code"       # for artifact
    parse_success: bool = True
    parse_error: str = ""             # if parse_success is False
```

### 1.9 NEW: ConvergenceCheckResult

```python
@dataclass(frozen=True)
class ConvergenceCheckResult:
    """Result of checking convergence for a target at a given round."""
    target_id: str
    round_number: int
    converged: bool
    intent_count: int                 # number of intent signals in this round
    veto_count: int                   # number of veto signals in this round
```

### 1.10 NEW: EngineResult

```python
@dataclass(frozen=True)
class EngineResult:
    """Summary of a completed drive loop execution."""
    converged: bool
    forced_terminate: bool
    total_rounds: int
    artifact_files: list[str] = field(default_factory=list)
    signal_summary: dict[str, int] = field(default_factory=dict)  # {signal_type: count}
    error_count: int = 0
    duration_seconds: float = 0.0
```

## 2. Module APIs

### 2.1 StateKanban (Unchanged from Round 1)

```python
class FluidZone:
    """Mutable signal area with collision detection."""

    def write_signal(self, signal: Signal) -> None:
        """Write a signal to the fluid zone.

        Args:
            signal: The signal to write.

        Raises:
            InvalidSignalError: Signal fails schema validation.
        """

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

    def detect_collision(self, target_id: str) -> CollisionResult:
        """Check for conflicting signals on a target.

        Returns:
            CollisionResult with collided signals and whether they agree.
        """

    def clear_signals(self, target_id: str, round_number_ge: int) -> None:
        """Remove signals for a target at or above a round number."""
        ...


class CollisionResult:
    has_collision: bool
    signals: list[Signal]
    is_resolved: bool                 # True if all signals agree


class CrystalZone:
    """Append-only artifact store."""

    def append(self, artifact: Artifact) -> int: ...
    def read_artifact(self, seq_no: int) -> Artifact | None: ...
    def read_artifacts(
        self,
        artifact_type: ArtifactType | None = None,
        author_role: str | None = None,
    ) -> list[Artifact]: ...
    def latest_seq_no(self) -> int: ...


class AuditZone:
    """Append-only audit log."""

    def log(self, event_type: str, actor: str, action: str,
            details: dict[str, Any]) -> int: ...
    def read_entries(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        since_entry_id: int = 0,
    ) -> list[AuditEntry]: ...


class StateKanban:
    """Facade over FluidZone + CrystalZone + AuditZone + ViewportIndex."""

    MAX_CONVERGENCE_ROUNDS: int = 10

    def __init__(self) -> None:
        self.fluid: FluidZone
        self.crystal: CrystalZone
        self.audit: AuditZone

    def register_viewport(self, spec: ViewportSpec) -> None: ...
    def get_viewport_spec(self, role: str) -> ViewportSpec | None: ...
    def to_json(self) -> dict[str, Any]: ...
    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StateKanban": ...
    def run_convergence(self, target_id: str) -> ConvergenceResult: ...


class ConvergenceResult:
    target_id: str
    rounds: int
    converged: bool
    final_signals: list[Signal]
    forced_terminate: bool
```

### 2.2 MessageBus (Unchanged from Round 1)

```python
class MessageBus:
    """In-memory pub/sub and synchronous call infrastructure."""

    def subscribe(self, signal_type: str, callback: SignalCallback) -> str: ...
    def unsubscribe(self, subscription_id: str) -> None: ...
    async def publish(self, signal: Signal) -> None: ...
    async def sync_call(self, target_role: str, request: dict[str, Any],
                        timeout: float = 30.0) -> dict[str, Any]: ...
    async def async_notify(self, target_role: str, notification: dict[str, Any]) -> None: ...
    def register_sync_handler(self, role: str, handler: Callable) -> None: ...
    def register_notify_handler(self, role: str, handler: Callable) -> None: ...
```

### 2.3 ViewportSlicer (Unchanged from Round 1)

```python
class ViewportSlicer:
    """Context engineering: slice the kanban into role-specific views."""

    def __init__(self, kanban: StateKanban, specs: dict[str, ViewportSpec]) -> None: ...
    def slice(self, role: str) -> ViewportSlice: ...
    def estimate_tokens(self, text: str) -> int: ...


@dataclass
class ViewportSlice:
    role: str
    signals: list[Signal]
    artifacts: list[Artifact]
    token_estimate: int
    items_included: int
    items_excluded: int
    slice_log: dict[str, Any]
```

### 2.4 OutputValve (Unchanged from Round 1)

```python
class OutputValve:
    """Mandatory validation chain for all physical writes."""

    def __init__(self, validators: list[Validator] | None = None,
                 kanban: StateKanban | None = None) -> None: ...
    def set_kanban(self, kanban: StateKanban) -> None: ...
    async def validate_and_write(self, artifact: Artifact) -> ValveResult: ...
    def add_validator(self, validator: Validator, position: int = -1) -> None: ...


class Validator(ABC):
    @abstractmethod
    async def validate(self, artifact: Artifact) -> ValidationResult: ...


@dataclass
class ValidationResult:
    passed: bool
    validator_name: str
    error_detail: str = ""


@dataclass
class ValveResult:
    success: bool
    artifact_path: str | None = None
    validation_results: list[ValidationResult] = field(default_factory=list)
    error: str | None = None
```

### 2.5 ToolRegistry (Updated: adds call_codex)

```python
class ToolRegistry:
    """Permission-gated tool dispatch with audit."""

    def __init__(self, kanban: StateKanban) -> None: ...
    def register(self, tool_def: ToolDef, implementation: ToolImplementation) -> None: ...
    async def dispatch(self, tool_name: str, caller_role: str,
                       params: dict[str, Any]) -> ToolResult: ...
    def get_tool_def(self, tool_name: str) -> ToolDef | None: ...
    def list_tools(self) -> list[str]: ...


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
```

### 2.6 ProcessManager (Unchanged from Round 1)

```python
class ProcessManager:
    """Process lifecycle management."""

    def __init__(self, kanban: StateKanban, bus: MessageBus) -> None: ...
    def create_process(self, role: str, tool_permits: set[str],
                       viewport_spec: ViewportSpec) -> ProcessInfo: ...
    def activate(self, process_id: str) -> None: ...
    def suspend(self, process_id: str) -> None: ...
    def terminate(self, process_id: str, terminator: str) -> None: ...
    def claim_primary(self, role: str, new_process_id: str) -> None: ...
    def check_heartbeats(self) -> list[str]: ...
    def heartbeat(self, process_id: str) -> None: ...
    def get_process(self, process_id: str) -> ProcessInfo | None: ...
    def list_processes(self, state: ProcessState | None = None) -> list[ProcessInfo]: ...
    def get_state_for_snapshot(self) -> dict[str, Any]: ...
    def load_state_from_snapshot(self, data: dict[str, Any]) -> None: ...
```

### 2.7 LLM Adapter (Unchanged from Round 1)

```python
class LLMAdapter(ABC):
    """Abstract base for LLM backends."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse: ...


class AnthropicMessagesAdapter(LLMAdapter):
    def __init__(self, api_key: str | None = None,
                 model: str = "claude-sonnet-4-20250514") -> None: ...


class ClaudeCLIAdapter(LLMAdapter):
    def __init__(self, cli_path: str = "claude") -> None: ...


class MockLLMAdapter(LLMAdapter):
    def __init__(self, responses: dict[str, list[LLMResponse]] | None = None) -> None: ...
    def set_response(self, role: str, responses: list[LLMResponse]) -> None: ...
    def set_structured_response(self, role: str, response_type: ParsedResponseType,
                                 target_id: str = "task_root",
                                 payload: dict[str, Any] | None = None,
                                 reason: str = "",
                                 artifact_path: str = "",
                                 artifact_content: str = "") -> None: ...
```

### 2.8 NEW: CodexAdapter

```python
class CodexAdapter(LLMAdapter):
    """LLM adapter that executes via the OpenAI Codex CLI subprocess.

    Unlike other adapters, Codex is specialized for code generation:
    - Input: prompt + context_files
    - Output: code snippet (not structured JSON)
    - No tool_use support
    - No streaming
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

        Returns:
            LLMResponse with content=code_snippet, finish_reason="end_turn"

        Raises:
            CodexNotAvailableError: Codex CLI not found on PATH
            CodexExecutionError: Codex returned non-zero exit or timed out
        """
        ...

    def check_available(self) -> bool:
        """Check whether the Codex CLI is available on PATH.

        Result is cached after first check.
        """
        if self._available is None:
            self._available = shutil.which(self._cli_path) is not None
        return self._available
```

### 2.9 NEW: Engine Module

#### 2.9.1 Engine (Main Class)

```python
class Engine:
    """Top-level orchestrator that drives the development loop.

    Composes all sub-components and executes the drive loop until
    convergence or circuit break.
    """

    def __init__(
        self,
        kanban: StateKanban,
        bus: MessageBus,
        registry: ToolRegistry,
        valve: OutputValve,
        slicer: ViewportSlicer,
        pm: ProcessManager,
        adapter: LLMAdapter,
        config: Config,
    ) -> None:
        """
        Args:
            kanban: Single source of truth.
            bus: Inter-process communication.
            registry: Tool dispatch with permission.
            valve: Output validation guard.
            slicer: Viewport context engineering.
            pm: Process lifecycle management.
            adapter: LLM backend (selected via CLI --adapter).
            config: System configuration.
        """
        self._kanban = kanban
        self._bus = bus
        self._registry = registry
        self._valve = valve
        self._slicer = slicer
        self._pm = pm
        self._adapter = adapter
        self._config = config
        self._parser = ResponseParser()
        self._convergence = ConvergenceDetector(kanban)
        self._scheduler = RoleScheduler()
        self._breaker = CircuitBreaker(max_rounds=config.convergence_max_rounds)
        self._summarizer = ResultSummarizer(kanban, pm)
        self._router = SignalRouter(pm)
        self._verbose = False

    def set_verbose(self, verbose: bool) -> None:
        """Enable per-round verbose output to stderr."""

    async def drive(self, intent: str) -> EngineResult:
        """Execute the full drive loop for a given intent.

        1. Seeds the initial intent signal into FluidZone.
        2. Iterates the drive loop: role scheduling, LLM calls, parsing,
           signal injection, convergence detection.
        3. On convergence: crystal fixation + valve write.
        4. On circuit break: report failure.
        5. Returns EngineResult summary.

        Args:
            intent: The user's task intent string.

        Returns:
            EngineResult with convergence status, round count, and file list.

        Raises:
            CircuitBreakerError: Max rounds exceeded (propagated to CLI).
        """
        ...

    async def _seed_intent(self, intent: str) -> None:
        """Write the initial IntentSignal into FluidZone (round 0)."""
        ...

    async def _process_role(self, role: str, round_number: int) -> None:
        """Process a single role within the drive loop.

        Steps:
        1. Read viewport slice for the role.
        2. Call LLM (or Codex) via ToolRegistry.
        3. Parse response into ParsedResponse objects.
        4. Inject parsed signals into FluidZone.

        Args:
            role: The role to process.
            round_number: Current round number (1-based).
        """
        ...

    async def _call_llm_for_role(self, role: str, slice: ViewportSlice) -> LLMResponse:
        """Invoke LLM for a role with the given viewport slice.

        Uses call_llm tool via ToolRegistry to maintain permission and audit.

        Args:
            role: The requesting role.
            slice: The viewport slice as context.

        Returns:
            Raw LLMResponse.
        """
        ...

    def _inject_parsed(self, parsed: ParsedResponse, round_number: int) -> None:
        """Inject a parsed response into FluidZone as a typed Signal.

        - ParsedResponseType.INTENT -> IntentSignal
        - ParsedResponseType.VETO -> VetoSignal
        - ParsedResponseType.ARTIFACT -> IntentSignal (artifact approval pending)
        - ParsedResponseType.ERROR -> ErrorSignal

        Args:
            parsed: The parsed response to inject.
            round_number: Current round number.
        """
        ...

    def _crystalize_and_write(self) -> None:
        """After convergence: fixate artifact into CrystalZone and submit to OutputValve.

        Steps:
        1. Extract the artifact content from the converged intent signal payload.
        2. Create an Artifact instance.
        3. Append to CrystalZone.
        4. Submit to OutputValve.validate_and_write().
        5. If valve fails, inject ErrorSignal into FluidZone.
        """
        ...
```

#### 2.9.2 ResponseParser

```python
class ResponseParser:
    """Parses raw LLM responses into typed ParsedResponse objects.

    Handles three input formats:
    1. Structured JSON: {"type": "intent"|"veto"|"artifact", ...}
    2. Fenced code block: ```python ... ```
    3. Unstructured text: treated as error
    """

    def parse(
        self,
        raw_response: LLMResponse,
        author_role: str,
        round_number: int,
    ) -> list[ParsedResponse]:
        """Parse a raw LLM response into typed signals.

        Args:
            raw_response: The raw LLM response.
            author_role: Role that produced this response.
            round_number: Current round number.

        Returns:
            List of ParsedResponse objects. On complete parse failure,
            returns a single ERROR-typed ParsedResponse.
        """
        ...

    def _try_structured_json(
        self, content: str, author_role: str, round_number: int
    ) -> list[ParsedResponse] | None:
        """Attempt to parse content as structured JSON.

        Returns None if content is not valid JSON or does not match
        the expected schema.
        """
        ...

    def _try_code_block(
        self, content: str, author_role: str, round_number: int
    ) -> list[ParsedResponse] | None:
        """Attempt to extract code from fenced code blocks.

        Returns None if no fenced code blocks found.
        """
        ...

    def _make_error_response(
        self, content: str, author_role: str, round_number: int, error_msg: str
    ) -> ParsedResponse:
        """Create an ERROR-typed ParsedResponse for parse failures."""
        ...
```

#### 2.9.3 ConvergenceDetector

```python
class ConvergenceDetector:
    """Determines whether signals for a target have converged."""

    def __init__(self, kanban: StateKanban) -> None:
        self._kanban = kanban

    def check(self, target_id: str, current_round: int) -> ConvergenceCheckResult:
        """Check convergence for a target at the given round.

        A target is converged when:
        - There exists at least one IntentSignal for this target in current_round
        - There are zero VetoSignal entries for this target in current_round

        Args:
            target_id: The target to check.
            current_round: The current round number.

        Returns:
            ConvergenceCheckResult with convergence status and signal counts.
        """
        ...

    def check_all_pending(self, current_round: int) -> dict[str, ConvergenceCheckResult]:
        """Check convergence for all targets that have signals in the current round.

        Returns:
            Dict mapping target_id to ConvergenceCheckResult.
        """
        ...
```

#### 2.9.4 RoleScheduler

```python
class RoleScheduler:
    """Defines and iterates the role processing order within a drive round."""

    DEFAULT_ORDER: list[str] = ["coder", "reviewer", "tester", "integrator"]

    def __init__(self, order: list[str] | None = None) -> None:
        """
        Args:
            order: Custom role order. Defaults to DEFAULT_ORDER.
        """
        self._order = order or list(self.DEFAULT_ORDER)

    @property
    def order(self) -> list[str]:
        """Return a copy of the current role order."""
        return list(self._order)

    def iter_round(self) -> Iterator[str]:
        """Yield role names in scheduling order for one round."""
        ...
```

#### 2.9.5 CircuitBreaker

```python
class CircuitBreaker:
    """Prevents infinite drive loops by enforcing a maximum round count."""

    def __init__(self, max_rounds: int = 10) -> None:
        """
        Args:
            max_rounds: Maximum number of rounds before circuit break.
        """
        self._max_rounds = max_rounds

    def should_break(self, current_round: int) -> bool:
        """Check if the drive loop should terminate.

        Returns:
            True if current_round >= max_rounds.
        """
        return current_round >= self._max_rounds

    def report(self, current_round: int) -> EngineResult:
        """Generate an EngineResult for circuit break termination.

        Args:
            current_round: The round at which the break occurred.

        Returns:
            EngineResult with converged=False, forced_terminate=True.
        """
        ...

    @property
    def max_rounds(self) -> int:
        return self._max_rounds
```

#### 2.9.6 ResultSummarizer

```python
class ResultSummarizer:
    """Produces end-of-loop EngineResult summaries."""

    def __init__(self, kanban: StateKanban, pm: ProcessManager) -> None:
        self._kanban = kanban
        self._pm = pm

    def summarize(
        self,
        total_rounds: int,
        converged: bool,
        forced_terminate: bool = False,
        start_time: datetime.datetime | None = None,
    ) -> EngineResult:
        """Generate a summary of the drive loop execution.

        Args:
            total_rounds: Number of rounds completed.
            converged: Whether convergence was achieved.
            forced_terminate: Whether circuit breaker fired.
            start_time: When the drive loop started (for duration calc).

        Returns:
            EngineResult with signal counts, artifact files, and timing.
        """
        ...
```

#### 2.9.7 SignalRouter

```python
class SignalRouter:
    """Routes signals to the appropriate processing role."""

    def __init__(self, pm: ProcessManager) -> None:
        self._pm = pm

    def route(self, signal: Signal) -> str | None:
        """Determine which role should process a signal.

        Routing rules:
        - IntentSignal from "user" -> "coder"
        - IntentSignal from "coder" -> "reviewer"
        - VetoSignal from "reviewer" -> "coder" (rework)
        - ErrorSignal from "OutputValve" -> "coder" (rework)
        - ErrorSignal from "ResponseParser" -> "coder" (retry)
        - Other -> None (no specific route; picked up by scheduler)

        Args:
            signal: The signal to route.

        Returns:
            Role name that should process this signal, or None.
        """
        ...

    def get_pending_targets(self) -> list[str]:
        """Get all target_ids that have unprocessed signals.

        Returns:
            List of target_ids with pending signals.
        """
        ...
```

### 2.10 Snapshot (Unchanged from Round 1)

```python
def save_snapshot(kanban: StateKanban, path: str) -> None: ...
def load_snapshot(path: str) -> StateKanban: ...
```

### 2.11 NEW: call_codex Tool

```python
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

    Raises (via ToolRegistry.dispatch):
        PermissionDeniedError: if caller_role not in {"coder", "integrator"}
        CodexNotAvailableError: if Codex CLI not found
        CodexExecutionError: if Codex subprocess fails
    """
    ...
```

### 2.12 CLI (Updated)

```python
@click.group()
def cli() -> None:
    """StateKanban -- Instruction-level development engine."""
    pass


@cli.command()
@click.option("--intent", required=True, help="Task intent description")
@click.option("--config", "config_path", default=None, help="Path to config file")
@click.option("--adapter", type=click.Choice(["mock", "anthropic", "cli", "codex"]),
              default="mock", help="LLM adapter to use")
@click.option("--max-rounds", default=10, type=int, help="Maximum drive loop rounds")
@click.option("--verbose", is_flag=True, help="Output per-round details")
def run(intent: str, config_path: str | None, adapter: str,
        max_rounds: int, verbose: bool) -> None:
    """Start a development task with the drive loop."""
    ...


@cli.command()
def status() -> None: ...


@cli.command()
@click.option("--output", default="snapshot.json", help="Output file path")
def snapshot(output: str) -> None: ...


@cli.command()
@click.option("--file", "snapshot_file", required=True, help="Snapshot file to restore from")
def restore(snapshot_file: str) -> None: ...
```

## 3. Error Code Definitions (Updated)

### 3.1 Error Code Format

Format: `SK_<MODULE>_<CODE>`

| Module | Prefix |
|--------|--------|
| FluidZone | `SK_FZ_` |
| CrystalZone | `SK_CZ_` |
| AuditZone | `SK_AZ_` |
| ViewportSlicer | `SK_VS_` |
| OutputValve | `SK_OV_` |
| ToolRegistry | `SK_TR_` |
| ProcessManager | `SK_PM_` |
| MessageBus | `SK_MB_` |
| LLMAdapter | `SK_LLM_` |
| Snapshot | `SK_SN_` |
| Engine (NEW) | `SK_EN_` |
| CodexAdapter (NEW) | `SK_CX_` |

### 3.2 Error Code Table

| Code | HTTP Analogy | Description | Recovery |
|------|-------------|-------------|----------|
| `SK_FZ_001` | 400 | Invalid signal schema | Fix signal structure and retry |
| `SK_FZ_002` | 409 | Signal collision detected | Run convergence |
| `SK_FZ_003` | 408 | Convergence timeout (>10 rounds) | Manual intervention |
| `SK_CZ_001` | 409 | Duplicate sequence number | Auto-assign seq_no |
| `SK_CZ_002` | 405 | Append-only violation (modify/delete) | Not possible via API |
| `SK_AZ_001` | 500 | Audit write failure | Log to stderr, continue |
| `SK_VS_001` | 400 | Invalid viewport spec | Fix spec configuration |
| `SK_VS_002` | 413 | Slice exceeds token budget even after truncation | Increase budget or reduce scope |
| `SK_OV_001` | 422 | Syntax check failed | Rework artifact |
| `SK_OV_002` | 422 | Type check failed | Rework artifact |
| `SK_OV_003` | 422 | Test execution failed | Rework artifact |
| `SK_OV_004` | 500 | Atomic write failed (disk/permission) | Check filesystem, retry |
| `SK_OV_005` | 403 | Human gate rejected | Revise and resubmit |
| `SK_TR_001` | 403 | Permission denied | Use permitted tool or request access |
| `SK_TR_002` | 404 | Tool not found | Register tool before use |
| `SK_TR_003` | 408 | Tool execution timeout | Retry or adjust timeout |
| `SK_PM_001` | 409 | Invalid state transition | Check current state |
| `SK_PM_002` | 403 | Self-termination attempted | Request scheduler to terminate |
| `SK_PM_003` | 408 | Heartbeat timeout | Auto-recovery from snapshot |
| `SK_PM_004` | 409 | Handoff failed | Verify predecessor exists |
| `SK_MB_001` | 400 | Invalid subscription | Fix signal type or callback |
| `SK_MB_002` | 408 | Sync call timeout | Increase timeout or check callee |
| `SK_LLM_001` | 429 | Rate limit hit | Exponential backoff retry |
| `SK_LLM_002` | 401 | Authentication failure | Fix API key |
| `SK_LLM_003` | 500 | Response parse error | Retry with different parameters |
| `SK_SN_001` | 422 | Snapshot integrity check failed | Use earlier snapshot |
| `SK_SN_002` | 500 | Snapshot write failed | Check disk space/permissions |
| `SK_EN_001` (NEW) | 408 | Circuit breaker fired (max rounds exceeded) | Manual intervention |
| `SK_EN_002` (NEW) | 400 | Signal routing error (no matching role) | Next round retry |
| `SK_EN_003` (NEW) | 500 | Parse recovery failed (consecutive parse errors) | Circuit break |
| `SK_EN_004` (NEW) | 500 | Valve rework loop (valve keeps failing) | Circuit break |
| `SK_CX_001` (NEW) | 503 | Codex CLI not available on PATH | Graceful degradation to call_llm |
| `SK_CX_002` (NEW) | 500 | Codex execution error (non-zero exit) | Retry or fallback to call_llm |
| `SK_CX_003` (NEW) | 408 | Codex execution timeout | Retry with adjusted timeout |

## 4. Inter-Module Interface Specifications (Updated)

### 4.1 Updated Dependency Graph

```
CLI
  --> Engine (NEW)
        --> ProcessManager
              --> StateKanban
              --> MessageBus
                    --> StateKanban (audit)
        --> StateKanban (read/write signals)
        --> ViewportSlicer --> StateKanban
        --> ToolRegistry
              --> StateKanban (audit)
              --> OutputValve (for write_file)
                    --> StateKanban (error signal injection)
              --> CodexAdapter (for call_codex) (NEW)
        --> ResponseParser (NEW)
              --> StateKanban (error signal injection on parse failure)
        --> ConvergenceDetector (NEW) --> StateKanban
        --> RoleScheduler (NEW)
        --> CircuitBreaker (NEW)
        --> ResultSummarizer (NEW) --> StateKanban + ProcessManager
        --> SignalRouter (NEW) --> ProcessManager
  --> StateKanban (snapshot/restore)

ProcessRole (Coder, Reviewer, etc.)
  --> ViewportSlicer --> StateKanban
  --> MessageBus
  --> ToolRegistry
        --> StateKanban (audit)
        --> OutputValve (for write_file)
              --> StateKanban (error signal injection)
        --> CodexAdapter (for call_codex) (NEW)

StateKanban
  --> (no external dependencies -- pure data structure)

LLMAdapter / CodexAdapter
  --> (no internal dependencies -- wraps external SDK/CLI)

MessageBus
  --> StateKanban (audit only)
```

### 4.2 Interface Contracts

All Round 1 interface contracts are preserved. New contracts follow.

#### Engine <-> StateKanban

- **Inbound**: Engine calls `kanban.fluid.write_signal()` (seed intent, inject parsed signals, inject error signals)
- **Outbound**: Engine calls `kanban.fluid.read_signals()`, `kanban.fluid.detect_collision()`, `kanban.crystal.append()`
- **Contract**: Engine is the primary writer to FluidZone during the drive loop. Processes write signals only through their role's execute method, which the Engine calls.

#### Engine <-> ViewportSlicer

- **Inbound**: Engine calls `slicer.slice(role)` before each LLM call
- **Outbound**: None (Engine only reads slices)
- **Contract**: Engine never bypasses the slicer to read StateKanban directly for LLM context

#### Engine <-> ToolRegistry

- **Inbound**: Engine calls `registry.dispatch("call_llm", role, params)` to invoke LLM
- **Outbound**: ToolRegistry returns ToolResult
- **Contract**: Engine uses call_llm tool for LLM invocation, not the adapter directly. This preserves permission checks and audit trails.

#### Engine <-> ResponseParser

- **Inbound**: Engine calls `parser.parse(raw_response, role, round_number)`
- **Outbound**: ResponseParser returns `list[ParsedResponse]`; on parse failure, ResponseParser injects ErrorSignal into FluidZone
- **Contract**: ResponseParser is allowed to write ErrorSignals directly to FluidZone; it does not propagate parse errors as exceptions

#### Engine <-> ConvergenceDetector

- **Inbound**: Engine calls `detector.check(target_id, round_number)` and `detector.check_all_pending(round_number)`
- **Outbound**: ConvergenceDetector returns ConvergenceCheckResult
- **Contract**: ConvergenceDetector only reads from FluidZone; it never writes signals

#### Engine <-> CircuitBreaker

- **Inbound**: Engine calls `breaker.should_break(round_number)`
- **Outbound**: CircuitBreaker returns bool
- **Contract**: CircuitBreaker is stateless; it just compares the round number to the configured max

#### Engine <-> RoleScheduler

- **Inbound**: Engine calls `scheduler.iter_round()`
- **Outbound**: RoleScheduler yields role names
- **Contract**: RoleScheduler is stateless; it just iterates the configured order

#### Engine <-> ResultSummarizer

- **Inbound**: Engine calls `summarizer.summarize(rounds, converged, forced_terminate, start_time)`
- **Outbound**: ResultSummarizer returns EngineResult
- **Contract**: ResultSummarizer reads from StateKanban and ProcessManager to build summary

#### Engine <-> SignalRouter

- **Inbound**: Engine calls `router.route(signal)`
- **Outbound**: SignalRouter returns role name or None
- **Contract**: SignalRouter reads from ProcessManager to resolve role mappings; it never writes signals

#### ToolRegistry <-> CodexAdapter (call_codex)

- **Inbound**: When `call_codex` tool is dispatched, ToolRegistry invokes `codex_adapter.complete()`
- **Outbound**: LLMResponse is wrapped in a ToolResult
- **Contract**: CodexAdapter follows the same LLMAdapter ABC; no session state between calls

#### CodexAdapter <-> Infrastructure

- **Inbound**: CodexAdapter spawns `codex` CLI subprocess via `asyncio.create_subprocess_exec`
- **Outbound**: stdout captured as code snippet; exit code checked
- **Contract**: CodexAdapter is the only module that interacts with the Codex CLI. No other module spawns the `codex` process.

### 4.3 Updated Initialization Order

1. `StateKanban()` -- no dependencies
2. `MessageBus(kanban)` -- depends on StateKanban (audit)
3. `ToolRegistry(kanban)` -- depends on StateKanban (audit)
4. `OutputValve(validators, kanban=kanban)` -- depends on StateKanban (error injection)
5. `ViewportSlicer(kanban, specs)` -- depends on StateKanban (read)
6. `ProcessManager(kanban, bus)` -- depends on StateKanban + MessageBus
7. `LLMAdapter` (selected via --adapter) -- no internal dependencies
8. `CodexAdapter` (if selected) -- no internal dependencies
9. **Engine sub-components (NEW):**
   - `ResponseParser()` -- no dependencies
   - `ConvergenceDetector(kanban)` -- depends on StateKanban
   - `RoleScheduler()` -- no dependencies
   - `CircuitBreaker(max_rounds)` -- depends on Config
   - `ResultSummarizer(kanban, pm)` -- depends on StateKanban + ProcessManager
   - `SignalRouter(pm)` -- depends on ProcessManager
10. `Engine(...)` -- depends on all above
11. Register tools (including call_codex if CodexAdapter is selected)
12. Create and activate process roles

### 4.4 Updated Async Boundary

| Module | Async Required | Reason |
|--------|---------------|--------|
| StateKanban | No | Pure data structure, no I/O |
| MessageBus | Yes | Callback dispatch, sync_call futures |
| ViewportSlicer | No | Pure computation on in-memory data |
| OutputValve | Yes | File I/O (atomic write) and subprocess (test execution) |
| ToolRegistry | Yes | Delegates to tool implementations (may be async) |
| ProcessManager | No | State machine operations are synchronous |
| LLMAdapter | Yes | Network I/O to API |
| CodexAdapter | Yes | Subprocess I/O to Codex CLI |
| **Engine** (NEW) | **Yes** | Drives async LLM calls, orchestrates async sub-components |
| ResponseParser | No | Pure computation on strings |
| ConvergenceDetector | No | Reads in-memory data |
| RoleScheduler | No | Stateless iteration |
| CircuitBreaker | No | Stateless comparison |
| ResultSummarizer | No | Reads in-memory data |
| SignalRouter | No | Reads in-memory data |
| CLI | Yes | Drives async Engine |

### 4.5 Updated Event Flow Sequence (Engine-Driven Task)

```
1. CLI parses options (--intent, --adapter, --max-rounds, --verbose)
2. CLI bootstraps system: StateKanban, MessageBus, ToolRegistry, OutputValve, ViewportSlicer, ProcessManager
3. CLI creates LLM/Codex adapter based on --adapter
4. CLI creates Engine sub-components: ResponseParser, ConvergenceDetector, RoleScheduler, CircuitBreaker, ResultSummarizer, SignalRouter
5. CLI creates Engine with all components
6. CLI creates and activates processes: Coder, Reviewer, Tester, Integrator
7. CLI registers tools in ToolRegistry (including call_codex if --adapter codex)
8. CLI calls Engine.drive(intent)
   a. Engine._seed_intent(intent) -> IntentSignal(round=0) -> FluidZone
   b. Loop:
      i.   For each role in RoleScheduler.order:
           - Read pending signals for this role
           - ViewportSlicer.slice(role) -> ViewportSlice
           - ToolRegistry.dispatch("call_llm", role, {messages, ...}) -> LLMResponse
           - ResponseParser.parse(response, role, round) -> list[ParsedResponse]
           - For each ParsedResponse: inject typed Signal into FluidZone
      ii.  ConvergenceDetector.check_all_pending(round)
           - If all targets converged: break loop
      iii. CircuitBreaker.should_break(round)
           - If true: break loop, return forced_terminate=True
   c. If converged: Engine._crystalize_and_write()
      - CrystalZone.append(artifact)
      - OutputValve.validate_and_write(artifact)
      - If valve fails: ErrorSignal -> FluidZone, continue loop
   d. ResultSummarizer.summarize(rounds, converged, ...)
9. CLI outputs EngineResult summary
10. If --verbose: per-round details were printed to stderr during loop
```