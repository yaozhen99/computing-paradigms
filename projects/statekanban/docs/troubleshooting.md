# StateKanban Troubleshooting Guide

Common issues, their causes, and step-by-step solutions.

---

## 1. Installation Issues

### 1.1 `pip install` fails with Python version error

**Symptom:**

```
ERROR: Package 'statekanban' requires Python >=3.11
```

**Cause:** StateKanban requires Python 3.11 or later due to use of modern type hint syntax (`X | None`, `dict[str, Any]`).

**Solution:**

```bash
# Check your Python version
python --version

# If below 3.11, install a supported version
# On macOS (Homebrew):
brew install python@3.11

# On Ubuntu:
sudo apt install python3.11 python3.11-venv

# Then create a venv with the correct version
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 1.2 `ModuleNotFoundError: No module named 'click'`

**Cause:** The `click` dependency was not installed.

**Solution:**

```bash
pip install -e ".[dev]"
# Or install dependencies directly:
pip install click>=8.1 anthropic>=0.30
```

### 1.3 `anthropic` package import error on startup

**Symptom:**

```
ImportError: cannot import name 'AsyncAnthropic' from 'anthropic'
```

**Cause:** The installed `anthropic` SDK version is too old.

**Solution:**

```bash
pip install --upgrade anthropic>=0.30
```

If you do not need the Anthropic adapter, use the mock or CLI adapter instead:

```bash
statekanban run --intent "..." --adapter mock
```

---

## 2. LLM Adapter Issues

### 2.1 `LLMAuthError: ANTHROPIC_API_KEY not set`

**Symptom:**

```
statekanban.core.errors.LLMAuthError: ANTHROPIC_API_KEY not set
```

**Cause:** The `ANTHROPIC_API_KEY` environment variable is not set or is empty.

**Solution:**

```bash
# Set the API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Verify it is set
echo $ANTHROPIC_API_KEY

# Alternatively, use a .env file in the project root
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
```

### 2.2 `LLMRateLimitError: Anthropic API rate limit hit`

**Symptom:**

```
statekanban.core.errors.LLMRateLimitError: Anthropic API rate limit hit
```

**Cause:** The Anthropic API rate limit has been exceeded. The adapter retries 3 times with exponential backoff before raising this error.

**Solution:**

1. Wait a few seconds and retry. The adapter already uses exponential backoff (1s, 2s, 4s).
2. Check your Anthropic account rate limits at console.anthropic.com.
3. Reduce the number of concurrent processes or increase the interval between calls.
4. Consider using a model with higher rate limits.

### 2.3 `LLMResponseParseError: Failed to parse response`

**Symptom:**

```
statekanban.core.errors.LLMResponseParseError: Failed to parse response: ...
```

**Cause:** The LLM returned a response that could not be parsed into the expected format.

**Solution:**

1. Retry the request -- transient API issues can cause malformed responses.
2. Check if the `anthropic` SDK version is compatible with the model version.
3. If using custom tools, verify the tool definitions are valid JSON Schema.

### 2.4 `ClaudeCLIAdapter: Claude CLI not found`

**Symptom:**

```
statekanban.core.errors.LLMAuthError: Claude CLI not found at: claude
```

**Cause:** The `claude` command-line tool is not installed or not on the PATH.

**Solution:**

```bash
# Install Claude CLI (if available)
npm install -g @anthropic-ai/claude-cli

# Or specify the full path
statekanban run --intent "..." --adapter cli --cli-path /usr/local/bin/claude
```

---

## 3. Viewport and Slicing Issues

### 3.1 `InvalidViewportSpecError: No viewport spec registered for role`

**Symptom:**

```
statekanban.core.errors.InvalidViewportSpecError: No viewport spec registered for role: devops
```

**Cause:** A custom role was created without a corresponding ViewportSpec.

**Solution:**

Register a ViewportSpec for the custom role before creating its process:

```python
from statekanban.core.kanban import ViewportSpec, SignalType, ArtifactType

spec = ViewportSpec(
    role="devops",
    visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
    visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG],
    visible_target_patterns=["*"],
    max_tokens=2000,
)
kanban.register_viewport(spec)
```

### 3.2 `SliceOverflowError: Cannot fit any items within token budget`

**Symptom:**

```
statekanban.core.errors.SliceOverflowError: Cannot fit any items within token budget (2000) for role: coder
```

**Cause:** Even a single signal or artifact exceeds the token budget for the role's viewport.

**Solution:**

1. Increase the token budget in the ViewportSpec:

```python
spec = ViewportSpec(
    role="coder",
    visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
    visible_artifact_types=[ArtifactType.CODE],
    visible_target_patterns=["*"],
    max_tokens=4000,  # Increase from 2000
)
```

2. Reduce the scope of visible items (narrower target patterns or fewer artifact types).
3. Check if a single artifact has abnormally large content; consider splitting it.

---

## 4. Tool and Permission Issues

### 4.1 `PermissionDeniedError: Role 'reviewer' lacks permission for tool 'write_file'`

**Symptom:**

```
statekanban.core.errors.PermissionDeniedError: Role 'reviewer' lacks permission for tool 'write_file'
```

**Cause:** The Reviewer role is not permitted to call `write_file`. Only `coder` and `integrator` have this permission.

**Solution:**

This is by design -- Reviewer should not write files. If you need a custom role with write access, register the tool with the role in its permission set:

```python
from statekanban.core.kanban import ToolDef

# Create a new tool definition that includes the custom role
registry.register(
    ToolDef(
        name="write_file_custom",
        description="Write with custom permissions",
        param_schema={...},
        required_permissions={"custom_role"},
    ),
    write_file_impl,
)
```

### 4.2 `ToolNotFoundError: Tool not found: my_custom_tool`

**Symptom:**

```
statekanban.core.errors.ToolNotFoundError: Tool not found: my_custom_tool
```

**Cause:** The tool was never registered in the ToolRegistry.

**Solution:**

Register the tool before dispatching calls:

```python
from statekanban.core.kanban import ToolDef

async def my_custom_tool(params):
    return {"result": "done"}

registry.register(
    ToolDef(
        name="my_custom_tool",
        description="Custom tool description",
        param_schema={"type": "object", "properties": {}},
        required_permissions={"all_roles"},
    ),
    my_custom_tool,
)
```

### 4.3 `ToolTimeoutError: Tool 'run_shell' timed out after 120s`

**Symptom:**

```
statekanban.core.errors.ToolTimeoutError: Tool 'run_shell' timed out after 120s
```

**Cause:** The shell command execution exceeded the timeout limit.

**Solution:**

1. Check if the command is hanging (e.g., waiting for input).
2. Increase the timeout when calling the tool:

```python
result = await registry.dispatch("run_shell", "tester", {
    "command": "long_running_command",
    "timeout": 300,  # 5 minutes
})
```

3. Use background execution if the command is expected to run long.

---

## 5. Process Management Issues

### 5.1 `SelfTerminationError: Process cannot terminate itself`

**Symptom:**

```
statekanban.core.errors.SelfTerminationError: Process abc123 cannot terminate itself
```

**Cause:** A process attempted to call `terminate()` with its own process_id as the terminator. This is forbidden by design.

**Solution:**

Only the scheduler (ProcessManager) or another process can terminate a process:

```python
# Correct: scheduler terminates the process
pm.terminate(process_id, terminator="scheduler")

# Incorrect: process terminates itself
pm.terminate(process_id, terminator=process_id)  # raises SelfTerminationError
```

### 5.2 `InvalidStateTransitionError: Invalid transition: terminated -> active`

**Symptom:**

```
statekanban.core.errors.InvalidStateTransitionError: Invalid transition: terminated -> active
```

**Cause:** Attempting to transition a TERMINATED process back to ACTIVE. TERMINATED is a terminal state.

**Solution:**

Create a new process for the role instead:

```python
# Instead of reactivating a terminated process:
new_process = pm.create_process(
    role="coder",
    tool_permits={"write_file", "read_file", "call_llm", "search_code"},
    viewport_spec=kanban.get_viewport_spec("coder"),
)
pm.activate(new_process.process_id)
```

### 5.3 `HandoffError: No predecessor process exists for role`

**Symptom:**

```
statekanban.core.errors.HandoffError: No predecessor process exists for role: architect
```

**Cause:** `claim_primary()` was called for a role that has no existing process.

**Solution:**

Use `create_process()` + `activate()` for the first process of a role. `claim_primary()` is only for replacing an existing process:

```python
# First process: use create + activate
info = pm.create_process(role="architect", tool_permits=..., viewport_spec=...)
pm.activate(info.process_id)

# Later, replace with a new process:
new_info = pm.create_process(role="architect", tool_permits=..., viewport_spec=...)
pm.claim_primary("architect", new_info.process_id)
```

### 5.4 Heartbeat timeout detected

**Symptom:** `check_heartbeats()` returns process IDs that have timed out.

**Cause:** The process has not recorded a heartbeat within the threshold (default: 90 seconds = 3x the 30s interval).

**Solution:**

1. Ensure the process is calling `pm.heartbeat(process_id)` regularly.
2. If the process crashed, recreate it from the last snapshot:

```python
timed_out = pm.check_heartbeats()
for pid in timed_out:
    process = pm.get_process(pid)
    if process:
        pm.terminate(pid, terminator="heartbeat_monitor")
        # Recreate from snapshot
        new_process = pm.create_process(
            role=process.role,
            tool_permits=process.tool_permits,
            viewport_spec=process.viewport_spec,
        )
        pm.activate(new_process.process_id)
```

---

## 6. Snapshot Issues

### 6.1 `SnapshotIntegrityError: Snapshot integrity check failed`

**Symptom:**

```
statekanban.core.errors.SnapshotIntegrityError: Snapshot integrity check failed: checksum mismatch
```

**Cause:** The snapshot file was modified or corrupted after it was written. The SHA-256 checksum embedded in the snapshot does not match the recomputed checksum.

**Solution:**

1. Do not manually edit snapshot JSON files.
2. If you have an earlier snapshot, use that instead:

```bash
statekanban restore --file earlier_snapshot.json
```

3. If no valid snapshot exists, start fresh:

```bash
statekanban run --intent "..." # creates a new kanban
```

### 6.2 `SnapshotWriteError: Failed to write snapshot`

**Symptom:**

```
statekanban.core.errors.SnapshotWriteError: Failed to write snapshot to /path/snapshot.json: [Errno 13] Permission denied
```

**Cause:** The snapshot directory or file is not writable.

**Solution:**

```bash
# Check directory permissions
ls -la .statekanban/snapshots/

# Create the directory with proper permissions
mkdir -p .statekanban/snapshots
chmod 755 .statekanban/snapshots

# Or specify a different output path
statekanban snapshot --output /tmp/snapshot.json
```

### 6.3 `FileNotFoundError: Snapshot file not found`

**Symptom:**

```
FileNotFoundError: Snapshot file not found: missing_snapshot.json
```

**Cause:** The specified snapshot file does not exist.

**Solution:**

1. Verify the file path is correct.
2. Check if the file was moved or deleted.
3. List available snapshots:

```bash
ls -la .statekanban/snapshots/
```

---

## 7. CrystalZone and FluidZone Issues

### 7.1 `ArtifactConflictError: Sequence number X already exists`

**Symptom:**

```
statekanban.core.errors.ArtifactConflictError: Sequence number 5 already exists
```

**Cause:** An artifact was appended with an explicit `seq_no` that already exists in CrystalZone.

**Solution:**

Use `seq_no=0` to let CrystalZone auto-assign the next available sequence number:

```python
artifact = Artifact(
    seq_no=0,  # Auto-assigned
    artifact_type=ArtifactType.CODE,
    path="src/module.py",
    content="...",
    checksum=compute_checksum("..."),
    author_role="coder",
    created_at=now_utc(),
)
seq_no = crystal.append(artifact)
```

### 7.2 `InvalidSignalError: signal_id is required`

**Symptom:**

```
statekanban.core.errors.InvalidSignalError: signal_id is required
```

**Cause:** A signal was created with an empty `signal_id`.

**Solution:**

Always use `make_signal_id()` to generate a UUID4 signal ID:

```python
from statekanban.core.kanban import IntentSignal, make_signal_id, now_utc

signal = IntentSignal(
    signal_id=make_signal_id(),  # Always generate a new UUID
    author_role="coder",
    target_id="feature_x",
    payload={},
    timestamp=now_utc(),
    round_number=0,
)
```

### 7.3 Convergence never completes (runs 10 rounds)

**Symptom:** `ConvergenceResult.forced_terminate = True` after 10 rounds.

**Cause:** Coder and Reviewer signals continue to conflict after 10 convergence iterations. This is a design limit to prevent infinite loops.

**Solution:**

1. Check the FluidZone signals to understand the conflict:

```python
signals = kanban.fluid.read_signals(target_id="contested_artifact")
for s in signals:
    print(f"{s.author_role}: {s.signal_type.value} (round {s.round_number})")
```

2. Manually resolve by clearing stale signals and re-injecting:

```python
kanban.fluid.clear_signals(target_id="contested_artifact", round_number_ge=0)
# Re-inject a consensus signal
```

3. Check audit logs for convergence timeout details:

```python
entries = kanban.audit.read_entries(event_type="convergence_timeout")
```

---

## 8. OutputValve Issues

### 8.1 `SyntaxCheckError: Python syntax error`

**Symptom:**

```
OutputValve validation failed: Python syntax error: invalid syntax (file.py, line 42)
```

**Cause:** The artifact content contains Python syntax errors.

**Solution:**

1. Fix the syntax error in the generated code.
2. The error is automatically injected as an ErrorSignal into FluidZone, which will trigger a rework loop by the Coder process.
3. To manually inspect the error:

```python
error_signals = kanban.fluid.read_signals(
    signal_type=SignalType.ERROR,
    target_id="src/module.py",
)
for s in error_signals:
    print(s.error_detail)
```

### 8.2 `AtomicWriteError: Atomic write failed`

**Symptom:**

```
statekanban.core.errors.AtomicWriteError: Atomic write failed for /path/file.py: [Errno 13] Permission denied
```

**Cause:** The filesystem does not allow writing to the target path.

**Solution:**

1. Check file and directory permissions.
2. Ensure the parent directory exists.
3. On Windows, check if the file is locked by another process.
4. Check available disk space.

---

## 9. General Debugging Tips

### 9.1 Inspecting the Audit Log

The AuditZone records every state change. Query it to trace issues:

```python
# All entries
entries = kanban.audit.read_entries()

# Filter by event type
tool_calls = kanban.audit.read_entries(event_type="tool_call")
timeouts = kanban.audit.read_entries(event_type="tool_timeout")
state_changes = kanban.audit.read_entries(event_type="process_activated")

# Filter by actor
coder_events = kanban.audit.read_entries(actor="coder")

# Get entries since a specific ID
recent = kanban.audit.read_entries(since_entry_id=100)
```

### 9.2 Checking Board Status via CLI

```bash
statekanban status
```

This shows:
- FluidZone: total signals, intent count, veto count, error count
- CrystalZone: latest sequence number, artifact counts by type
- AuditZone: total entries, last action
- Processes: count per state

### 9.3 Creating a Debug Snapshot

Before investigating an issue, save a snapshot so you can restore it later:

```bash
statekanban snapshot --output debug_snapshot.json
```

### 9.4 Running with the Mock Adapter

For debugging without consuming API credits:

```bash
statekanban run --intent "test task" --adapter mock
```

The MockLLMAdapter returns deterministic responses and requires no API key.

### 9.5 Checking Test Coverage

```bash
cd 03_source/backend
pip install pytest pytest-asyncio pytest-cov
pytest --cov=statekanban --cov-report=term-missing
```

The test suite includes 203 tests covering all core modules with integration tests for end-to-end pipelines.