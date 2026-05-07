# R6 Rework Verification

**Reviewer**: reviewer
**Date**: 2026-05-07
**Round**: R6 Rework Verification
**Input**: r6_review.md (12 findings: 2 Critical, 4 Major, 3 Minor, 3 Advisory), 05_delivery/statekanban/ (reworked code), 04_testing/
**Test Results**: 500 passed, 3 skipped (live_api gated), 0 failed

---

## Summary

Backend has reworked all 6 items (M1, M2, m1-m6) from the rework request. All testable fixes are verified in code and confirmed by the test suite. One naming discrepancy: `ToolPathViolationError` was expected per the review checklist but the implementation uses `PathEscapeError` with `SK_TR_005` error code in a dict-return pattern -- functionally equivalent but not a distinct exception class.

**Verdict**: **PASS**

---

## Issue-by-Issue Verification

### Major

#### M1: read_file tool path sandbox + ToolPathViolationError

**Status**: **FIXED** (with naming note)

**Evidence**:
- `read_file()` now accepts `config: Any | None = None` parameter (line 22-23)
- When config is provided, calls `config.resolve_path(path)` with exception catch (lines 53-64)
- Null-byte check always runs, even without config (line 45-50)
- Symlink normalization via `os.path.realpath()` after resolve (line 66)
- Post-resolve `is_relative_to` check against `project_root` (lines 67-77)
- Without config, logs warning about unvalidated path access (line 80)
- Error code `SK_TR_005` used consistently for all path violations

**Note**: The review checklist asked "是否有 ToolPathViolationError?" -- there is no exception class named `ToolPathViolationError` in the codebase. The original R6 review (C-2) specified adding a `config` parameter to `read_file()` and using `config.resolve_path()`, which the implementation follows. The path violation is signaled via `SK_TR_005` error code in the return dict, not via a dedicated exception. This is consistent with the tool's async dict-return contract. The `PathEscapeError` class exists for `config.resolve_path()` throws, and `read_file` catches those and converts to dict returns. **Functionally equivalent**; the missing class name is cosmetic.

---

#### M2: SnapshotManager._resolve_path traversal guard uses project_root

**Status**: **FIXED**

**Evidence**:
- `_resolve_path()` legacy path (when `config is None`) now has traversal guard (lines 222-233)
- When `self._project_root` is set, computes `abs_result = os.path.abspath(result)` and `abs_root = os.path.abspath(self._project_root)`
- Uses `Path(abs_result).is_relative_to(Path(abs_root))` for boundary check
- Raises `PathEscapeError` with `attempted_path` and `project_root` on escape
- When `config` is provided, delegates to `config.resolve_path()` which has its own guard

The legacy path traversal guard now correctly uses `project_root` (not CWD) as the boundary, addressing BUG-3.

---

### Minor

#### m1: snapshot.py has import tempfile

**Status**: **FIXED**

**Evidence**: `import tempfile` present at line 19 of `snapshot.py`. This directly fixes C-1 from the original review. The conftest.py hotfix (lines 20-22) still exists but is now defensive -- it checks `if not hasattr(_snapshot_mod, 'tempfile')` which will be False since the module now has the import, making the hotfix a no-op.

---

#### m2: save_snapshot calls _ensure_gitignore

**Status**: **FIXED**

**Evidence**: `save_snapshot()` method (line 159-161) calls `self._ensure_gitignore()` before `_save_snapshot_atomic()`. This directly fixes M-2 from the original review. The `.gitignore` will be created on every snapshot save attempt.

---

#### m3: validate.py error messages are consistent

**Status**: **FIXED**

**Evidence**: All three error classes use a consistent message pattern:
- `NullByteError`: `f"Path validation error [null byte]: {path!r}"`
- `PathNotExistError`: `f"Path validation error [not exist]: {path!r}"`
- `PathNotDirectoryError`: `f"Path validation error [not directory]: {path!r}"`

All follow `Path validation error [category]: {path!r}` with consistent formatting.

---

#### m4: VirtualProjectRoot.__repr__ includes project_root

**Status**: **FIXED**

**Evidence**: `__repr__` method (config.py line 106-109) returns:
```python
f"VirtualProjectRoot(root={root_repr!r})"
```
Where `root_repr` is `str(self._root)` when set, or `"CWD"` when None. The `project_root` value is clearly visible in the representation.

---

#### m5: test_valve_path_contract assertions strengthened

**Status**: **FIXED**

**Evidence**: Multiple strengthened assertions added:
- `test_resolve_delegates_to_config_resolve_path` (line 103): `assert Path(result).is_relative_to(Path(tmp_dir).resolve())`
- `test_normal_path_write_succeeds` (line 144): `assert Path(result.artifact_path).is_relative_to(Path(tmp_dir).resolve())`
- `test_escape_path_write_blocked` (lines 159-160): asserts `attempted_path` and `project_root` on the exception
- `test_absolute_path_write_succeeds_with_warning` (line 178): `assert os.path.exists(abs_output)`
- `test_nested_path_write_succeeds` (line 193): `assert Path(result.artifact_path).is_relative_to(Path(tmp_dir).resolve())`

Assertions now verify both the path boundary and actual file existence, not just success/failure.

---

#### m6: cli/validate.py has type annotations

**Status**: **FIXED**

**Evidence**: All functions and methods have full type annotations:
- `def __init__(self, message: str) -> None:`
- `def __init__(self, path: str) -> None:`
- `def validate_project_root(path_str: str) -> Path:`
- `exit_code: int = 1/2/3/4`
- `self.message: str`
- `self.path: str`

---

## Original Review Critical Issues (C-1, C-2) Status

Although the rework task focused on M1/M2/m1-m6, the two Critical issues from r6_review.md are now resolved:

| Original Issue | Description | Rework Status |
|---|---|---|
| C-1 | snapshot.py missing `import tempfile` | **FIXED** (m1) |
| C-2 | read_file has no path sandbox | **FIXED** (M1) |

---

## Original Review Major Issues (M-1, M-4) Status

These were not in the rework task but are worth noting:

| Original Issue | Description | Status |
|---|---|---|
| M-1 | cli/main.py and e2e_helpers.py pass `project_root` instead of `config` to OutputValve | **FIXED** -- both now pass `config=config` to OutputValve (cli/main.py line 145, e2e_helpers.py line 234) |
| M-4 | call_llm.py lacks timeout/retry/degradation | **NOT FIXED** -- not part of rework scope |

---

## Test Suite Results

```
500 passed, 3 skipped (live_api gated), 0 failed, 1 warning (deprecation)
```

No regressions. All R5 legacy tests still pass.

---

## Final Verdict

**PASS**

All 6 rework items (M1, M2, m1-m6) are verified as FIXED. The two Critical issues from the original review (C-1, C-2) are also resolved. The M-1 issue (passing config instead of project_root to OutputValve) is also fixed. M-4 (call_llm timeout) was not in rework scope and remains open.

The `ToolPathViolationError` naming discrepancy is noted: the implementation uses `PathEscapeError` with `SK_TR_005` error code in a dict-return pattern, which is functionally equivalent to a dedicated exception class for the `read_file` tool's contract. This is acceptable given that tools return error dicts, not raise exceptions.
