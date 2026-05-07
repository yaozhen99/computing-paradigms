# R6 Architecture Design: VirtualProjectRoot Isolation Hardening

**Round**: R6
**Architect**: Claude (architect role)
**Date**: 2026-05-07
**Input**: `01_requirements/r6_requirements.md` (5 REQ: 601-605)
**Base code**: `05_delivery/statekanban/` (R5, 407 tests passing)

---

## Overview

R6 hardens the path layer by introducing a `VirtualProjectRoot` abstraction in `Config`, adding path-traversal guards to `resolve_path()`, isolating snapshot storage per project root, enforcing a path contract on OutputValve writes, and adding a full CLI path-validation chain. The design preserves backward compatibility: all new parameters default to values that reproduce R5 behavior (empty `project_root` falls back to CWD; no traversal guard triggers on valid paths).

### Key Design Decisions

1. **VirtualProjectRoot is a thin wrapper**, not a heavy abstraction. It wraps `Path` and exposes `resolve()`, `is_within()`, and serialization methods. Config holds a `VirtualProjectRoot` instance instead of a bare `str`, but the `project_root` string field is retained for backward compatibility and delegated to the wrapper.

2. **Path traversal detection uses `Path.is_relative_to()`** (Python 3.9+), not string matching. This handles symlinks correctly when combined with `Path.resolve()`.

3. **OutputValve delegates to `Config.resolve_path()`** instead of maintaining its own `_resolve_artifact_path()`. This eliminates the three redundant `os.getcwd()` fallback points (Config, Valve, Snapshot) and converges on a single resolution entry point.

4. **SnapshotManager accepts `Config`** instead of bare `project_root: str`. This gives it access to `resolve_path()` with traversal guards.

5. **CLI validation is extracted to `cli/validate.py`** as a pure function, testable independently of argparse.

---

## REQ-601: VirtualProjectRoot -- Path Resolution Unified Abstraction

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `config.py` | `VirtualProjectRoot` (new class) | New |
| `config.py` | `Config` | Add `vpr` property, refactor `resolve_path()` |
| `engine/engine.py` | `Engine.__init__()` | Use `config.resolve_path()` (already done in R5) |
| `core/valve.py` | `OutputValve.__init__()` | Add `config` parameter, delegate to `config.resolve_path()` |
| `snapshot.py` | `SnapshotManager.__init__()` | Accept `config` instead of `project_root` |
| `tools/read_file.py` | `read_file()` | No change (reads, doesn't resolve paths) |
| `tools/write_file.py` | `write_file()` | No change (delegates to OutputValve) |
| `tools/search_code.py` | `search_code()` | No change (receives resolved path from caller) |
| `cli/main.py` | `cmd_drive()` | Pass `config` to OutputValve and SnapshotManager |

### Interface Changes

#### VirtualProjectRoot (new class)

```python
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class VirtualProjectRoot:
    """Encapsulates project_root path semantics.

    All path resolution in StateKanban flows through this class
    via Config.resolve_path(). No module should call os.getcwd()
    or manually join paths against project_root.

    Attributes:
        root: Absolute Path of the project root directory.
              None means "fall back to CWD at resolution time".
    """

    def __init__(self, root: str | Path | None = None) -> None:
        """
        Args:
            root: Project root path. None or empty string means CWD fallback.
                  Relative paths are resolved to absolute at construction time.
        """
        if root is None or root == "":
            self._root: Path | None = None
        else:
            self._root = Path(root).resolve()

    @property
    def root(self) -> Path | None:
        """The absolute project root Path, or None for CWD fallback."""
        return self._root

    @property
    def is_set(self) -> bool:
        """True if an explicit project_root was provided (not CWD fallback)."""
        return self._root is not None

    def resolve(self, relative_path: str = "") -> Path:
        """Resolve a path relative to this project root.

        If relative_path is absolute, return it as-is (with warning log).
        If project_root is None, fall back to os.getcwd().

        Args:
            relative_path: Path to resolve.

        Returns:
            Absolute Path resolved against project_root (or CWD).

        Raises:
            ValueError: If relative_path contains null bytes.
        """
        if "\x00" in relative_path:
            raise ValueError("Path contains null bytes")

        path = Path(relative_path)

        if path.is_absolute():
            logger.warning(
                "resolve_path received absolute path: %s (project_root=%s)",
                relative_path,
                self._root,
            )
            return path

        base = self._root if self._root is not None else Path.cwd()
        return base / relative_path

    def is_within(self, path: Path) -> bool:
        """Check whether a resolved path is within this project root.

        Uses Path.is_relative_to() for robust prefix checking.

        Args:
            path: Absolute path to check.

        Returns:
            True if path is within project_root.
            Always True if project_root is None (CWD fallback, no sandbox).
        """
        if self._root is None:
            return True  # CWD fallback: no sandbox constraint
        try:
            return path.resolve().is_relative_to(self._root)
        except ValueError:
            return False

    def to_dict(self) -> dict[str, str | None]:
        """Serialize to dict for Config.to_dict()."""
        return {"root": str(self._root) if self._root is not None else None}

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> VirtualProjectRoot:
        """Deserialize from dict for Config.from_dict()."""
        return cls(root=data.get("root"))
```

#### Config changes

```python
@dataclass
class Config:
    # ... existing fields ...

    # REQ-501: Project space root (backward compat)
    project_root: str = ""  # empty string => os.getcwd() at resolution time

    # REQ-601: VirtualProjectRoot instance (derived from project_root)
    # Not a dataclass field -- computed property

    @property
    def vpr(self) -> VirtualProjectRoot:
        """Lazy-initialized VirtualProjectRoot derived from project_root."""
        if not hasattr(self, "_vpr") or self._vpr is None:
            self._vpr = VirtualProjectRoot(
                root=self.project_root if self.project_root else None
            )
        return self._vpr

    def resolve_path(self, relative_path: str) -> str:
        """Resolve a path relative to project_root.

        REQ-601: Delegates to VirtualProjectRoot.resolve().
        REQ-602: Adds path traversal guard (see REQ-602 section).

        Args:
            relative_path: Path to resolve (typically relative).

        Returns:
            Absolute path resolved against project_root (or CWD).

        Raises:
            ValueError: If relative_path contains null bytes.
            PathEscapeError: If resolved path escapes project_root (REQ-602).
        """
        resolved = self.vpr.resolve(relative_path)
        # REQ-602 guard applied here (see REQ-602 section)
        # ...
        return str(resolved)
```

**VPR invalidation on project_root mutation**: When `config.project_root` is set directly, the cached `_vpr` must be invalidated. Two approaches:

- **Option A** (preferred): Override `__setattr__` in Config to clear `_vpr` when `project_root` changes.
- **Option B**: Make `_vpr` a `@cached_property` and delete it on mutation.

```python
def __setattr__(self, name: str, value: Any) -> None:
    super().__setattr__(name, value)
    if name == "project_root":
        # Invalidate cached VPR when project_root changes
        object.__setattr__(self, "_vpr", None)
```

### Data Flow

```
Config(project_root="/tmp/sk_project")
    |
    v  config.vpr -> VirtualProjectRoot(root="/tmp/sk_project")
    |
    v  config.resolve_path("output.py")
    |-- vpr.resolve("output.py")
    |-- = Path("/tmp/sk_project") / "output.py"
    |-- = Path("/tmp/sk_project/output.py")
    |
    v  str(resolved) = "/tmp/sk_project/output.py"


Config(project_root="")
    |
    v  config.vpr -> VirtualProjectRoot(root=None)
    |
    v  config.resolve_path("output.py")
    |-- vpr.resolve("output.py")
    |-- base = Path.cwd()  (CWD fallback)
    |-- = Path.cwd() / "output.py"
    |
    v  str(resolved) = "/current/working/dir/output.py"
```

### os.getcwd() Elimination Audit

Current R5 `os.getcwd()` call sites (3 locations):

| File | Method | Current Usage | R6 Replacement |
|------|--------|---------------|----------------|
| `config.py:69` | `Config.resolve_path()` | `os.getcwd()` fallback | Delegated to `VirtualProjectRoot.resolve()` which uses `Path.cwd()` |
| `core/valve.py:247` | `OutputValve._resolve_artifact_path()` | `os.getcwd()` fallback | **Eliminated**: Valve delegates to `config.resolve_path()` |
| `snapshot.py:199` | `SnapshotManager._resolve_path()` | `os.getcwd()` fallback | **Eliminated**: Snapshot delegates to `config.resolve_path()` |

After R6:
- `os.getcwd()` / `Path.cwd()` appears only inside `VirtualProjectRoot.resolve()` (for CWD fallback).
- `OutputValve._resolve_artifact_path()` is removed; Valve uses `self._config.resolve_path()`.
- `SnapshotManager._resolve_path()` is removed; Snapshot uses `self._config.resolve_path()`.

### Compatibility Analysis

- **Config.project_root**: The `str` field is retained. Existing code that reads/writes `config.project_root` still works. The VPR is a lazy-derived property, not a stored field.
- **Config.from_dict / to_dict**: `project_root` is already a dataclass field; `from_dict({"project_root": "/tmp/x"})` works. VPR is derived on access, not stored.
- **OutputValve**: New `config` parameter defaults to `None`. When `config=None` and `project_root=""`, behavior is identical to R5 (CWD fallback). When `config` is provided, `_resolve_artifact_path` delegates to it.
- **SnapshotManager**: New `config` parameter defaults to `None`. When `config=None` and `project_root=""`, behavior is identical to R5.
- **Existing 407 tests**: All use default `Config()` (project_root="") or construct with `project_root=""`. No regression.

---

## REQ-602: Path Traversal Guard -- Path Escape Detection

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `config.py` | `Config.resolve_path()` | Add traversal guard after resolution |
| `config.py` | `VirtualProjectRoot.resolve()` | Add optional guard flag |
| `core/errors.py` | `PathEscapeError` (new) | New error class, code SK_06_001 |

### Interface Changes

#### PathEscapeError (new)

```python
class PathEscapeError(StateKanbanError):
    """Resolved path escapes the project root sandbox.

    Error code: SK_06_001
    """

    error_code = "SK_06_001"
    http_analogy = 403

    def __init__(
        self,
        message: str = "",
        *,
        attempted_path: str = "",
        project_root: str = "",
        error_code: str | None = None,
    ) -> None:
        if not message:
            message = (
                f"Path escape detected: '{attempted_path}' "
                f"resolves outside project root '{project_root}'"
            )
        super().__init__(message, error_code=error_code)
        self.attempted_path = attempted_path
        self.project_root = project_root
```

#### Config.resolve_path() with traversal guard

```python
def resolve_path(self, relative_path: str) -> str:
    """Resolve a path relative to project_root with traversal guard.

    REQ-601: Delegates to VirtualProjectRoot.resolve().
    REQ-602: After resolution, checks that the resolved path
             is within project_root. If not, raises PathEscapeError.

    Absolute path inputs bypass the traversal guard (they are
    returned as-is with a warning log, per AC-601.2).

    Args:
        relative_path: Path to resolve (typically relative).

    Returns:
        Absolute path resolved against project_root (or CWD).

    Raises:
        ValueError: If relative_path contains null bytes.
        PathEscapeError: If resolved path escapes project_root.
    """
    if "\x00" in relative_path:
        raise ValueError("Path contains null bytes")

    path = Path(relative_path)

    # Absolute paths: return as-is with warning (AC-601.2)
    if path.is_absolute():
        logger.warning(
            "resolve_path received absolute path: %s (project_root=%s)",
            relative_path,
            self.project_root,
        )
        return str(path)

    # Resolve relative path against project_root (or CWD)
    base = self.vpr.root if self.vpr.is_set else Path.cwd()
    resolved = (base / relative_path).resolve()

    # REQ-602: Traversal guard (AC-602.1, AC-602.2)
    # Only check when project_root is explicitly set (sandbox mode)
    if self.vpr.is_set and not resolved.is_relative_to(self.vpr.root):
        raise PathEscapeError(
            attempted_path=relative_path,
            project_root=str(self.vpr.root),
        )

    return str(resolved)
```

### Key Design Points

1. **`Path.resolve()` normalizes `..` components**. `(base / "../../etc/passwd").resolve()` produces an absolute path outside `base`. The `is_relative_to()` check catches this.

2. **`is_relative_to()` uses path prefix matching**, not string matching. This handles platform-specific separators and normalization.

3. **Traversal guard only fires when `project_root` is explicitly set** (sandbox mode). When `project_root=""` (CWD fallback), no sandbox constraint applies -- this preserves backward compatibility.

4. **AC-602.4**: `resolve_path("subdir/../other/file.txt")` resolves to `project_root / "other/file.txt"` which IS within project_root, so no error. The `Path.resolve()` call normalizes the `..` before the `is_relative_to()` check.

5. **Symlinks**: `Path.resolve()` follows symlinks on most platforms. If a symlink inside project_root points outside, `resolved.is_relative_to(root)` will return `False` because `resolve()` dereferences the symlink. This is the correct security posture -- symlinks that escape the sandbox are caught. The R6 scope explicitly excludes deep symlink resolution, so this behavior is acceptable.

### Data Flow

```
resolve_path("../../etc/passwd")
    |-- base = Path("/tmp/sk_project")
    |-- candidate = base / "../../etc/passwd"
    |-- resolved = candidate.resolve() = Path("/etc/passwd")
    |-- resolved.is_relative_to(base) = False
    |
    v  raise PathEscapeError(attempted_path="../../etc/passwd",
                             project_root="/tmp/sk_project")


resolve_path("subdir/../other/file.txt")
    |-- base = Path("/tmp/sk_project")
    |-- candidate = base / "subdir/../other/file.txt"
    |-- resolved = candidate.resolve() = Path("/tmp/sk_project/other/file.txt")
    |-- resolved.is_relative_to(base) = True
    |
    v  return "/tmp/sk_project/other/file.txt"
```

### Compatibility Analysis

- **No existing R5 test uses traversal paths**: All R5 tests use valid relative paths or absolute paths. No regression.
- **PathEscapeError is new**: Not caught by any existing code. Since it only fires on genuinely escaped paths (which don't occur in valid usage), this is safe.
- **Performance**: `Path.resolve()` is slightly slower than `os.path.join()` because it may hit the filesystem to resolve symlinks. For typical usage (no symlinks), the overhead is negligible.

---

## REQ-603: Snapshot Isolation -- Project-Scoped Snapshot Storage

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `snapshot.py` | `SnapshotManager.__init__()` | Accept `config: Config`, derive storage path |
| `snapshot.py` | `SnapshotManager._resolve_path()` | Delegate to `config.resolve_path()` |
| `snapshot.py` | `SnapshotManager._ensure_gitignore()` | New: auto-create `.gitignore` in `.statekanban/` |
| `engine/engine.py` | `Engine.__init__()` | Pass `config` to `SnapshotManager` |
| `cli/main.py` | `cmd_drive()` | Pass `config` to `SnapshotManager` |
| `testing/e2e_helpers.py` | `_build_engine()` | Pass `config` to `SnapshotManager` |

### Interface Changes

#### SnapshotManager constructor

```python
class SnapshotManager:
    def __init__(
        self,
        base_dir: str = ".statekanban/snapshots",
        project_root: str = "",    # REQ-503: deprecated, use config instead
        config: Config | None = None,  # REQ-603: preferred
    ) -> None:
        """
        Args:
            base_dir: Directory where snapshots are stored (relative to project_root).
            project_root: Project space root (deprecated, use config).
            config: Config instance for path resolution (REQ-603).
        """
        self._base_dir = base_dir
        self._config = config
        # Backward compat: if config not provided, create one from project_root
        if config is not None:
            self._project_root = config.project_root
        else:
            self._project_root = project_root
```

#### SnapshotManager._resolve_path()

```python
def _resolve_path(self, path: str) -> str:
    """Resolve a path relative to project_root + base_dir.

    REQ-603: When config is provided, uses config.resolve_path()
    which includes traversal guard. Otherwise falls back to
    legacy project_root/CWD resolution.
    """
    if os.path.isabs(path):
        return path

    if self._config is not None:
        # REQ-603: Use config.resolve_path() with traversal guard
        effective_path = os.path.join(self._base_dir, path)
        return self._config.resolve_path(effective_path)

    # Legacy fallback (R5 compat)
    base = self._project_root if self._project_root else os.getcwd()
    effective_base = os.path.join(base, self._base_dir)
    return os.path.join(effective_base, path)
```

#### SnapshotManager._ensure_gitignore()

```python
def _ensure_gitignore(self) -> None:
    """Create .gitignore in .statekanban/ if it doesn't exist (AC-603.5).

    Content is '*' to prevent snapshots from being tracked by git.
    """
    if self._config is not None:
        statekanban_dir = self._config.resolve_path(".statekanban")
    else:
        base = self._project_root if self._project_root else os.getcwd()
        statekanban_dir = os.path.join(base, ".statekanban")

    gitignore_path = os.path.join(statekanban_dir, ".gitignore")

    if not os.path.exists(gitignore_path):
        os.makedirs(statekanban_dir, exist_ok=True)
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("*\n")
```

This is called lazily on first `save_snapshot()`.

### Data Flow

```
Config(project_root="/tmp/sk_project")
    |
    v  SnapshotManager(config=config)
    |
    v  mgr.save_snapshot(kanban, "snapshot1.json")
    |-- _resolve_path("snapshot1.json")
    |-- config.resolve_path(".statekanban/snapshots/snapshot1.json")
    |-- = "/tmp/sk_project/.statekanban/snapshots/snapshot1.json"
    |
    v  _save_snapshot_atomic(kanban, "/tmp/sk_project/.statekanban/snapshots/snapshot1.json")


Config(project_root="/tmp/sk_other_project")
    |
    v  SnapshotManager(config=config_other)
    |
    v  mgr_other.list_snapshots()
    |-- _resolve_path("") => config.resolve_path(".statekanban/snapshots/")
    |-- = "/tmp/sk_other_project/.statekanban/snapshots/"
    |-- Only sees snapshots in /tmp/sk_other_project/.statekanban/snapshots/
```

### Isolation Guarantee

Different `project_root` values produce disjoint snapshot directories:

```
project_root = "/tmp/sk_project"    => /tmp/sk_project/.statekanban/snapshots/
project_root = "/tmp/sk_other"      => /tmp/sk_other/.statekanban/snapshots/
project_root = "" (CWD fallback)    => $CWD/.statekanban/snapshots/
```

No SnapshotManager instance can list or access snapshots from a different project_root because:
1. `list_snapshots()` only scans `self._config.resolve_path(".statekanban/snapshots/")`.
2. `load_snapshot()` and `delete_snapshot()` resolve paths through the same `config.resolve_path()`.
3. Path traversal guard (REQ-602) prevents `..` escapes that could reach another project's snapshots.

### Compatibility Analysis

- **Public API unchanged**: `save()`, `load()`, `list()`, `delete()` signatures are identical.
- **New `config` parameter defaults to None**: Existing code that constructs `SnapshotManager(project_root=x)` still works.
- **Storage path is deterministic**: With the same `project_root`, the storage path is the same as R5 (`project_root/.statekanban/snapshots/`). The only behavioral change is that `config.resolve_path()` applies traversal guards and uses `Path.resolve()` for normalization.
- **`.gitignore` creation is idempotent**: Only creates if missing; existing `.gitignore` is not overwritten.

---

## REQ-604: Valve Path Contract -- OutputValve Write Path Enforcement

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `core/valve.py` | `OutputValve.__init__()` | Add `config: Config | None` parameter |
| `core/valve.py` | `OutputValve._resolve_artifact_path()` | Delegate to `config.resolve_path()` |
| `core/valve.py` | `OutputValve.validate_and_write()` | Add debug logging of resolved path |
| `engine/engine.py` | `Engine.__init__()` | Pass `config` to OutputValve |
| `cli/main.py` | `cmd_drive()` | Pass `config` to OutputValve (already done) |
| `testing/e2e_helpers.py` | `_build_engine()` | Pass `config` to OutputValve (already done) |
| `04_testing/test_scripts/test_valve_path_contract.py` | New file | Path contract tests |

### Interface Changes

#### OutputValve constructor

```python
class OutputValve:
    def __init__(
        self,
        validators: list[Validator] | None = None,
        kanban: StateKanban | None = None,
        project_root: str = "",        # REQ-503: deprecated, use config
        config: Config | None = None,  # REQ-604: preferred
    ) -> None:
        """
        Args:
            validators: Ordered list of validators.
            kanban: StateKanban instance for error signal injection.
            project_root: Project space root (deprecated, use config).
            config: Config instance for path resolution (REQ-604).
        """
        self._validators: list[Validator] = validators or [
            SyntaxValidator(),
            TypeValidator(),
            TestValidator(),
        ]
        self._kanban = kanban
        self._config = config
        # Backward compat: if config not provided, store project_root
        if config is not None:
            self._project_root = config.project_root
        else:
            self._project_root = project_root
```

#### OutputValve._resolve_artifact_path() -- unified with config.resolve_path()

```python
def _resolve_artifact_path(self, artifact_path: str) -> str:
    """Resolve an artifact path against project_root.

    REQ-604: When config is provided, delegates to config.resolve_path()
    which includes traversal guard (REQ-602).
    Otherwise falls back to legacy project_root/CWD resolution.

    Args:
        artifact_path: Path from the artifact.

    Returns:
        Absolute resolved path.

    Raises:
        PathEscapeError: If resolved path escapes project_root (via config.resolve_path).
    """
    if self._config is not None:
        return self._config.resolve_path(artifact_path)

    # Legacy fallback (R5 compat)
    if os.path.isabs(artifact_path):
        return artifact_path
    base = self._project_root if self._project_root else os.getcwd()
    return os.path.join(base, artifact_path)
```

#### OutputValve.validate_and_write() -- debug logging

```python
async def validate_and_write(self, artifact: Artifact) -> ValveResult:
    # ... validation chain unchanged ...

    # All validators passed -- resolve artifact path and perform atomic write
    resolved_path = self._resolve_artifact_path(artifact.path)
    logger.debug(
        "Valve write: original_path=%s, resolved_path=%s",
        artifact.path,
        resolved_path,
    )
    # ... atomic write unchanged ...
```

### Path Contract

The contract enforced by REQ-604:

> **For every file written by OutputValve, the resolved write path
> is either (a) within project_root, or (b) an absolute path
> (with warning log). PathEscapeError is raised for any path
> that resolves outside project_root via relative traversal.**

This contract is enforced by the chain:
```
OutputValve.validate_and_write(artifact)
    |
    v  _resolve_artifact_path(artifact.path)
    |-- config.resolve_path(artifact.path)
    |       |
    |       v  VirtualProjectRoot.resolve()
    |       |-- normalizes to absolute Path
    |       |
    |       v  Traversal guard (REQ-602)
    |       |-- PathEscapeError if escape detected
    |
    v  _atomic_write(resolved_path, content)
```

### Test Design: test_valve_path_contract.py

```python
"""Valve path contract tests (REQ-604)."""

class TestValvePathContract:

    @pytest.mark.asyncio
    async def test_normal_path_write_succeeds(self):
        """AC-604.1: Normal path within project_root writes successfully."""
        # config with project_root set, artifact with relative path
        # -> write succeeds, file exists at project_root/path

    @pytest.mark.asyncio
    async def test_escape_path_write_blocked(self):
        """AC-604.2: Traversal path raises PathEscapeError, no file written."""
        # config with project_root set, artifact with "../../etc/passwd"
        # -> PathEscapeError raised, no file at escaped path

    @pytest.mark.asyncio
    async def test_absolute_path_write_succeeds_with_warning(self):
        """AC-604.3: Absolute path writes successfully, warning logged."""
        # config with project_root set, artifact with absolute path
        # -> write succeeds, warning logged

    def test_valve_accepts_config_parameter(self):
        """AC-604.4: OutputValve constructor accepts config parameter."""

    @pytest.mark.asyncio
    async def test_valve_logs_resolved_path(self):
        """AC-604.5: Valve writes log with original and resolved path."""
        # capture debug log, verify both paths present
```

### Compatibility Analysis

- **New `config` parameter defaults to None**: Existing `OutputValve(kanban=kanban, project_root=x)` still works.
- **_resolve_artifact_path() signature unchanged**: Same input/output types. Only internal delegation logic changes.
- **validate_and_write() signature unchanged**: Same input/output types. Only adds debug logging.
- **PathEscapeError propagation**: If a traversal path is passed, PathEscapeError propagates up from `validate_and_write()`. This is a new exception that callers must be aware of. Engine's `_crystalize_and_write()` already has a general `except Exception` handler for valve failures, so it will catch this correctly.

---

## REQ-605: CLI Path Validation -- CLI Entry Path Validation Chain

### Change Scope

| File | Class/Method | Change Type |
|------|-------------|-------------|
| `cli/validate.py` | `validate_project_root()` | New: full validation chain |
| `cli/validate.py` | `NullByteError` | New: specific error for null byte detection |
| `cli/validate.py` | `PathValidationError` | New: base for validation errors |
| `cli/main.py` | `cmd_drive()` | Replace inline validation with `validate_project_root()` |
| `04_testing/test_scripts/test_cli_path_validation.py` | New file | CLI path validation tests |

### Interface Changes

#### cli/validate.py (new module)

```python
"""CLI path validation for --project-root argument.

Validation chain (in order, AC-605.7):
1. Null byte detection
2. Path normalization (relative -> absolute)
3. Existence check
4. Directory check

Each step produces a specific error code and message.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


class PathValidationError(Exception):
    """Base error for CLI path validation failures."""

    exit_code: int = 1


class NullByteError(PathValidationError):
    """Path contains null byte (AC-605.1)."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Path contains null byte: {path!r}")


class PathNotExistError(PathValidationError):
    """Project root path does not exist (AC-605.3)."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Project root does not exist: {path}")


class PathNotDirectoryError(PathValidationError):
    """Project root path is not a directory (AC-605.4)."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Project root is not a directory: {path}")


def validate_project_root(path_str: str) -> Path:
    """Validate and normalize --project-root argument.

    Validation chain (AC-605.7):
    1. Null byte detection -- fail fast before any path operations
    2. Relative -> absolute conversion (via os.getcwd(), the ONLY
       authorized os.getcwd() call in CLI)
    3. Existence check
    4. Directory check

    Args:
        path_str: Raw --project-root argument value.

    Returns:
        Validated absolute Path.

    Raises:
        NullByteError: If path_str contains null bytes.
        PathNotExistError: If path does not exist.
        PathNotDirectoryError: If path is not a directory.
    """
    # Step 1: Null byte detection (AC-605.1)
    if "\x00" in path_str:
        raise NullByteError(path_str)

    # Step 2: Normalize to absolute path (AC-605.2)
    # This is the ONLY authorized os.getcwd() call in the CLI module
    abs_path = Path(path_str).resolve()

    # Step 3: Existence check (AC-605.3)
    if not abs_path.exists():
        raise PathNotExistError(str(abs_path))

    # Step 4: Directory check (AC-605.4)
    if not abs_path.is_dir():
        raise PathNotDirectoryError(str(abs_path))

    return abs_path
```

#### cmd_drive() refactored

```python
def cmd_drive(args: argparse.Namespace) -> int:
    """Execute the 'drive' sub-command."""
    config = Config()
    if args.rounds is not None:
        config.convergence_max_rounds = args.rounds

    # REQ-605: --project-root validation via validate_project_root()
    if args.project_root is not None:
        try:
            validated_root = validate_project_root(args.project_root)
            config.project_root = str(validated_root)
        except NullByteError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except PathNotExistError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except PathNotDirectoryError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    # ... rest unchanged ...
```

### Validation Chain Order (AC-605.7)

```
Input: --project-root value
    |
    v  Step 1: Null byte detection
    |-- If "\x00" in value -> NullByteError, exit 1
    |
    v  Step 2: Relative -> absolute conversion
    |-- Path(value).resolve()
    |-- This is the ONLY os.getcwd() call in CLI
    |
    v  Step 3: Existence check
    |-- If not abs_path.exists() -> PathNotExistError, exit 1
    |
    v  Step 4: Directory check
    |-- If not abs_path.is_dir() -> PathNotDirectoryError, exit 1
    |
    v  Return validated absolute Path
```

**Why null byte check is first**: Null bytes can cause path truncation on C-style string handling (the OS truncates at `\x00`). Checking for null bytes before any path operation prevents the OS from interpreting a malicious path like `/tmp/valid\x00../../etc/passwd` as `/tmp/valid`.

### Windows Considerations

On Windows, `Path.resolve()` handles:
- **UNC paths** (`\\server\share\dir`): Treated as absolute, no `os.getcwd()` needed.
- **Drive-relative paths** (`\dir`): Resolved against current drive's root.
- **Drive letter paths** (`C:dir`): Resolved against CWD on that drive.

These are all handled correctly by `Path.resolve()`. No special Windows code is needed beyond what `pathlib` provides.

### Test Design: test_cli_path_validation.py

```python
"""CLI path validation tests (REQ-605)."""

class TestValidateProjectRoot:

    def test_null_byte_rejected(self):
        """AC-605.1: Null byte in path raises NullByteError."""
        with pytest.raises(NullByteError):
            validate_project_root("/tmp/test\x00malicious")

    def test_relative_path_converted_to_absolute(self):
        """AC-605.2: Relative path converted to absolute."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Use a relative path that resolves to tmp_dir
            # (test from within tmp_dir's parent)
            result = validate_project_root(tmp_dir)
            assert result.is_absolute()
            assert result == Path(tmp_dir).resolve()

    def test_nonexistent_path_rejected(self):
        """AC-605.3: Nonexistent path raises PathNotExistError."""
        with pytest.raises(PathNotExistError):
            validate_project_root("/nonexistent_dir_12345")

    def test_file_path_rejected(self):
        """AC-605.4: File (not directory) raises PathNotDirectoryError."""
        with tempfile.NamedTemporaryFile() as tmp_file:
            with pytest.raises(PathNotDirectoryError):
                validate_project_root(tmp_file.name)

    def test_valid_directory_accepted(self):
        """AC-605.2/3/4: Valid directory returns absolute Path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = validate_project_root(tmp_dir)
            assert result == Path(tmp_dir).resolve()

    def test_validation_order_null_byte_before_existence(self):
        """AC-605.7: Null byte check runs before existence check."""
        # Path with null byte that doesn't exist
        # Should raise NullByteError, not PathNotExistError
        with pytest.raises(NullByteError):
            validate_project_root("/nonexistent\x00path")
```

### Compatibility Analysis

- **New file `cli/validate.py`**: No existing code is modified. The module is imported by `cli/main.py`.
- **`cmd_drive()` change**: The inline validation is replaced with a call to `validate_project_root()`. The behavior is identical for all valid inputs. Error messages are slightly different (now include `Error:` prefix and use exception messages), but the exit code (1) is the same.
- **os.getcwd() authorization**: `validate_project_root()` is the ONLY place in the CLI that may call `os.getcwd()` (via `Path.resolve()`). This satisfies AC-605.2 and the global constraint that `os.getcwd()` only appears in `cli/validate.py` and `VirtualProjectRoot.resolve()`.

---

## Cross-REQ Interaction Analysis

### REQ-601 + REQ-602 Interaction

REQ-602's traversal guard is implemented inside REQ-601's `Config.resolve_path()`. They are a single unified method. The guard is transparent to callers -- it either returns the resolved path or raises `PathEscapeError`. No caller needs to handle the guard separately.

### REQ-601 + REQ-603 Interaction

SnapshotManager receives `config` (REQ-603) and calls `config.resolve_path()` (REQ-601). This means snapshots automatically benefit from the traversal guard (REQ-602). If someone tries to save a snapshot with a traversal path, `PathEscapeError` is raised.

### REQ-601 + REQ-604 Interaction

OutputValve receives `config` (REQ-604) and delegates to `config.resolve_path()` (REQ-601). Same pattern: valve writes automatically benefit from the traversal guard.

### REQ-603 + REQ-604 Interaction

Both SnapshotManager and OutputValve now use `config.resolve_path()` for path resolution. They share the same traversal guard and the same base path (`project_root`). Their storage paths are:
- Snapshots: `project_root/.statekanban/snapshots/`
- Valve writes: `project_root/<artifact_path>`

These are disjoint sub-trees within `project_root`, providing natural isolation.

### REQ-605 + REQ-601 Interaction

REQ-605 validates `--project-root` at CLI entry time, BEFORE `Config` is constructed. This means `Config.resolve_path()` always receives a validated `project_root` (absolute, existing, directory). The only exception is when `--project-root` is not provided (default: empty string = CWD fallback).

### REQ-604 + REQ-602 Interaction

If an artifact path contains `..` traversal, the valve's call to `config.resolve_path()` triggers `PathEscapeError`. The artifact is NOT written (the exception propagates to `Engine._crystalize_and_write()`, which catches it and injects an ErrorSignal). This is the desired behavior: no file escapes the sandbox.

---

## Implementation Order

The REQs have the following dependency structure:

```
REQ-601 (VirtualProjectRoot)
    |
    +---> REQ-602 (Path Traversal Guard) -- inside resolve_path()
    |
    +---> REQ-603 (Snapshot Isolation) -- depends on 601+602
    |
    +---> REQ-604 (Valve Path Contract) -- depends on 601+602

REQ-605 (CLI Path Validation) -- independent of 601-604
```

Recommended implementation order:

1. **REQ-601 + REQ-602 together**: Add `VirtualProjectRoot` class and refactored `resolve_path()` with traversal guard + `PathEscapeError` in `core/errors.py`. These are tightly coupled -- `resolve_path()` is a single method that does both resolution and guarding.

2. **REQ-603**: Update `SnapshotManager` to accept `config`, delegate to `config.resolve_path()`, add `.gitignore` auto-creation.

3. **REQ-604**: Update `OutputValve` to accept `config`, delegate to `config.resolve_path()`, add debug logging. Add `test_valve_path_contract.py`.

4. **REQ-605**: Create `cli/validate.py` with `validate_project_root()`. Refactor `cmd_drive()`. Add `test_cli_path_validation.py`.

This order ensures that each step builds on the previous and can be tested incrementally.

---

## Error Code Allocation

| Code | Name | Module | Trigger |
|------|------|--------|---------|
| SK_06_001 | PathEscapeError | `core/errors.py` | `resolve_path()` detects path traversal outside project_root |

No other new error codes. CLI validation errors use Python exceptions (`NullByteError`, `PathNotExistError`, `PathNotDirectoryError`) that produce exit code 1 but are not SK_ error codes (they are CLI-level, not system-level).

---

## File Change Summary

| File | Change Type | REQ(s) |
|------|-------------|--------|
| `config.py` | Modified: add VirtualProjectRoot, refactor resolve_path() | 601, 602 |
| `core/errors.py` | Modified: add PathEscapeError | 602 |
| `core/valve.py` | Modified: add config param, delegate to resolve_path() | 604 |
| `snapshot.py` | Modified: add config param, delegate to resolve_path(), add .gitignore | 603 |
| `engine/engine.py` | Modified: pass config to SnapshotManager | 603 |
| `cli/main.py` | Modified: use validate_project_root(), pass config to Valve/Snapshot | 605 |
| `cli/validate.py` | New: validate_project_root() and error classes | 605 |
| `testing/e2e_helpers.py` | Modified: pass config to SnapshotManager | 603 |
| `04_testing/test_scripts/test_valve_path_contract.py` | New: valve path contract tests | 604 |
| `04_testing/test_scripts/test_cli_path_validation.py` | New: CLI path validation tests | 605 |
| `04_testing/test_scripts/test_isolation.py` | New: isolation tests (per approved_tech_stack.json) | 601-605 |

---

## Backward Compatibility Summary

| REQ | Breaking Change | Backward Compatible |
|-----|-----------------|-------------------|
| 601 | No (VirtualProjectRoot is internal) | Yes (Config.project_root str field retained) |
| 602 | No (PathEscapeError is new, only fires on invalid input) | Yes (valid paths never trigger) |
| 603 | No (SnapshotManager.public_api unchanged) | Yes (new config param defaults to None) |
| 604 | No (OutputValve.public_api unchanged) | Yes (new config param defaults to None) |
| 605 | No (CLI exit behavior same for valid input) | Yes (error messages slightly different, exit code same) |

All 407 existing R5 tests should pass without modification. New tests are additive.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `Path.resolve()` performance (symlink resolution) | Only called in `resolve_path()`, not hot path; acceptable for file I/O |
| `Path.is_relative_to()` not available on Python < 3.9 | Project requires Python 3.11+ (per tech stack) |
| VPR cache invalidation when project_root mutated | `__setattr__` override clears cached `_vpr` |
| `.gitignore` auto-creation race condition | `os.makedirs(exist_ok=True)` + check-then-write with O_EXCL not needed (idempotent) |
| PathEscapeError propagation to Engine | Engine's `except Exception` handler in `_crystalize_and_write()` catches it |
| Windows UNC paths | `Path.resolve()` handles UNC natively; no special code needed |
