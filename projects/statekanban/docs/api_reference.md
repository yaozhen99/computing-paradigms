# StateKanban API Reference

Complete API reference for all public modules, generated from source code and the API contracts specification.

---

## 1. Core Data Structures

### 1.1 Signal Types

```python
from statekanban.core.kanban import SignalType, Signal, IntentSignal, VetoSignal, ErrorSignal
```

#### SignalType (Enum)

| Value | Description |
|-------|-------------|
| `INTENT` | Positive assertion from a role (e.g. "code is ready for review") |
| `VETO` | Rejection with mandatory reason |
| `ERROR` | Error feedback from OutputValve or ToolRegistry |

#### Signal (frozen dataclass)

Base signal stored in FluidZone.

| Field | Type | Description |
|-------|------|-------------|
| `signal_id` | `str` | UUID4 identifier |
| `signal_type` | `SignalType` | One of INTENT / VETO / ERROR |
| `author_role` | `str` | Role that produced the signal (e.g. "coder") |
| `target_id` | `str` | Artifact or decision target |
| `payload` | `dict[str, Any]` | Role-specific data |
| `timestamp` | `datetime.datetime` | UTC timestamp, monotonic within session |
| `round_number` | `int` | Convergence round (0 = initial) |

**Methods:**

- `to_dict() -> dict[str, Any]` -- Serialize to a JSON-serializable dict.
- `Signal.from_dict(data) -> Signal` -- Reconstruct from dict.

#### IntentSignal(Signal)

`signal_type` is always `SignalType.INTENT`. No additional fields.

#### VetoSignal(Signal)

| Additional Field | Type | Default | Description |
|------------------|------|---------|-------------|
| `reason` | `str` | `""` | Mandatory rejection reason |

**Example -- creating a VetoSignal:**

```python
from statekanban.core.kanban import VetoSignal, make_signal_id, now_utc

veto = VetoSignal(
    signal_id=make_signal_id(),
    author_role="reviewer",
    target_id="auth_module",
    payload={"concern": "missing input validation"},
    timestamp=now_utc(),
    round_number=1,
    reason="Input validation missing on login endpoint",
)
print(veto.to_dict())
# {
#   "signal_id": "a1b2c3...",
#   "signal_type": "veto",
#   "author_role": "reviewer",
#   "target_id": "auth_module",
#   "payload": {"concern": "missing input validation"},
#   "timestamp": "2026-05-05T12:00:00+00:00",
#   "round_number": 1,
#   "reason": "Input validation missing on login endpoint"
# }
```

#### ErrorSignal(Signal)

| Additional Field | Type | Default | Description |
|------------------|------|---------|-------------|
| `error_code` | `str` | `""` | Machine-readable error code (e.g. "SK_OV_001") |
| `error_detail` | `str` | `""` | Human-readable error description |

---

### 1.2 Artifact Types

```python
from statekanban.core.kanban import ArtifactType, Artifact
```

#### ArtifactType (Enum)

| Value | Description |
|-------|-------------|
| `CODE` | Source code artifact |
| `CONFIG` | Configuration file |
| `DOC` | Documentation |
| `TEST` | Test file |

#### Artifact (frozen dataclass)

Immutable artifact stored in CrystalZone (append-only).

| Field | Type | Description |
|-------|------|-------------|
| `seq_no` | `int` | Monotonically increasing sequence number (0 = auto-assign) |
| `artifact_type` | `ArtifactType` | CODE / CONFIG / DOC / TEST |
| `path` | `str` | Target filesystem path |
| `content` | `str` | File content |
| `checksum` | `str` | SHA-256 of content |
| `author_role` | `str` | Role that created the artifact |
| `created_at` | `datetime.datetime` | Creation timestamp |
| `metadata` | `dict[str, Any]` | Optional metadata |

**Methods:**

- `to_dict() -> dict[str, Any]`
- `Artifact.from_dict(data) -> Artifact`

---

### 1.3 AuditEntry

```python
from statekanban.core.kanban import AuditEntry
```

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | `int` | Monotonically increasing entry ID |
| `event_type` | `str` | "tool_call", "signal_write", "state_transition", etc. |
| `actor` | `str` | Role or module name |
| `action` | `str` | Verb describing the action |
| `details` | `dict[str, Any]` | Event-specific data (content hashed for sensitive ops) |
| `timestamp` | `datetime.datetime` | UTC timestamp |

---

### 1.4 ViewportSpec

```python
from statekanban.core.kanban import ViewportSpec
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `role` | `str` | -- | Role name this spec applies to |
| `visible_signal_types` | `list[SignalType]` | -- | Signal types this role can see |
| `visible_artifact_types` | `list[ArtifactType]` | -- | Artifact types this role can see |
| `visible_target_patterns` | `list[str]` | -- | Glob-like patterns for target_id filtering |
| `max_tokens` | `int` | `2000` | Token budget per slice |
| `priority_order` | `list[str]` | `["role_relevant", "dependency_upstream", "global_summary"]` | Ordering priority |

**Example:**

```python
from statekanban.core.kanban import ViewportSpec, SignalType, ArtifactType

coder_spec = ViewportSpec(
    role="coder",
    visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
    visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG],
    visible_target_patterns=["*"],
    max_tokens=2000,
)
```

---

### 1.5 ProcessInfo

```python
from statekanban.core.kanban import ProcessInfo, ProcessState
```

#### ProcessState (Enum)

| Value | Description |
|-------|-------------|
| `CREATED` | Process initialized, not yet active |
| `ACTIVE` | Process running, heartbeat active |
| `SUSPENDED` | Process paused (e.g. waiting on convergence) |
| `TERMINATED` | Process stopped (terminal state) |

#### ProcessInfo (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `process_id` | `str` | UUID4 |
| `role` | `str` | Role name |
| `state` | `ProcessState` | Current state |
| `tool_permits` | `set[str]` | Allowed tool names |
| `viewport_spec` | `ViewportSpec` | Viewport configuration |
| `heartbeat_at` | `datetime.datetime | None` | Last heartbeat timestamp |
| `last_signal_id` | `str | None` | ID of last signal processed |

---

### 1.6 ToolDef

```python
from statekanban.core.kanban import ToolDef
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | -- | Tool name (e.g. "write_file") |
| `description` | `str` | -- | Human-readable description |
| `param_schema` | `dict[str, Any]` | -- | JSON Schema for parameters |
| `required_permissions` | `set[str]` | -- | Roles that may call this tool (use "all_roles" for universal) |
| `timeout_seconds` | `float` | `60.0` | Execution timeout |
| `max_retries` | `int` | `0` | Maximum retry attempts |

---

### 1.7 LLM Types

```python
from statekanban.core.kanban import LLMMessage, LLMResponse
```

#### LLMMessage

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `role` | `str` | -- | "user", "assistant", "tool_result" |
| `content` | `str | None` | `None` | Text content |
| `tool_use` | `dict[str, Any] | None` | `None` | Tool use request |
| `tool_result` | `dict[str, Any] | None` | `None` | Tool execution result |

#### LLMResponse

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `content` | `str | None` | `None` | Text content |
| `tool_use_calls` | `list[dict[str, Any]]` | `[]` | Tool use calls from the model |
| `finish_reason` | `str` | `""` | "end_turn", "tool_use", "max_tokens" |
| `usage` | `dict[str, int]` | `{}` | Token usage (input_tokens, output_tokens) |
| `raw` | `dict[str, Any]` | `{}` | Original API response |

---

## 2. Module APIs

### 2.1 StateKanban (FluidZone / CrystalZone / AuditZone)

```python
from statekanban.core.kanban import FluidZone, CrystalZone, AuditZone, StateKanban
```

#### FluidZone

Mutable signal area with collision detection.

| Method | Signature | Description |
|--------|-----------|-------------|
| `write_signal` | `(signal: Signal) -> None` | Write a signal. Raises `InvalidSignalError` on validation failure. |
| `read_signals` | `(target_id=None, signal_type=None, author_role=None) -> list[Signal]` | Read signals matching filters, ordered by timestamp ascending. |
| `detect_collision` | `(target_id: str) -> CollisionResult` | Check for conflicting INTENT/VETO signals. |
| `clear_signals` | `(target_id: str, round_number_ge: int) -> None` | Remove signals for a target at or above a round number. |

**CollisionResult:**

| Field | Type | Description |
|-------|------|-------------|
| `has_collision` | `bool` | Whether INTENT and VETO signals coexist |
| `signals` | `list[Signal]` | All signals for the target |
| `is_resolved` | `bool` | True if no conflict or all signals agree |

**Example:**

```python
from statekanban.core.kanban import FluidZone, IntentSignal, VetoSignal, make_signal_id, now_utc

fluid = FluidZone()

# Write an intent signal
intent = IntentSignal(
    signal_id=make_signal_id(),
    author_role="coder",
    target_id="auth_module",
    payload={"status": "ready"},
    timestamp=now_utc(),
    round_number=0,
)
fluid.write_signal(intent)

# Write a veto signal
veto = VetoSignal(
    signal_id=make_signal_id(),
    author_role="reviewer",
    target_id="auth_module",
    payload={"concern": "security"},
    timestamp=now_utc(),
    round_number=0,
    reason="Missing input validation",
)
fluid.write_signal(veto)

# Detect collision
result = fluid.detect_collision("auth_module")
print(result.has_collision)  # True
print(result.is_resolved)    # False
```

#### CrystalZone

Append-only artifact store. No update or delete operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `append` | `(artifact: Artifact) -> int` | Append artifact. Returns assigned seq_no. Raises `ArtifactConflictError` or `AppendOnlyViolationError`. |
| `read_artifact` | `(seq_no: int) -> Artifact | None` | Read a single artifact by sequence number. |
| `read_artifacts` | `(artifact_type=None, author_role=None) -> list[Artifact]` | Read artifacts matching filters. |
| `latest_seq_no` | `() -> int` | Return the highest sequence number (0 if empty). |

**Example:**

```python
from statekanban.core.kanban import CrystalZone, Artifact, ArtifactType, compute_checksum, now_utc

crystal = CrystalZone()

artifact = Artifact(
    seq_no=0,  # auto-assigned
    artifact_type=ArtifactType.CODE,
    path="src/auth.py",
    content="def login(): pass",
    checksum=compute_checksum("def login(): pass"),
    author_role="coder",
    created_at=now_utc(),
)

seq_no = crystal.append(artifact)
print(seq_no)  # 1
print(crystal.latest_seq_no())  # 1
```

#### AuditZone

Append-only audit log.

| Method | Signature | Description |
|--------|-----------|-------------|
| `log` | `(event_type, actor, action, details) -> int` | Append entry. Returns assigned entry_id. |
| `read_entries` | `(event_type=None, actor=None, since_entry_id=0) -> list[AuditEntry]` | Read entries matching filters. |

#### StateKanban (Facade)

| Method | Signature | Description |
|--------|-----------|-------------|
| `register_viewport` | `(spec: ViewportSpec) -> None` | Register a viewport spec for a role. |
| `get_viewport_spec` | `(role: str) -> ViewportSpec | None` | Get viewport spec for a role. |
| `to_json` | `() -> dict[str, Any]` | Serialize entire kanban with SHA-256 checksum. |
| `StateKanban.from_json` | `(data: dict[str, Any]) -> StateKanban` | Reconstruct from dict. Raises `SnapshotIntegrityError`. |
| `run_convergence` | `(target_id: str) -> ConvergenceResult` | Execute convergence loop for a target. |

**ConvergenceResult:**

| Field | Type | Description |
|-------|------|-------------|
| `target_id` | `str` | Target identifier |
| `rounds` | `int` | Number of convergence rounds executed |
| `converged` | `bool` | Whether agreement was reached |
| `final_signals` | `list[Signal]` | Final signal state |
| `forced_terminate` | `bool` | True if max rounds (10) exceeded |

---

### 2.2 MessageBus

```python
from statekanban.core.message_bus import MessageBus
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `subscribe` | `(signal_type: str, callback: Callable) -> str` | Subscribe to a signal type. Returns subscription_id. Raises `SubscriptionError`. |
| `unsubscribe` | `(subscription_id: str) -> None` | Remove a subscription. Raises `SubscriptionError`. |
| `publish` | `async (signal: Signal) -> None` | Publish a signal to all matching subscribers (async dispatch). |
| `sync_call` | `async (target_role, request, timeout=30.0) -> dict` | Synchronously call a role. Raises `SyncCallTimeoutError`. |
| `async_notify` | `async (target_role, notification) -> None` | Fire-and-forget notification (best-effort). |
| `register_sync_handler` | `(role, handler) -> None` | Register a sync call handler for a role. |
| `register_notify_handler` | `(role, handler) -> None` | Register a notification handler for a role. |

**Example:**

```python
from statekanban.core.kanban import StateKanban, IntentSignal, make_signal_id, now_utc
from statekanban.core.message_bus import MessageBus

kanban = StateKanban()
bus = MessageBus(kanban)

# Subscribe to intent signals
async def on_intent(signal):
    print(f"Intent received: {signal.target_id}")

sub_id = bus.subscribe("intent", on_intent)

# Publish a signal
signal = IntentSignal(
    signal_id=make_signal_id(),
    author_role="coder",
    target_id="feature_x",
    payload={},
    timestamp=now_utc(),
    round_number=0,
)
await bus.publish(signal)

# Unsubscribe
bus.unsubscribe(sub_id)
```

---

### 2.3 ViewportSlicer

```python
from statekanban.core.viewport import ViewportSlicer, ViewportSlice
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `slice` | `(role: str) -> ViewportSlice` | Generate a viewport slice for a role. Raises `InvalidViewportSpecError` if no spec registered. |
| `estimate_tokens` | `(text: str) -> int` | Estimate token count (heuristic: 4 chars/token). |

**ViewportSlice:**

| Field | Type | Description |
|-------|------|-------------|
| `role` | `str` | Role name |
| `signals` | `list[Signal]` | Filtered signals |
| `artifacts` | `list[Artifact]` | Filtered artifacts |
| `token_estimate` | `int` | Estimated tokens in the slice |
| `items_included` | `int` | Number of items included within budget |
| `items_excluded` | `int` | Number of items dropped due to budget |
| `slice_log` | `dict[str, Any]` | Slice metadata for logging |

---

### 2.4 OutputValve

```python
from statekanban.core.valve import OutputValve, ValveResult, ValidationResult, Validator
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `validate_and_write` | `async (artifact: Artifact) -> ValveResult` | Run validation chain; atomic write on success; error signal injection on failure. |
| `add_validator` | `(validator: Validator, position: int = -1) -> None` | Insert a validator into the chain. |

**Built-in Validators:**

| Validator | Description |
|-----------|-------------|
| `SyntaxValidator` | AST parse for Python (.py), JSON parse for configs (.json) |
| `TypeValidator` | Stub -- always passes (extensible) |
| `TestValidator` | Stub for pytest execution (extensible) |

**ValveResult:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether all validations passed and write succeeded |
| `artifact_path` | `str | None` | Written file path (None on failure) |
| `validation_results` | `list[ValidationResult]` | Results from each validator |
| `error` | `str | None` | Error message on failure |

**Example:**

```python
from statekanban.core.kanban import StateKanban, Artifact, ArtifactType, compute_checksum, now_utc
from statekanban.core.valve import OutputValve

kanban = StateKanban()
valve = OutputValve(kanban=kanban)

artifact = Artifact(
    seq_no=0,
    artifact_type=ArtifactType.CODE,
    path="/tmp/test_module.py",
    content="def hello():\n    return 'world'\n",
    checksum=compute_checksum("def hello():\n    return 'world'\n"),
    author_role="coder",
    created_at=now_utc(),
)

result = await valve.validate_and_write(artifact)
print(result.success)       # True
print(result.artifact_path)  # "/tmp/test_module.py"
```

---

### 2.5 ToolRegistry

```python
from statekanban.core.registry import ToolRegistry, ToolResult
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(tool_def: ToolDef, implementation: Callable) -> None` | Register a tool. Raises `ToolNotFoundError` on duplicate. |
| `dispatch` | `async (tool_name, caller_role, params) -> ToolResult` | Dispatch a tool call. Raises `PermissionDeniedError`, `ToolNotFoundError`, `ToolTimeoutError`. |
| `get_tool_def` | `(tool_name: str) -> ToolDef | None` | Get tool definition. |
| `list_tools` | `() -> list[str]` | List registered tool names. |

**ToolResult:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether the tool call succeeded |
| `output` | `Any` | Tool output (None on failure) |
| `error` | `str | None` | Error message on failure |
| `duration_ms` | `float` | Execution duration in milliseconds |

**Built-in tools and their permissions:**

| Tool | Allowed Roles | Description |
|------|---------------|-------------|
| `write_file` | coder, integrator | Write artifact via OutputValve |
| `read_file` | all_roles | Read file contents |
| `run_shell` | integrator, tester | Execute shell command |
| `call_llm` | all_roles | Invoke LLM via adapter |
| `search_code` | all_roles | Search codebase for patterns |

**Example:**

```python
from statekanban.core.kanban import StateKanban, ToolDef
from statekanban.core.registry import ToolRegistry

kanban = StateKanban()
registry = ToolRegistry(kanban)

# Register a tool
async def my_tool(params):
    return {"result": "ok"}

registry.register(
    ToolDef(
        name="my_tool",
        description="Custom tool",
        param_schema={"type": "object", "properties": {}},
        required_permissions={"coder"},
    ),
    my_tool,
)

# Dispatch
result = await registry.dispatch("my_tool", "coder", {})
print(result.success)  # True

# Permission denied
try:
    await registry.dispatch("my_tool", "reviewer", {})
except PermissionDeniedError as e:
    print(e.error_code)  # SK_TR_001
```

---

### 2.6 ProcessManager

```python
from statekanban.core.process import ProcessManager
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `create_process` | `(role, tool_permits, viewport_spec) -> ProcessInfo` | Create process in CREATED state. |
| `activate` | `(process_id: str) -> None` | Transition CREATED/SUSPENDED -> ACTIVE. Starts heartbeat. |
| `suspend` | `(process_id: str) -> None` | Transition ACTIVE -> SUSPENDED. |
| `terminate` | `(process_id, terminator) -> None` | Transition to TERMINATED. Raises `SelfTerminationError` if process terminates itself. |
| `claim_primary` | `(role, new_process_id) -> None` | New process claims primary, terminates predecessor. |
| `check_heartbeats` | `() -> list[str]` | Return process IDs with heartbeat timeout. |
| `heartbeat` | `(process_id: str) -> None` | Record heartbeat for a process. |
| `get_process` | `(process_id) -> ProcessInfo | None` | Get process by ID. |
| `list_processes` | `(state=None) -> list[ProcessInfo]` | List processes, optionally filtered by state. |

**Valid state transitions:**

```
CREATED -> ACTIVE
ACTIVE -> SUSPENDED
ACTIVE -> TERMINATED
SUSPENDED -> ACTIVE
SUSPENDED -> TERMINATED
TERMINATED -> (none -- terminal state)
```

---

### 2.7 LLM Adapters

```python
from statekanban.adapters.base import LLMAdapter
from statekanban.adapters.anthropic_adapter import AnthropicMessagesAdapter
from statekanban.adapters.cli_adapter import ClaudeCLIAdapter
from statekanban.adapters.mock_adapter import MockLLMAdapter
```

#### LLMAdapter (ABC)

| Method | Signature | Description |
|--------|-----------|-------------|
| `complete` | `async (messages, tools=None, max_tokens=4096, temperature=0.0) -> LLMResponse` | Send completion request. |

#### AnthropicMessagesAdapter

| Constructor Argument | Type | Default | Description |
|---------------------|------|---------|-------------|
| `api_key` | `str | None` | `None` | API key; reads `ANTHROPIC_API_KEY` env var if None |
| `model` | `str` | `"claude-sonnet-4-20250514"` | Model identifier |

Features: exponential backoff retry (3 attempts), rate limit handling, tool_use support.

#### ClaudeCLIAdapter

| Constructor Argument | Type | Default | Description |
|---------------------|------|---------|-------------|
| `cli_path` | `str` | `"claude"` | Path to claude CLI executable |

#### MockLLMAdapter

| Constructor Argument | Type | Default | Description |
|---------------------|------|---------|-------------|
| `responses` | `dict[str, list[LLMResponse]] | None` | `None` | Map of role name to response list (cycled) |

| Method | Signature | Description |
|--------|-----------|-------------|
| `set_response` | `(role, responses: list[LLMResponse]) -> None` | Configure responses for a role. |

---

### 2.8 Snapshot

```python
from statekanban.snapshot import save_snapshot, load_snapshot
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `save_snapshot` | `(kanban: StateKanban, path: str) -> None` | Serialize kanban to JSON file (atomic write). Raises `SnapshotWriteError`. |
| `load_snapshot` | `(path: str) -> StateKanban` | Load and validate snapshot. Raises `SnapshotIntegrityError`, `FileNotFoundError`. |

**Example:**

```python
from statekanban.core.kanban import StateKanban
from statekanban.snapshot import save_snapshot, load_snapshot

kanban = StateKanban()
# ... work with kanban ...

# Save
save_snapshot(kanban, "backup.json")

# Restore
restored = load_snapshot("backup.json")
# Integrity checksum is automatically verified
```

---

### 2.9 Config

```python
from statekanban.config import Config
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `llm_adapter` | `str` | `"mock"` | "anthropic", "cli", or "mock" |
| `llm_model` | `str` | `"claude-sonnet-4-20250514"` | LLM model identifier |
| `llm_max_tokens` | `int` | `4096` | Max output tokens |
| `llm_temperature` | `float` | `0.0` | Sampling temperature |
| `heartbeat_interval` | `int` | `30` | Seconds between heartbeats |
| `heartbeat_threshold` | `int` | `90` | Seconds before heartbeat timeout (3x interval) |
| `convergence_max_rounds` | `int` | `10` | Max convergence iterations |
| `default_token_budget` | `int` | `2000` | Default token budget for viewport slicing |
| `enable_type_check` | `bool` | `False` | Enable type checking in OutputValve |
| `enable_test_run` | `bool` | `True` | Enable test execution in OutputValve |
| `enable_human_gate` | `bool` | `False` | Enable human confirmation (P2) |
| `tool_timeout_default` | `float` | `60.0` | Default tool timeout (seconds) |
| `shell_timeout_default` | `float` | `60.0` | Default shell command timeout |
| `snapshot_dir` | `str` | `".statekanban/snapshots"` | Snapshot directory |
| `max_intent_length` | `int` | `4096` | Max CLI intent string length |
| `extra` | `dict[str, Any]` | `{}` | Additional configuration keys |

**Methods:**

- `Config.from_dict(data) -> Config` -- Create from dict, ignoring unknown keys.
- `to_dict() -> dict[str, Any]` -- Serialize to dict.

---

### 2.10 CLI Commands

```bash
statekanban run --intent INTENT [--config CONFIG]
statekanban status
statekanban snapshot [--output PATH]
statekanban restore --file PATH
```

| Command | Options | Description |
|---------|---------|-------------|
| `run` | `--intent` (required), `--config` (optional) | Start a development task. Creates Coder, Reviewer, Tester processes and writes initial IntentSignal. |
| `status` | (none) | Display FluidZone/CrystalZone/AuditZone summary. |
| `snapshot` | `--output` (default: `snapshot.json`) | Save kanban to JSON file. |
| `restore` | `--file` (required) | Restore kanban from snapshot file with integrity check. |

---

## 3. Error Codes

Format: `SK_<MODULE>_<CODE>`

| Code | HTTP | Class | Description | Recovery |
|------|------|-------|-------------|----------|
| `SK_FZ_001` | 400 | `InvalidSignalError` | Invalid signal schema | Fix signal structure |
| `SK_FZ_002` | 409 | `SignalCollisionError` | Signal collision detected | Run convergence |
| `SK_FZ_003` | 408 | `ConvergenceTimeoutError` | Convergence > 10 rounds | Manual intervention |
| `SK_CZ_001` | 409 | `ArtifactConflictError` | Duplicate seq_no | Auto-assign seq_no |
| `SK_CZ_002` | 405 | `AppendOnlyViolationError` | Append-only violation | Not possible via API |
| `SK_AZ_001` | 500 | `AuditWriteError` | Audit write failure | Log to stderr, continue |
| `SK_VS_001` | 400 | `InvalidViewportSpecError` | Invalid viewport spec | Fix spec configuration |
| `SK_VS_002` | 413 | `SliceOverflowError` | Slice exceeds token budget | Increase budget or reduce scope |
| `SK_OV_001` | 422 | `SyntaxCheckError` | Syntax check failed | Rework artifact |
| `SK_OV_002` | 422 | `TypeCheckError` | Type check failed | Rework artifact |
| `SK_OV_003` | 422 | `TestExecutionError` | Test execution failed | Rework artifact |
| `SK_OV_004` | 500 | `AtomicWriteError` | Atomic write failed | Check filesystem, retry |
| `SK_OV_005` | 403 | `HumanGateRejectedError` | Human gate rejected | Revise and resubmit |
| `SK_TR_001` | 403 | `PermissionDeniedError` | Permission denied | Use permitted tool |
| `SK_TR_002` | 404 | `ToolNotFoundError` | Tool not found | Register tool first |
| `SK_TR_003` | 408 | `ToolTimeoutError` | Tool execution timeout | Retry or adjust timeout |
| `SK_PM_001` | 409 | `InvalidStateTransitionError` | Invalid state transition | Check current state |
| `SK_PM_002` | 403 | `SelfTerminationError` | Self-termination attempted | Request scheduler termination |
| `SK_PM_003` | 408 | `HeartbeatTimeoutError` | Heartbeat timeout | Auto-recovery from snapshot |
| `SK_PM_004` | 409 | `HandoffError` | Handoff failed | Verify predecessor exists |
| `SK_MB_001` | 400 | `SubscriptionError` | Invalid subscription | Fix signal type or callback |
| `SK_MB_002` | 408 | `SyncCallTimeoutError` | Sync call timeout | Increase timeout or check callee |
| `SK_LLM_001` | 429 | `LLMRateLimitError` | Rate limit hit | Exponential backoff retry |
| `SK_LLM_002` | 401 | `LLMAuthError` | Authentication failure | Fix API key |
| `SK_LLM_003` | 500 | `LLMResponseParseError` | Response parse error | Retry with different parameters |
| `SK_SN_001` | 422 | `SnapshotIntegrityError` | Snapshot checksum mismatch | Use earlier snapshot |
| `SK_SN_002` | 500 | `SnapshotWriteError` | Snapshot write failed | Check disk space/permissions |