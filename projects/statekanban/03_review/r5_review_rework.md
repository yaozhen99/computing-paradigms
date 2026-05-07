# R5 Rework Verification

**Reviewer**: reviewer (automated)
**Date**: 2026-05-07
**Round**: R5 rework verification
**Input**: r5_review.md (issues M1, m1-m4), 05_delivery/statekanban/, 04_testing/test_scripts/

---

## Verification Results

### M1 (Major): config.py duplicate method definitions

**Status**: FIXED

**Evidence**:
- `05_delivery/statekanban/config.py` contains exactly one `from_dict` definition (lines 72-85) and one `to_dict` definition (lines 87-91).
- The retained `from_dict` correctly handles unknown keys: it filters known keys from input, builds an `extra` dict from unknown keys, and merges with pre-existing extra via `config.extra = {**config.extra, **extra}` (line 84).
- The retained `to_dict` uses `dataclasses.asdict(self)` which is the correct and complete serialization.
- No dead code, no conflicting logic.

---

### m1 (Minor): CLI error message wording

**Status**: FIXED

**Evidence**:
- `cli/main.py` line 134: `print(f"Project root does not exist: {resolved}")`
- Matches AC-502.4 specification exactly: "Project root does not exist: <path>"

---

### m2 (Minor): E2E VetoSignal assertion weak fallback

**Status**: FIXED

**Evidence**:
- `test_e2e.py` lines 194-198 (TC-E2E-02):
  ```python
  all_signals = kanban.fluid.read_signals()
  veto_signals = [s for s in all_signals if s.signal_type == SignalType.VETO]
  assert len(veto_signals) >= 1, \
      "Expected at least 1 VetoSignal in FluidZone for collision convergence scenario"
  ```
- No weak fallback path. The assertion is hard -- it will fail with a descriptive message if no VetoSignal is found in FluidZone.
- `engine.py` `_call_llm_for_role()` ToolRegistry response unwrapping (lines 352-373) correctly handles the nested `output["output"]` structure with proper fallback chain.

---

### m3 (Minor): project_root null-byte validation

**Status**: FIXED

**Evidence**:
- `config.py` `resolve_path()` lines 65-66:
  ```python
  if "\x00" in relative_path:
      raise ValueError("Path contains null bytes")
  ```
- `cli/main.py` `cmd_drive()` lines 129-131:
  ```python
  if "\x00" in args.project_root:
      print("Error: --project-root contains null bytes", file=sys.stderr)
      return 1
  ```
- Both entry points validate null bytes before path operations.

---

### m4 (Minor): SnapshotManager.list_snapshots() uses project_root

**Status**: FIXED

**Evidence**:
- `snapshot.py` lines 167-174:
  ```python
  def list_snapshots(self) -> list[str]:
      resolved_base = self._resolve_path("")
      return list_snapshots(resolved_base)
  ```
- `list_snapshots()` now uses `self._resolve_path("")` which resolves `base_dir` against `project_root` (falling back to `os.getcwd()` when project_root is empty), consistent with `save_snapshot`, `load_snapshot`, and `delete_snapshot`.

---

## Test Results

```
404 passed, 3 skipped, 0 failures
```

- 3 skipped: `test_live_api.py` (gated by `--run-live`, by design)
- 0 xfail
- 1 DeprecationWarning: `asyncio.iscoroutinefunction` in `test_codex_adapter.py` (advisory, not blocking)

---

## Final Verdict

**PASS**

All 5 issues from the R5 review have been fully fixed:
- M1: Duplicate method definitions removed from config.py
- m1: CLI error message matches AC-502.4 specification
- m2: E2E VetoSignal assertion has no weak fallback
- m3: Null-byte validation added to both config.py and cli/main.py
- m4: SnapshotManager.list_snapshots() correctly uses _resolve_path()

All 404 tests pass with 3 expected skips (live API gated tests).
