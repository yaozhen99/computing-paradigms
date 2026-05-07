# R5 Architecture Design: Configurable Project Space + R4 Legacy Fixes

**Round**: R5
**Architect**: Claude (architect role)
**Date**: 2026-05-07
**Input**: `01_requirements/r5_requirements.md` (5 REQ: 501-505)
**Base code**: `05_delivery/statekanban/` (R4, 381 tests passing)

---

## Overview

R5 addresses a structural gap (project-space path resolution, REQ-501/502/503) and two deferred R4 interface deviations (dual-parameter `set_behavior_mode` signature, REQ-504; E2E test single-call pattern, REQ-505). The design preserves backward compatibility for REQ-501/502/503 (empty-string default falls back to CWD) and introduces a controlled breaking change for REQ-504 (removing overloaded positional signature).

---

## REQ-501: Config.project_root

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `05_delivery/statekanban/config.py` | `Config` dataclass | Add field |
| `05_delivery/statekanban/config.py` | `Config.resolve_path()` | Add method |
| `05_delivery/statekanban/config.py` | `Config.from_dict()` | Extend (already handles unknown keys, field auto-included) |
| `05_delivery/statekanban/config.py` | `Config.to_dict()` | Extend (dataclasses.asdict already covers new fields) |

### Interface Change

```python
@dataclass
class Config:
    # ... existing fields ...

    # REQ-501: Project space root
    project_root: str = ""  # empty string => os.getcwd() at resolution time

    def resolve_path(self, relative_path: str) -> str:
        """Resolve a path relative to project_root.

        If project_root is empty string, falls back to os.getcwd().
        If relative_path is already absolute, returns it unchanged.

        Args:
            relative_path: Path to resolve (typically relative).

        Returns:
            Absolute path resolved against project_root (or CWD).
        """
        if os.path.isabs(relative_path):
            return relative_path
        base = self.project_root if self.project_root else os.getcwd()
        return os.path.join(base, relative_path)
```

### Data Flow

```
Config(project_root="")
    |
    v
resolve_path(".statekanban/snapshots")
    |
    v  (project_root="" => CWD fallback)
os.getcwd() + "/.statekanban/snapshots"


Config(project_root="/tmp/sk_project")
    |
    v
resolve_path(".statekanban/snapshots")
    |
    v  (project_root set)
"/tmp/sk_project/.statekanban/snapshots"
```

### Compatibility Analysis

- **from_dict / to_dict**: Already work via `dataclasses.asdict()` and `cls(**filtered)`. Adding a new field with a default value means `Config()` still works, `Config.from_dict({})` still works (field defaults to `""`), and `Config.from_dict({"project_root": "/tmp/x"})` populates the field. No code change needed in these methods -- the dataclass machinery handles it.
- **Existing tests**: No existing test constructs `Config` with positional args that would be disrupted (all use `Config()` or keyword args). The default `project_root=""` preserves identical behavior.
- **os.getcwd() audit**: Currently zero `os.getcwd()` calls in `05_delivery/statekanban/`. All path resolution is implicit (relative paths written to CWD by the OS). After REQ-501, `resolve_path()` becomes the single point where `os.getcwd()` is called for project-space purposes.

---

## REQ-502: CLI --project-root

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `05_delivery/statekanban/cli/main.py` | `build_parser()` | Add argument |
| `05_delivery/statekanban/cli/main.py` | `cmd_drive()` | Add propagation + validation |

### Interface Change

```python
# In build_parser(), drive sub-command:
drive_p.add_argument(
    "--project-root",
    default=None,
    help="Project root directory (default: current working directory)",
)
```

```python
# In cmd_drive(), after config = Config():
if args.project_root is not None:
    project_root = os.path.abspath(args.project_root)
    if not os.path.isdir(project_root):
        print(f"Project root does not exist: {project_root}", file=sys.stderr)
        return 1
    config.project_root = project_root
```

### Data Flow

```
CLI: statekanban drive "intent" --project-root /tmp/myproject
    |
    v
argparse: args.project_root = "/tmp/myproject"
    |
    v
cmd_drive():
    1. os.path.abspath("/tmp/myproject") => "/tmp/myproject" (already absolute)
    2. os.path.isdir("/tmp/myproject") => True
    3. config.project_root = "/tmp/myproject"
    |
    v
Engine reads config.project_root via config.resolve_path()
```

```
CLI: statekanban drive "intent" --project-root ./relative
    |
    v
argparse: args.project_root = "./relative"
    |
    v
cmd_drive():
    1. os.path.abspath("./relative") => "/current/work/dir/relative"
    2. os.path.isdir(...) => True/False
    3. If True: config.project_root = "/current/work/dir/relative"
       If False: exit(1), print error
```

### Error Handling

| Condition | Behavior | Exit Code |
|-----------|----------|-----------|
| `--project-root` not provided | `config.project_root` remains `""` (CWD fallback) | N/A |
| Provided path is absolute and exists | Set `config.project_root` to the path | 0 |
| Provided path is relative | Resolve with `os.path.abspath()`, then check existence | 0 or 1 |
| Provided path does not exist | Print error to stderr, exit | 1 |
| `--project-root` on `snapshot` sub-command | Ignored (snapshot uses its own `path` argument) | N/A |

### Compatibility Analysis

- **Existing CLI tests**: No existing test uses `--project-root`. The flag defaults to `None`, so `cmd_drive()` does not touch `config.project_root` when the flag is absent. All existing CLI behavior is preserved.
- **snapshot sub-command**: REQ-502 explicitly scopes `--project-root` to the `drive` sub-command only. The `snapshot` sub-command's `path` argument remains unchanged.

---

## REQ-503: Engine Path Resolution

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `05_delivery/statekanban/engine/engine.py` | `Engine.__init__()` | Store resolved project_root |
| `05_delivery/statekanban/engine/engine.py` | `Engine._crystalize_and_write()` | Pass project_root to OutputValve |
| `05_delivery/statekanban/core/valve.py` | `OutputValve.__init__()` | Add `project_root` parameter |
| `05_delivery/statekanban/core/valve.py` | `OutputValve.validate_and_write()` | Resolve artifact path against project_root |
| `05_delivery/statekanban/core/valve.py` | `OutputValve._atomic_write()` | No change (already accepts absolute path) |
| `05_delivery/statekanban/snapshot.py` | `SnapshotManager.__init__()` | Add `project_root` parameter |
| `05_delivery/statekanban/snapshot.py` | `SnapshotManager._resolve_path()` | Use project_root as base |
| `05_delivery/statekanban/snapshot.py` | `list_snapshots()` | Accept optional `project_root` parameter |

### Interface Changes

#### OutputValve

```python
class OutputValve:
    def __init__(
        self,
        validators: list[Validator] | None = None,
        kanban: StateKanban | None = None,
        project_root: str = "",  # REQ-503
    ) -> None:
        self._validators = validators or [SyntaxValidator(), TypeValidator(), TestValidator()]
        self._kanban = kanban
        self._project_root = project_root  # REQ-503

    async def validate_and_write(self, artifact: Artifact) -> ValveResult:
        # ... validation chain unchanged ...
        # All validators passed -- resolve artifact path and write
        resolved_path = self._resolve_artifact_path(artifact.path)
        self._atomic_write(resolved_path, artifact.content)
        # ...

    def _resolve_artifact_path(self, path: str) -> str:
        """Resolve artifact path against project_root."""
        if os.path.isabs(path):
            return path
        base = self._project_root if self._project_root else os.getcwd()
        return os.path.join(base, path)
```

#### SnapshotManager

```python
class SnapshotManager:
    def __init__(
        self,
        base_dir: str = ".statekanban/snapshots",
        project_root: str = "",  # REQ-503
    ) -> None:
        self._base_dir = base_dir
        self._project_root = project_root

    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to project_root + base_dir."""
        if os.path.isabs(path):
            return path
        base = self._project_root if self._project_root else os.getcwd()
        effective_base = os.path.join(base, self._base_dir)
        return os.path.join(effective_base, path)
```

#### Engine

```python
class Engine:
    def __init__(self, ..., config: Config) -> None:
        # ... existing init code ...
        self._project_root = config.resolve_path("")  # Resolves "" to CWD or project_root
        # Propagate project_root to OutputValve
        self._valve._project_root = config.project_root  # or: pass in constructor
```

Alternative (preferred): Pass `project_root` into OutputValve at construction time, not by post-init mutation.

```python
# In cmd_drive() and E2ETestRunner._run_drive():
valve = OutputValve(kanban=kanban, project_root=config.project_root)
```

### Data Flow

```
Config(project_root="/tmp/sk_project")
    |
    v
Engine.__init__(config)
    |-- self._project_root = config.resolve_path("") = "/tmp/sk_project"
    |
    v  _crystalize_and_write():
    artifact.path = "output.py"  (relative)
    |
    v  OutputValve.validate_and_write(artifact)
    |-- resolved = _resolve_artifact_path("output.py")
    |-- = os.path.join("/tmp/sk_project", "output.py")
    |-- = "/tmp/sk_project/output.py"
    |
    v  _atomic_write("/tmp/sk_project/output.py", content)
    |-- writes to /tmp/sk_project/output.py
```

```
Config(project_root="")
    |
    v  resolve_path("") => os.getcwd()
    |
    v  All paths resolved against CWD (identical to R4 behavior)
```

### os.getcwd() Elimination Plan

Current state: zero explicit `os.getcwd()` calls in the codebase. Path resolution is implicit (relative paths resolved by the OS against CWD).

After REQ-503:
- `Config.resolve_path()` introduces the **single authorized** `os.getcwd()` call.
- `OutputValve._resolve_artifact_path()` may call `os.getcwd()` only when `project_root == ""`.
- `SnapshotManager._resolve_path()` may call `os.getcwd()` only when `project_root == ""`.
- These are the **only** three locations where `os.getcwd()` may appear for project-space resolution.
- No other module should call `os.getcwd()` for this purpose.

### Directory Auto-Creation

REQ-503 requires: "If project_root is set and does not exist, Engine must create it on first use (for snapshot_dir sub-directories)."

Design: `Config.resolve_path()` does NOT create directories. Directory creation is the responsibility of the consumer:
- `SnapshotManager.save_snapshot()` already creates parent directories via `os.makedirs(parent, exist_ok=True)`.
- `OutputValve._atomic_write()` already creates parent directories via `os.makedirs(parent, exist_ok=True)`.
- For the `project_root` itself (not just sub-directories), `Engine._crystalize_and_write()` should call `os.makedirs(self._project_root, exist_ok=True)` before the first valve write if `project_root` is set and does not exist.

```python
# In Engine._crystalize_and_write(), before valve submission:
if self._project_root and not os.path.exists(self._project_root):
    os.makedirs(self._project_root, exist_ok=True)
```

### Compatibility Analysis

- **OutputValve**: New `project_root` parameter defaults to `""`. All existing `OutputValve(kanban=kanban)` calls remain valid. When `project_root=""`, `_resolve_artifact_path()` falls back to `os.getcwd()`, which produces the same behavior as the current implicit CWD resolution.
- **SnapshotManager**: Same pattern -- new `project_root=""` default, CWD fallback.
- **Engine**: No Engine signature change. `config.project_root` is read internally.
- **CLI / E2E helpers**: Both construct `OutputValve(kanban=kanban)`. Updated to `OutputValve(kanban=kanban, project_root=config.project_root)`.
- **Existing tests**: All 381 tests use default `Config()` (project_root=""), so behavior is identical.

---

## REQ-504: Dual-Parameter Signature Fix

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `05_delivery/statekanban/adapters/mock_adapter.py` | `MockLLMAdapter.set_behavior_mode()` | Replace signature |
| `05_delivery/statekanban/adapters/mock_adapter.py` | `MockLLMAdapter._apply_behavior_mode()` | Rewrite for dual-parameter |
| `05_delivery/statekanban/adapters/mock_adapter.py` | `MockLLMAdapter._resolve_behavior_string()` | Remove (no longer needed) |
| `05_delivery/statekanban/adapters/mock_adapter.py` | `MockLLMAdapter._behavior_mode` | Change type to tuple |
| `05_delivery/statekanban/testing/e2e_helpers.py` | `happy_path_scenario()` | Update to dual-param |
| `05_delivery/statekanban/testing/e2e_helpers.py` | `collision_convergence_scenario()` | Update to dual-param |
| `05_delivery/statekanban/testing/e2e_helpers.py` | `circuit_break_scenario()` | Update to dual-param |

### Interface Change

**Before (R4 overloaded)**:
```python
def set_behavior_mode(
    self,
    role_or_mode: str | MockReviewerBehavior | MockCoderBehavior,
    mode: str | None = None,
) -> None:
```

**After (R5 canonical)**:
```python
def set_behavior_mode(
    self,
    reviewer_behavior: MockReviewerBehavior = MockReviewerBehavior.ALWAYS_APPROVE,
    coder_behavior: MockCoderBehavior = MockCoderBehavior.GENERATE_SIMPLE,
) -> None:
    """Enable behavior mode. Auto-enables structured_mode.
    Simultaneously configures reviewer and coder behaviors.
    Also auto-configures tester and integrator roles.

    Args:
        reviewer_behavior: Reviewer response behavior.
        coder_behavior: Coder response behavior.

    Raises:
        TypeError: If called with positional args (old convention).
    """
```

### Internal State Change

```python
# Before:
self._behavior_mode: MockReviewerBehavior | MockCoderBehavior | None = None

# After:
self._reviewer_behavior: MockReviewerBehavior = MockReviewerBehavior.ALWAYS_APPROVE
self._coder_behavior: MockCoderBehavior = MockCoderBehavior.GENERATE_SIMPLE
self._behavior_mode_active: bool = False  # True after set_behavior_mode() called
```

### _apply_behavior_mode Rewrite

The current `_apply_behavior_mode` takes a single enum and applies it to one role. The new version must configure **both** reviewer and coder simultaneously, plus auto-configure tester and integrator.

```python
def _apply_behavior_mode(
    self,
    reviewer_behavior: MockReviewerBehavior,
    coder_behavior: MockCoderBehavior,
) -> None:
    """Pre-configure structured responses for all roles based on behavior modes."""
    self._structured_responses.clear()

    # --- Reviewer ---
    if reviewer_behavior == MockReviewerBehavior.ALWAYS_APPROVE:
        self.set_structured_response(
            role="reviewer",
            response_type="intent",
            target_id="task_root",
            payload={"approved": True},
        )
    elif reviewer_behavior == MockReviewerBehavior.ALWAYS_REJECT:
        self.set_structured_response(
            role="reviewer",
            response_type="veto",
            target_id="task_root",
            reason="Quality gate: always reject",
        )
    elif reviewer_behavior == MockReviewerBehavior.REJECT_THEN_APPROVE:
        self.set_structured_response(
            role="reviewer",
            response_type="veto",
            target_id="task_root",
            reason="Quality gate: needs rework",
        )
        self.set_structured_response(
            role="reviewer",
            response_type="intent",
            target_id="task_root",
            payload={"approved": True},
        )

    # --- Coder ---
    if coder_behavior == MockCoderBehavior.GENERATE_SIMPLE:
        self.set_structured_response(
            role="coder",
            response_type="artifact",
            target_id="task_root",
            artifact_path="output.py",
            artifact_content='def hello():\n    return "hello world"\n',
            artifact_type="code",
        )
    elif coder_behavior == MockCoderBehavior.GENERATE_WITH_BUG:
        self.set_structured_response(
            role="coder",
            response_type="artifact",
            target_id="task_root",
            artifact_path="output.py",
            artifact_content="def hello():\n    return undefined_var\n",
            artifact_type="code",
        )

    # --- Tester (auto-configured) ---
    self.set_structured_response(
        role="tester",
        response_type="intent",
        target_id="task_root",
        payload={"action": "test_passed", "coverage": "100%"},
    )

    # --- Integrator (auto-configured) ---
    self.set_structured_response(
        role="integrator",
        response_type="intent",
        target_id="task_root",
        payload={"action": "integrate", "files": ["output.py"]},
    )
```

### artifact_content Exact Values

| Mode | artifact_content | Notes |
|------|-----------------|-------|
| `GENERATE_SIMPLE` | `'def hello():\n    return "hello world"\n'` | Trailing newline added (REQ-504 AC-504.4) |
| `GENERATE_WITH_BUG` | `'def hello():\n    return undefined_var\n'` | Uses `return undefined_var`, not `print()` (REQ-504 AC-504.5) |

**Critical deviation from current code**: The current `GENERATE_WITH_BUG` uses `"def hello():\n    print('hello world')"` -- this is a bug (not actually buggy in a way that would fail). The R5 requirement specifies `"def hello():\n    return undefined_var\n"`, which references an undefined variable and will raise `NameError` at runtime. This must be corrected.

### Breaking Change: Positional Call Convention Removed

The old calling conventions that will raise `TypeError`:

```python
# OLD (will raise TypeError):
adapter.set_behavior_mode("coder", "generate_simple")
adapter.set_behavior_mode("reviewer", "always_approve")
adapter.set_behavior_mode(MockReviewerBehavior.ALWAYS_APPROVE)
adapter.set_behavior_mode(MockCoderBehavior.GENERATE_SIMPLE)

# NEW (canonical):
adapter.set_behavior_mode(
    reviewer_behavior=MockReviewerBehavior.ALWAYS_APPROVE,
    coder_behavior=MockCoderBehavior.GENERATE_SIMPLE,
)
adapter.set_behavior_mode()  # defaults: ALWAYS_APPROVE + GENERATE_SIMPLE
adapter.set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT)
adapter.set_behavior_mode(coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG)
```

### Call Site Migration Map

| File | Old Call | New Call |
|------|----------|----------|
| `testing/e2e_helpers.py:70` | `set_behavior_mode(MockReviewerBehavior.ALWAYS_APPROVE)` | `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_APPROVE)` |
| `testing/e2e_helpers.py:82` | `set_behavior_mode(MockReviewerBehavior.REJECT_THEN_APPROVE)` | `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE)` |
| `testing/e2e_helpers.py:94` | `set_behavior_mode(MockReviewerBehavior.ALWAYS_REJECT)` | `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT, coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG)` |
| `test_e2e.py:111` | `set_behavior_mode("coder", "generate_simple")` | `set_behavior_mode(coder_behavior=MockCoderBehavior.GENERATE_SIMPLE)` |
| `test_e2e.py:160-161` | Two separate calls | `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE, coder_behavior=MockCoderBehavior.GENERATE_SIMPLE)` |
| `test_e2e.py:209-210` | Two separate calls | `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT, coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG)` |
| `test_mock_adapter.py:60` | `set_behavior_mode(MockCoderBehavior.GENERATE_SIMPLE)` | `set_behavior_mode(coder_behavior=MockCoderBehavior.GENERATE_SIMPLE)` |
| `test_mock_adapter.py:84` | `set_behavior_mode(MockCoderBehavior.GENERATE_WITH_BUG)` | `set_behavior_mode(coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG)` |
| `test_mock_adapter.py:99` | `set_behavior_mode(MockReviewerBehavior.ALWAYS_APPROVE)` | `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_APPROVE)` |
| `test_mock_adapter.py:116` | `set_behavior_mode(MockReviewerBehavior.ALWAYS_REJECT)` | `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT)` |
| `test_mock_adapter.py:133` | `set_behavior_mode(MockReviewerBehavior.REJECT_THEN_APPROVE)` | `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE)` |
| `test_mock_adapter.py:153,161,177,187` | `set_behavior_mode(MockCoderBehavior.GENERATE_SIMPLE)` | `set_behavior_mode(coder_behavior=MockCoderBehavior.GENERATE_SIMPLE)` |
| `test_integration.py:85,87` | Two separate calls | Single dual-parameter call |

### Compatibility Analysis

- **Breaking change within R-series**: Allowed per R5 requirement constraints. All call sites must be updated.
- **behavior_mode property**: Current `self._behavior_mode` stores a single enum. With dual-parameter, this becomes two fields (`_reviewer_behavior`, `_coder_behavior`). The `behavior_mode` property should return a tuple `(self._reviewer_behavior, self._coder_behavior)` or be removed. Recommend returning a `NamedTuple` or tuple for backward inspection.
- **_get_behavior_response()**: Currently checks `self._behavior_mode == MockReviewerBehavior.REJECT_THEN_APPROVE`. Updated to check `self._reviewer_behavior == MockReviewerBehavior.REJECT_THEN_APPROVE`. Other behavior modes already use `_get_structured_response()` which cycles through `_structured_responses` per role.

---

## REQ-505: E2E Engine.drive() Fix

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `04_testing/test_scripts/test_e2e.py` | `test_tc_e2e_01_happy_path` | Rewrite set_behavior_mode call |
| `04_testing/test_scripts/test_e2e.py` | `test_tc_e2e_02_collision_convergence` | Rewrite set_behavior_mode call |
| `04_testing/test_scripts/test_e2e.py` | `test_tc_e2e_03_circuit_break` | Rewrite set_behavior_mode call |

### Design: Test Case Updates

#### TC-E2E-01: Happy Path

```python
async def test_tc_e2e_01_happy_path():
    """Happy path: coder produces, reviewer approves, converges in 1 round."""
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode(
        reviewer_behavior=MockReviewerBehavior.ALWAYS_APPROVE,
        coder_behavior=MockCoderBehavior.GENERATE_SIMPLE,
    )

    kanban = StateKanban()
    bus = MessageBus(kanban)
    registry = ToolRegistry(kanban)
    valve = OutputValve(kanban=kanban)
    # ... build engine ...
    result = await engine.drive("Write a hello function")

    assert result.converged is True
    assert result.total_rounds == 1
    assert len(result.artifact_files) >= 1
```

#### TC-E2E-02: Collision Convergence

```python
async def test_tc_e2e_02_collision_convergence():
    """Reviewer rejects then approves; converges in 2 rounds."""
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode(
        reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE,
        coder_behavior=MockCoderBehavior.GENERATE_SIMPLE,
    )

    # ... build engine ...
    result = await engine.drive("Write a hello function")

    assert result.converged is True
    assert result.total_rounds >= 2

    # Assert at least 1 VetoSignal in FluidZone (collision evidence)
    veto_signals = kanban.fluid.read_signals(signal_type=SignalType.VETO)
    assert len(veto_signals) >= 1
```

#### TC-E2E-03: Circuit Break

```python
async def test_tc_e2e_03_circuit_break():
    """Always reject + buggy code; circuit break after max_rounds."""
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode(
        reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT,
        coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG,
    )
    config = Config()
    config.convergence_max_rounds = 3

    # ... build engine with config ...
    result = await engine.drive("Write a hello function")

    assert result.converged is False
    # CrystalZone should have no artifacts (never converged)
    artifacts = kanban.crystal.read_artifacts()
    assert len(artifacts) == 0
```

### Data Flow

```
TC-E2E-01:
  adapter.set_behavior_mode(
      reviewer_behavior=ALWAYS_APPROVE,
      coder_behavior=GENERATE_SIMPLE,
  )
      |
      v  _apply_behavior_mode()
      |-- reviewer: set_structured_response("reviewer", "intent", {"approved": True})
      |-- coder: set_structured_response("coder", "artifact", content='def hello():\n    return "hello world"\n')
      |-- tester: set_structured_response("tester", "intent", {"action": "test_passed", ...})
      |-- integrator: set_structured_response("integrator", "intent", {"action": "integrate", ...})
      |
      v  engine.drive("Write a hello function")
      |-- Round 1: coder -> artifact, reviewer -> approve
      |-- Convergence detected
      |-- Crystal fix + valve write
      |
      v  result.converged = True, result.total_rounds = 1
```

### Compatibility Analysis

- **Engine.drive()**: No signature change. Tests already use `Engine.drive()` (R4 REQ-002 ensured this).
- **Key difference from R4**: Single `set_behavior_mode()` call sets both reviewer and coder (plus tester/integrator) in one step, instead of two separate calls. This eliminates the state-overwrite problem where the second call would overwrite `_behavior_mode` set by the first.
- **Assertion updates**: TC-E2E-02 adds VetoSignal assertion. TC-E2E-03 adds CrystalZone artifact assertion. These are new assertions that validate the behavior more precisely.

---

## Cross-REQ Interaction Analysis

### REQ-501 + REQ-503 Interaction

`Config.resolve_path()` (REQ-501) is the single method used by all path consumers (Engine, OutputValve, SnapshotManager) to resolve relative paths. REQ-503's consumers call `config.resolve_path(path)` instead of using `path` directly. This eliminates the need for each consumer to independently implement CWD fallback logic.

### REQ-502 + REQ-501 Interaction

CLI `--project-root` (REQ-502) sets `Config.project_root` (REQ-501). The CLI performs path validation (`os.path.isdir()`) before setting the config, ensuring that by the time Engine receives the Config, `project_root` is either `""` (CWD fallback) or a valid existing directory.

### REQ-504 + REQ-505 Interaction

REQ-504 defines the new `set_behavior_mode` signature. REQ-505 updates E2E tests to use it. REQ-505 depends on REQ-504 being implemented first -- the new signature must exist before tests can use it.

### REQ-503 + REQ-504 Interaction

No interaction. Path resolution and behavior mode are orthogonal concerns.

### REQ-501/502/503 + REQ-504/505 Interaction

No interaction. The project-root path system and the mock adapter behavior system are independent. They converge only in E2E test setup where both are configured, but they configure different aspects of the system.

---

## Implementation Order

The REQs have the following dependency structure:

```
REQ-501 (Config.project_root)
    |
    v
REQ-502 (CLI --project-root)     REQ-504 (dual-param signature)
    |                                 |
    v                                 v
REQ-503 (Engine path resolution)  REQ-505 (E2E test update)
```

Recommended implementation order:
1. **REQ-501**: Add `project_root` field and `resolve_path()` to Config
2. **REQ-502**: Add `--project-root` CLI flag and propagation
3. **REQ-503**: Update Engine, OutputValve, SnapshotManager to use `resolve_path()`
4. **REQ-504**: Rewrite `set_behavior_mode` with dual-keyword-parameter signature
5. **REQ-505**: Update E2E tests to use new signature

---

## Error Code Allocation

No new error codes needed for R5. Path validation errors in CLI use exit code 1 (standard CLI error). The `TypeError` raised by the new `set_behavior_mode` signature on positional calls is a standard Python error, not an SK_ error code.

If desired, a project-root-specific error code could be added:

| Code | Description | Module |
|------|-------------|--------|
| `SK_CFG_001` | Project root path does not exist | `config.py` |

This is optional since the CLI handles the validation before the config reaches Engine.

---

## Summary

| REQ | Files Modified | Breaking Change | Backward Compatible |
|-----|---------------|-----------------|-------------------|
| 501 | config.py | No | Yes (default `""` = CWD fallback) |
| 502 | cli/main.py | No | Yes (flag absent = no change) |
| 503 | engine.py, valve.py, snapshot.py | No | Yes (project_root="" = CWD behavior) |
| 504 | mock_adapter.py, e2e_helpers.py | Yes (positional signature removed) | No (call sites must be updated) |
| 505 | test_e2e.py, test_mock_adapter.py | No (test changes only) | N/A (tests are the deliverable) |
