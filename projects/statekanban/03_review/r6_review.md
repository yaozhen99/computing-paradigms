# R6 Code Review

**Reviewer**: reviewer
**Date**: 2026-05-07
**Round**: R6 (Virtual Project Root + Path Sandbox)
**Input**: r6_requirements.md (5 REQ: 601-605), r6_design.md, 05_delivery/statekanban/, 04_testing/
**Test Results**: 500 passed, 3 skipped (live_api gated), 0 failed

---

## Summary

R6 delivers 5 REQs that introduce a VirtualProjectRoot abstraction, path traversal protection via PathEscapeError, snapshot isolation, valve path contract enforcement, and CLI path validation. The core architecture is sound and faithful to the design. However, several implementation gaps remain: the most serious are a missing `import tempfile` that crashes snapshot operations, `read_file` lacking any path sandbox, and two key call sites (`cli/main.py` and `e2e_helpers.py`) passing `project_root=...` instead of `config=...` to OutputValve, which bypasses the newly built traversal guard entirely.

**Total findings**: 12
- Critical: 2
- Major: 4
- Minor: 3
- Advisory: 3

**Verdict**: **CONDITIONAL_PASS** -- requires 2 Critical fixes before clearance.

---

## Issues Found

### Critical

#### C-1: snapshot.py missing `import tempfile` (BUG-1 confirmed)

**File**: `05_delivery/statekanban/snapshot.py`, top-of-file imports section

**Description**: The `_save_snapshot_atomic()` helper (line 247) calls `tempfile.mkstemp()` but the `tempfile` module is never imported. This causes `NameError: name 'tempfile' is not defined` on every snapshot save attempt. The conftest.py hotfix injects `tempfile` into the module namespace at import time, masking the bug in tests, but the production code is broken without this patch.

**Impact**: Runtime crash on a primary feature path (snapshot save). REQ-603 is non-functional in production without the hotfix.

**Fix**: Add `import tempfile` to the module-level imports in `snapshot.py` (after `import json`).

**Severity rationale**: Runtime NameError on a core feature. The conftest hotfix is a test-only workaround and must not be relied upon for production correctness.

---

#### C-2: read_file tool has no path sandbox (BUG-4 confirmed)

**File**: `05_delivery/statekanban/tools/read_file.py`

**Description**: The `read_file()` function opens any path without validation. It does `open(path, "r", encoding="utf-8")` directly. No null-byte check, no traversal check, no `config.resolve_path()` call. This means `read_file("../../etc/passwd")` would succeed, providing arbitrary file read capability. This directly contradicts REQ-605's isolation goal of eliminating all 5 path leaks -- leak #3 (read_file unguarded) remains unfixed.

**Impact**: Security vulnerability. Arbitrary file read. A state or tool output containing a traversal path would exfiltrate files outside the project root.

**Fix**: Add `config: Config | None = None` parameter to `read_file()`. When `config` is provided, resolve the path via `config.resolve_path(path)` before opening. When `config` is None, fall back to direct read (backward compat) but log a warning about unvalidated path access. Also add null-byte check (`\x00 in path`).

**Severity rationale**: Direct security vulnerability + design non-conformance (5th leak not fixed).

---

### Major

#### M-1: cli/main.py and e2e_helpers.py pass `project_root` instead of `config` to OutputValve

**Files**: `05_delivery/statekanban/cli/main.py` line 145, `05_delivery/statekanban/testing/e2e_helpers.py` line 234

**Description**: Both call sites construct OutputValve as:
```python
valve = OutputValve(kanban=kanban, project_root=config.project_root)
```
This passes the deprecated `project_root` string parameter, NOT the new `config` parameter. When `project_root` is provided but `config` is None, OutputValve falls back to its legacy `_resolve_artifact_path()` which uses `os.path.join(base, artifact_path)` with `os.getcwd()` fallback -- completely bypassing `Config.resolve_path()` and the traversal guard.

The design document (r6_design.md, REQ-604 section) explicitly states that `cmd_drive()` should "Pass `config` to OutputValve". The implementation does not.

**Impact**: In the CLI and E2E paths, artifact writes have NO path traversal protection. A `../../etc/evil.py` artifact path would be written outside the project root. This defeats REQ-604's core purpose.

**Fix**: Change both call sites to `OutputValve(kanban=kanban, config=config)`.

**Severity rationale**: The traversal guard (REQ-602/604) is not activated in the primary CLI path. This is a functional regression from the design intent.

---

#### M-2: SnapshotManager._ensure_gitignore() not called from save_snapshot (BUG-2)

**File**: `05_delivery/statekanban/snapshot.py`

**Description**: The `_ensure_gitignore()` method exists (lines 219-239) but is never invoked from `save_snapshot()` or any other method. AC-603.5 specifies that `.gitignore` should be auto-created when the `.statekanban/` directory is created. The method is only reachable via explicit manual call, not lazily on first save.

**Impact**: Snapshot directories created by `save_snapshot` will not contain `.gitignore`, meaning snapshots could be tracked by git if the project root is inside a repository. Data hygiene gap.

**Fix**: Call `self._ensure_gitignore()` at the start of `save_snapshot()` (before the atomic write, after the path resolution).

**Severity rationale**: REQ-603 AC-603.5 not satisfied. The .gitignore creation is part of the isolation contract.

---

#### M-3: SnapshotManager traversal guard uses CWD instead of project_root in legacy path (BUG-3 partial)

**File**: `05_delivery/statekanban/snapshot.py`, line 215

**Description**: In `_resolve_path()` when `config is None` (legacy fallback), the code uses:
```python
base = self._project_root if self._project_root else os.getcwd()
```
When `SnapshotManager(project_root="/some/path")` is constructed without config, `_project_root` is set correctly. But the docstring and TesterRun BUG-3 report note that the traversal guard in `_resolve_path` only applies when `config is not None`. In the legacy path, there is no traversal guard at all -- the `os.getcwd()` fallback (or even `project_root`) does not prevent `../../etc/passwd` escapes because the legacy code just does `os.path.join(effective_base, path)` without any boundary check.

**Impact**: When SnapshotManager is used without config (backward compat mode), traversal paths are not blocked. This is a gap in the isolation guarantee.

**Fix**: For the legacy path, add a basic traversal check: if `os.path.abspath(result)` does not start with `os.path.abspath(effective_base)`, raise an error. Alternatively, encourage all call sites to pass `config` instead of `project_root`.

**Severity rationale**: Isolation guarantee only works when `config` is passed. Legacy path has no protection.

---

#### M-4: call_llm.py lacks timeout enforcement and graceful degradation

**File**: `05_delivery/statekanban/tools/call_llm.py`

**Description**: The design (r6_design.md) and TesterRun (AC4 PARTIAL) note that `CallLlmTool` should have `timeout=30.0`, `max_retries=2`, and `_fallback_response()`. The current implementation has no timeout parameter on the adapter call, no retry logic, and no degradation strategy. On failure, it returns a hard-error dict (`{"success": False, "error": str(exc)}`). The generic `except Exception` catch at line 115 does not distinguish between timeout, rate-limit, auth error, and parse error -- all get the same error code `SK_LLM_001`.

**Impact**: LLM calls can hang indefinitely. No graceful degradation on transient failures. All error types are lumped together, making it impossible for downstream logic to distinguish timeout from auth failure.

**Fix**: (1) Add `timeout` parameter to `CallLlmTool.__init__` and pass it to `adapter.complete()`. (2) Catch `anthropic.APITimeoutError` (or equivalent) specifically before the generic catch. (3) Implement `_fallback_response()` that returns a structured degradation signal rather than a hard error.

**Severity rationale**: REQ coverage gap (AC4 PARTIAL per TesterRun) + operational robustness.

---

### Minor

#### m-1: VirtualProjectRoot.resolve() uses Path.cwd() for CWD fallback, not os.getcwd()

**File**: `05_delivery/statekanban/config.py`, line 80

**Description**: `VirtualProjectRoot.resolve()` uses `Path.cwd()` when root is None. The design doc (r6_design.md) states that `os.getcwd()` should only appear in `cli/validate.py`. While `Path.cwd()` is semantically equivalent to `os.getcwd()`, it is technically a different API. The requirement says "os.getcwd() 仅允许出现在 cli/validate.py" which could be interpreted as also prohibiting `Path.cwd()`. However, `Path.cwd()` is the idiomatic pathlib API and is acceptable.

**Impact**: No functional impact. The spirit of the requirement (single CWD resolution point) is preserved.

**Recommendation**: Accept as-is. `Path.cwd()` is the correct API for pathlib-based code. If strict interpretation is needed, document that `Path.cwd()` inside `VirtualProjectRoot` is the authorized CWD resolution point alongside `cli/validate.py`.

---

#### m-2: Null-byte check in resolve_path uses string containment, not pathlib

**File**: `05_delivery/statekanban/config.py`, lines 67 and 205

**Description**: The null-byte check is `"\x00" in relative_path` (string containment). This is correct and efficient. However, `Path()` objects do not naturally contain null bytes (they would raise on construction). The check happens before the `Path()` construction, which is the right order. But it means the check is redundant for absolute-path paths that are passed as `str` -- `Path(relative_path)` would fail anyway for null bytes in some Python versions. The check is good defense-in-depth regardless.

**Impact**: No functional impact. The check is correct defense-in-depth.

**Recommendation**: Accept as-is. Defense-in-depth is good practice.

---

#### m-3: _ensure_gitignore() uses os.path.exists check before write (TOCTOU)

**File**: `05_delivery/statekanban/snapshot.py`, lines 232-238

**Description**: `_ensure_gitignore()` checks `if not os.path.exists(gitignore_path)` before creating the directory and writing the file. This is a TOCTOU (Time-Of-Check-Time-Of-Use) pattern per the CiviBBS anti-patterns rules: "不准先 exists() 再操作，必须直接操作+捕获异常." The gitignore creation should just attempt the write and catch `FileExistsError` (or use `exist_ok=True` on `os.makedirs` which is already done).

**Impact**: Low. The .gitignore content is `*\n` which is idempotent -- overwriting is harmless. But it violates the project's own anti-pattern rules.

**Recommendation**: Remove the `os.path.exists()` check and just attempt the write. If the file already exists, the overwrite is harmless (content is deterministic). Alternatively, open with mode `"x"` (exclusive create) and catch `FileExistsError`.

---

### Advisory

#### A-1: No test for symlink-based path traversal

**Observation**: The test suite validates `..` traversal and null bytes but does not test symlink-based escapes. Given that `Path.resolve()` follows symlinks and the design notes "symbol link escape caught by is_relative_to check," a test verifying this claim would provide regression protection. Platform-dependent (Windows symlinks require privilege), so may need `@pytest.mark.skipif`.

**Recommendation**: Add a symlink traversal test as `@pytest.mark.skipif` with a condition that checks symlink capability.

---

#### A-2: OutputValve._resolve_artifact_path retains os.getcwd() fallback

**File**: `05_delivery/statekanban/core/valve.py`, line 268

**Observation**: When `config` is None, `_resolve_artifact_path` falls back to `os.getcwd()`. This is intentional backward compatibility per the design. But combined with M-1 (call sites not passing config), this means the fallback is the active path in production. After M-1 is fixed, this fallback becomes dead code for production paths. No action needed now, but consider deprecating the `project_root` parameter in a future round.

---

#### A-3: validate_project_root uses Path.resolve() for relative-to-absolute, not os.getcwd()

**File**: `05_delivery/statekanban/cli/validate.py`, line 74

**Observation**: The design specifies that relative-to-absolute conversion should use `os.getcwd()` (AC-605.2 says "based on os.getcwd() 解析"). The implementation uses `Path(path_str).resolve()` which internally calls `os.getcwd()` on Python 3.11+. This is correct behavior -- `Path.resolve()` is the idiomatic API. The design wording is slightly misleading but the behavior matches.

**Recommendation**: Accept as-is. `Path.resolve()` is the correct modern API and internally uses CWD resolution.

---

## REQ Coverage Assessment

### REQ-601: VirtualProjectRoot
**Status**: IMPLEMENTED

- AC-601.1: `Config.resolve_path()` method exists and delegates to `VirtualProjectRoot.resolve()` -- PASS
- AC-601.2: Absolute paths returned with warning log -- PASS (verified in test_virtual_project_root.py)
- AC-601.3: `os.getcwd()` eliminated from core modules (except authorized locations) -- PASS (only in valve.py fallback, snapshot.py fallback, and VirtualProjectRoot)
- AC-601.4: Path operations use `config.resolve_path()` -- PARTIAL (see M-1: CLI and e2e_helpers don't pass config to Valve)
- AC-601.5: R5 tests pass -- PASS

### REQ-602: Path Traversal Guard
**Status**: IMPLEMENTED

- AC-602.1: `resolve_path("../../etc/passwd")` raises PathEscapeError -- PASS
- AC-602.2: `resolve_path("subdir/../../../etc/passwd")` raises PathEscapeError -- PASS
- AC-602.3: Valid paths resolve normally -- PASS
- AC-602.4: `subdir/../other/file.txt` resolves within root -- PASS
- AC-602.5: PathEscapeError registered as SK_06_001 with attempted_path and project_root -- PASS
- AC-602.6: Uses `Path.is_relative_to()` not string matching -- PASS

### REQ-603: Snapshot Isolation
**Status**: PARTIALLY IMPLEMENTED

- AC-603.1: SnapshotManager accepts `config` parameter -- PASS
- AC-603.2: Different project_root snapshots isolated -- PASS (verified in test_snapshot_isolation.py)
- AC-603.3: Snapshots stored under `project_root/.statekanban/snapshots/` -- PASS
- AC-603.4: Public API signatures unchanged -- PASS
- AC-603.5: `.gitignore` auto-created -- FAIL (see M-2: method exists but not called)

### REQ-604: Valve Path Contract
**Status**: PARTIALLY IMPLEMENTED

- AC-604.1: OutputValve writes resolve via `config.resolve_path()` -- FAIL in CLI/e2e paths (see M-1)
- AC-604.2: Traversal paths raise PathEscapeError -- PASS when config is provided
- AC-604.3: Path contract test file exists -- PASS (test_valve_path_contract.py)
- AC-604.4: OutputValve accepts `config` parameter -- PASS
- AC-604.5: Debug logging of resolved path -- PASS

### REQ-605: CLI Path Validation
**Status**: IMPLEMENTED

- AC-605.1: Null byte detection -- PASS (NullByteError raised)
- AC-605.2: Relative-to-absolute conversion -- PASS (via Path.resolve())
- AC-605.3: Nonexistent path rejected -- PASS (PathNotExistError)
- AC-605.4: File-not-directory rejected -- PASS (PathNotDirectoryError)
- AC-605.5: `validate_project_root()` is a standalone testable function -- PASS
- AC-605.6: Test file exists -- PASS (test_cli_path_validation.py)
- AC-605.7: Validation order: null byte -> normalize -> exist -> directory -- PASS

---

## Isolation Leak Assessment

| Leak | R5 Status | R6 Status | Notes |
|---|---|---|---|
| OutputValve._resolve_output_path | Unguarded | FIXED (config delegation) | But M-1: config not passed in CLI/e2e |
| SnapshotManager.save_snapshot | Unguarded | FIXED (config delegation) | |
| read_file tool | Unguarded | **NOT FIXED** | See C-2 |
| write_file tool | Unguarded | FIXED (delegates to Valve) | |
| search_code tool | Unguarded | FIXED (receives resolved path) | |

**Net result**: 3 of 5 leaks fixed. 1 unfixed (read_file). 1 partially fixed (OutputValve: code is correct but call sites bypass it).

---

## Backward Compatibility Assessment

| Scenario | Expected | Actual | Verdict |
|---|---|---|---|
| `project_root=""` | R5 behavior (CWD fallback) | `resolve_path` falls back to `Path.cwd()` | PASS |
| `config=None` for OutputValve | R5 behavior (project_root or CWD) | Falls back to `_resolve_artifact_path` legacy | PASS |
| `config=None` for SnapshotManager | R5 behavior (project_root or CWD) | Falls back to `_resolve_path` legacy | PASS |
| Existing 381 R5 tests | All pass | 500 passed (381 legacy + 119 new) | PASS |

Backward compatibility is preserved at the API level. The conftest hotfix for BUG-1 is a test-side workaround and does not affect production backward compat.

---

## TesterRun Bug Assessment

| Bug | TesterRun Severity | Reviewer Severity | Agreement | Notes |
|---|---|---|---|---|
| BUG-1: missing import tempfile | High | **Critical** | Upgrade | Runtime NameError on primary feature; conftest hotfix masks it in tests |
| BUG-2: _ensure_gitignore not called | Low | **Major** | Upgrade | AC-603.5 explicitly specified, not a cosmetic gap |
| BUG-3: SnapshotManager uses CWD not project_root | Medium | **Major** | Same tier | Isolation correctness undermined in legacy path |
| BUG-4: read_file no sandbox | High | **Critical** | Agree | Direct security vulnerability |

I agree with TesterRun's severity for BUG-4. For BUG-1, I upgrade from High to Critical because the missing import causes a hard crash (NameError), not just a functional failure -- and the hotfix is test-only, not production-ready. For BUG-2, I upgrade from Low to Major because AC-603.5 is an explicit acceptance criterion, not an optional nice-to-have. BUG-3 severity is consistent between TesterRun (Medium) and this review (Major) -- both recognize it undermines isolation correctness.

---

## Acceptance Criteria Assessment

| Criterion | Status | Notes |
|---|---|---|
| All tests pass (500, no skip/xfail) | PARTIAL | 3 skipped (live_api gated), BUG-1 masked by conftest hotfix |
| resolve_path blocks traversal with SK_06_001 | PASS | Verified via test_virtual_project_root.py |
| OutputValve writes via resolve_path | PARTIAL | Code supports it but CLI/e2e don't pass config (M-1) |
| read_file sandboxed | FAIL | No sandbox at all (C-2) |
| SK_06_001 registered in errors.py | PASS | PathEscapeError with error_code SK_06_001 |
| os.getcwd() only in authorized locations | PASS | Only in valve.py/snapshot.py fallback paths and VirtualProjectRoot |

---

## Verdict

### CONDITIONAL_PASS

R6 passes conditionally on fixing the 2 Critical issues:

1. **C-1**: Add `import tempfile` to `snapshot.py` -- single line fix
2. **C-2**: Add path sandbox to `tools/read_file.py` -- accept `config` parameter, call `resolve_path`, add null-byte check

Additionally, **M-1** (passing `config` instead of `project_root` to OutputValve in CLI/e2e_helpers) should be treated as effectively Critical for the traversal guard to function in production paths, though it is formally Major because the Valve code itself is correct.

**Recommended post-R6 actions**:
- Fix M-1 (change `OutputValve(project_root=...)` to `OutputValve(config=...)`)
- Fix M-2 (call `_ensure_gitignore()` in `save_snapshot`)
- Fix M-4 (add timeout/degradation to call_llm)
- Add symlink traversal test (A-1)
- Deprecate `project_root` parameter on OutputValve/SnapshotManager in future round (A-2)