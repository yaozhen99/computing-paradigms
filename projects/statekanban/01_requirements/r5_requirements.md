# R5 Requirements: Configurable Project Space + R4 Legacy Fixes

**Round**: R5
**Origin**: R4 completed with 381 tests passing, but left 2 implementation deviations; project_root is hardcoded throughout
**Core Goal**: Implement configurable project-space path resolution, and fix the 2 R4 legacy implementation deviations

---

## Background

R4 accomplished its primary objectives (dual-param `set_behavior_mode` signature, E2E tests driven by `Engine.drive()`, live API smoke test), but the review identified 2 deviations that were deferred:

1. `set_behavior_mode` accepts `(role_or_mode, mode)` instead of the canonical `(reviewer_behavior=, coder_behavior=)` keyword signature -- the current implementation uses positional overloading, not the intended dual-keyword-parameter design.
2. E2E tests TC-E2E-01/02/03 call `set_behavior_mode("coder", "generate_simple")` separately for each role rather than the single dual-parameter call `set_behavior_mode(reviewer_behavior=..., coder_behavior=...)`.

Additionally, the system has a structural gap: `Config` has no `project_root` field, the CLI has no `--project-root` flag, and `Engine` resolves paths against the current working directory (CWD) implicitly. This makes project-space portability impossible and testing unreliable across environments.

R5 addresses both the structural gap (REQ-501/502/503) and the 2 legacy deviations (REQ-504/505).

---

## REQ-501: Config.project_root -- Add project_root field to Config dataclass

**Description**

`Config` currently has no concept of a project root directory. All path-dependent features (snapshot storage, valve output, audit logs) rely on implicit CWD or hardcoded relative paths like `.statekanban/snapshots`. This REQ adds a `project_root: str` field to `Config`, defaulting to the current working directory, so that all path resolution has an explicit, configurable anchor point.

**Interface Change**

```python
@dataclass
class Config:
    # ... existing fields ...

    # Project space root (REQ-501)
    project_root: str = ""  # empty string => os.getcwd() at resolution time
```

**Behavior**

1. When `project_root` is an empty string (default), path resolution falls back to `os.getcwd()`, preserving backward compatibility.
2. When `project_root` is set to an absolute path, all internal path resolution (`snapshot_dir`, valve output path, etc.) must be resolved relative to `project_root`.
3. `Config.from_dict()` must accept `project_root` from the input dictionary.
4. `Config.to_dict()` must include `project_root` in the output dictionary.
5. No other module should call `os.getcwd()` directly for project-space resolution; they must read from `Config.project_root`.

**Acceptance Criteria**

- AC-501.1: `Config()` creates an instance with `project_root == ""` (backward compatible).
- AC-501.2: `Config(project_root="/tmp/test_project")` sets `project_root` to that path.
- AC-501.3: `Config.from_dict({"project_root": "/tmp/x"})` correctly populates the field.
- AC-501.4: `Config.to_dict()` includes `"project_root"` in its output.
- AC-501.5: Existing 381+ tests still pass without modification.

**Impact Scope**

| File | Change |
|------|--------|
| `05_delivery/statekanban/config.py` | Add `project_root` field, update `from_dict` / `to_dict` |
| `04_testing/test_scripts/test_config.py` | Add test cases for project_root (new or existing file) |

---

## REQ-502: CLI --project-root -- Add CLI flag for project root

**Description**

The `statekanban drive` command has no way to specify a project root directory. This REQ adds a `--project-root` flag to the `drive` sub-command that propagates the value into `Config.project_root`.

**Interface Change**

```python
# In build_parser(), drive sub-command:
drive_p.add_argument(
    "--project-root",
    default=None,
    help="Project root directory (default: current working directory)",
)
```

**Behavior**

1. If `--project-root` is provided, `cmd_drive()` sets `config.project_root` to the given value.
2. If `--project-root` is not provided, `config.project_root` remains `""` (falls back to CWD per REQ-501).
3. If the provided path is relative, it must be resolved to an absolute path using `os.path.abspath()`.
4. If the provided path does not exist, the CLI must exit with a non-zero code and a clear error message: `"Project root does not exist: <path>"`.
5. The `--project-root` flag does not apply to the `snapshot` sub-command (snapshots use their own path argument).

**Acceptance Criteria**

- AC-502.1: `statekanban drive "intent" --project-root /tmp/myproject` sets `config.project_root` to `/tmp/myproject`.
- AC-502.2: `statekanban drive "intent"` (no flag) leaves `config.project_root` as `""`.
- AC-502.3: `statekanban drive "intent" --project-root ./relative` resolves to `os.path.abspath("./relative")`.
- AC-502.4: `statekanban drive "intent" --project-root /nonexistent` exits with code 1 and prints error message.
- AC-502.5: Existing CLI tests still pass.

**Impact Scope**

| File | Change |
|------|--------|
| `05_delivery/statekanban/cli/main.py` | Add `--project-root` argument, propagate to Config in `cmd_drive()` |
| `04_testing/test_scripts/test_cli.py` | Add test cases for --project-root (new or existing file) |

---

## REQ-503: Engine path resolution -- Use Config.project_root for all path operations

**Description**

`Engine` and its sub-components currently resolve paths against CWD implicitly. The `OutputValve` writes files to CWD-relative paths, and `snapshot_dir` in Config is a relative path. This REQ ensures that all path resolution inside Engine and its dependencies uses `Config.project_root` as the base directory when set.

**Behavior**

1. `Engine.__init__()` stores `config.project_root` and resolves it: if `project_root == ""`, use `os.getcwd()`; otherwise, use the provided path.
2. `Engine._crystalize_and_write()` passes `project_root` to `OutputValve` so artifact paths are resolved relative to `project_root`.
3. `Config.snapshot_dir` (currently `".statekanban/snapshots"`) is resolved relative to `Config.project_root` when the latter is set.
4. No call to `os.getcwd()` remains in Engine, OutputValve, or SnapshotManager for path resolution purposes (they must use `Config.project_root`).
5. If `project_root` is set and does not exist, Engine must create it on first use (for snapshot_dir sub-directories).

**Acceptance Criteria**

- AC-503.1: When `Config(project_root="/tmp/sk_project")` is used, artifacts are written under that directory.
- AC-503.2: When `Config()` (default `project_root=""`) is used, behavior is identical to before (CWD-based).
- AC-503.3: `SnapshotManager` resolves `snapshot_dir` relative to `Config.project_root` when set.
- AC-503.4: No `os.getcwd()` calls remain in Engine, OutputValve, or SnapshotManager for project-space path resolution.
- AC-503.5: All 381+ existing tests still pass.

**Impact Scope**

| File | Change |
|------|--------|
| `05_delivery/statekanban/engine/engine.py` | Use `config.project_root` for path resolution |
| `05_delivery/statekanban/core/valve.py` | Accept and use `project_root` for output path resolution |
| `05_delivery/statekanban/snapshot.py` | Resolve `snapshot_dir` relative to `Config.project_root` |
| `04_testing/test_scripts/test_e2e.py` | Verify path resolution works with custom project_root |
| `04_testing/test_scripts/test_valve.py` | Add project_root test cases |

---

## REQ-504: Dual-parameter signature fix -- set_behavior_mode(reviewer_behavior=, coder_behavior=)

**Description**

R4 implemented `set_behavior_mode` as an overloaded method accepting either `(role_or_mode, mode)` positional arguments or `(EnumValue)`. The R4 requirement (REQ-001) specified a clean dual-keyword-parameter signature. The current implementation works but deviates from the intended interface: users must call `set_behavior_mode("coder", "generate_simple")` and `set_behavior_mode("reviewer", "always_approve")` separately, instead of the canonical single call with both keyword parameters.

This REQ replaces the overloaded signature with the canonical dual-keyword-parameter design from R4 REQ-001, while maintaining backward compatibility via a deprecation path.

**Target Interface**

```python
def set_behavior_mode(
    self,
    reviewer_behavior: MockReviewerBehavior = MockReviewerBehavior.ALWAYS_APPROVE,
    coder_behavior: MockCoderBehavior = MockCoderBehavior.GENERATE_SIMPLE,
) -> None:
    """Enable behavior mode. Auto-enables structured_mode.
    Simultaneously configures reviewer and coder behaviors."""
```

**Behavior**

1. Both parameters have default values, so `set_behavior_mode()` with no args is valid (sets ALWAYS_APPROVE + GENERATE_SIMPLE).
2. `set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE)` sets only reviewer behavior, coder defaults to GENERATE_SIMPLE.
3. `set_behavior_mode(coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG)` sets only coder behavior, reviewer defaults to ALWAYS_APPROVE.
4. Both can be set simultaneously: `set_behavior_mode(reviewer_behavior=..., coder_behavior=...)`.
5. Automatically configure tester role: `{"type": "intent", "target_id": "task_root", "payload": {"action": "test_passed", "coverage": "100%"}}`.
6. Automatically configure integrator role: `{"type": "intent", "target_id": "task_root", "payload": {"action": "integrate", "files": ["output.py"]}}`.
7. The old positional calling convention `set_behavior_mode("reviewer", "strict")` must be removed (not deprecated -- this is a breaking change within the R-series).
8. The old single-enum calling convention `set_behavior_mode(MockReviewerBehavior.ALWAYS_APPROVE)` must be removed.

**artifact_content exact values** (must match, no deviations):

| Mode | artifact_content |
|------|-----------------|
| GENERATE_SIMPLE | `"def hello():\n    return \"hello world\"\n"` |
| GENERATE_WITH_BUG | `"def hello():\n    return undefined_var\n"` |

**Acceptance Criteria**

- AC-504.1: `adapter.set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE, coder_behavior=MockCoderBehavior.GENERATE_SIMPLE)` is callable and configures both roles in one call.
- AC-504.2: `adapter.set_behavior_mode()` with no args uses defaults (ALWAYS_APPROVE + GENERATE_SIMPLE).
- AC-504.3: Calling the old positional form `set_behavior_mode("coder", "generate_simple")` raises TypeError.
- AC-504.4: `GENERATE_SIMPLE` artifact_content is exactly `"def hello():\n    return \"hello world\"\n"`.
- AC-504.5: `GENERATE_WITH_BUG` artifact_content is exactly `"def hello():\n    return undefined_var\n"`.
- AC-504.6: tester and integrator roles are auto-configured with the specified structured responses.
- AC-504.7: All call sites in test files updated to new signature; 381+ tests pass.

**R4 Reference**: This REQ supersedes R4 REQ-001 (set_behavior_mode dual-parameter signature).

**Impact Scope**

| File | Change |
|------|--------|
| `05_delivery/statekanban/adapters/mock_adapter.py` | Replace overloaded signature with dual-keyword-parameter signature; fix artifact_content; add tester/integrator auto-configuration |
| `04_testing/test_scripts/test_e2e.py` | Update TC-E2E-01/02/03 to use new signature |
| `04_testing/test_scripts/test_mock_adapter.py` | Update all set_behavior_mode call sites |

---

## REQ-505: E2E Engine.drive() fix -- Use dual-parameter set_behavior_mode in all E2E tests

**Description**

R4 REQ-002 required that E2E tests TC-E2E-02/03 use `Engine.drive()` + `set_behavior_mode` with dual parameters. The current implementation calls `set_behavior_mode("coder", "generate_simple")` and `set_behavior_mode("reviewer", "always_reject")` separately, which is a two-call pattern that only works with the overloaded R4 signature. With REQ-504's canonical dual-keyword-parameter signature, all E2E tests must be updated to use the single-call pattern.

Additionally, TC-E2E-01 must be updated from the current single-role call to a proper dual-parameter call.

**Behavior**

1. TC-E2E-01: `adapter.set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_APPROVE, coder_behavior=MockCoderBehavior.GENERATE_SIMPLE)` -- single call sets both roles.
2. TC-E2E-02: `adapter.set_behavior_mode(reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE, coder_behavior=MockCoderBehavior.GENERATE_SIMPLE)` -- collision convergence scenario.
3. TC-E2E-03: `adapter.set_behavior_mode(reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT, coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG)` -- circuit breaker scenario, with `max_rounds=3`.
4. All three tests must assert convergence/non-convergence status as before.
5. TC-E2E-02 must assert that FluidZone contains at least 1 VetoSignal (collision evidence).
6. TC-E2E-03 must assert `result.converged is False` and CrystalZone has no artifacts.

**Acceptance Criteria**

- AC-505.1: TC-E2E-01 uses single `set_behavior_mode(reviewer_behavior=..., coder_behavior=...)` call.
- AC-505.2: TC-E2E-02 uses single call, asserts convergence AND at least 1 VetoSignal in FluidZone.
- AC-505.3: TC-E2E-03 uses single call, asserts non-convergence AND no artifacts in CrystalZone.
- AC-505.4: All E2E tests are driven by `Engine.drive()`, not manual signal construction.
- AC-505.5: All 381+ tests pass after updates.

**R4 Reference**: This REQ supersedes R4 REQ-002 (E2E tests driven by Engine.drive()).

**Impact Scope**

| File | Change |
|------|--------|
| `04_testing/test_scripts/test_e2e.py` | Rewrite TC-E2E-01/02/03 to use dual-parameter set_behavior_mode |
| `04_testing/test_scripts/test_mock_adapter.py` | Update any remaining single-role calls |

---

## Technical Constraints

1. **Python 3.11+**, `black` formatting, `pytest` testing framework
2. **No core module interface changes** beyond the specified REQs (Config, MockLLMAdapter, Engine)
3. **Backward compatibility**: `Config()` with no `project_root` must behave identically to R4
4. **Breaking change**: REQ-504 removes the overloaded `set_behavior_mode(role, mode)` calling convention -- all call sites must be updated
5. **Error code system**: SK_XX_NNN (see `core/errors.py`)
6. **Test stability**: All 381+ existing tests must pass after changes

---

## Acceptance Criteria (Overall)

1. All tests pass (381+ + new), no skip, no xfail
2. `Config(project_root="/tmp/x")` sets project_root; `Config()` defaults to empty string
3. `statekanban drive "intent" --project-root /tmp/x` propagates project_root into Config
4. `set_behavior_mode(reviewer_behavior=..., coder_behavior=...)` dual-keyword-parameter signature is the only supported calling convention
5. E2E tests TC-E2E-01/02/03 use single dual-parameter `set_behavior_mode` call, driven by `Engine.drive()`

---

## Deliverable Summary

| # | File | Operation | REQ |
|---|------|-----------|-----|
| 1 | `05_delivery/statekanban/config.py` | Modify | REQ-501 |
| 2 | `05_delivery/statekanban/cli/main.py` | Modify | REQ-502 |
| 3 | `05_delivery/statekanban/engine/engine.py` | Modify | REQ-503 |
| 4 | `05_delivery/statekanban/core/valve.py` | Modify | REQ-503 |
| 5 | `05_delivery/statekanban/snapshot.py` | Modify | REQ-503 |
| 6 | `05_delivery/statekanban/adapters/mock_adapter.py` | Modify | REQ-504 |
| 7 | `04_testing/test_scripts/test_e2e.py` | Modify | REQ-505 |
| 8 | `04_testing/test_scripts/test_mock_adapter.py` | Modify | REQ-504/505 |
