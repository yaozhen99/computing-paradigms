"""Global configuration for StateKanban."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VirtualProjectRoot (REQ-601)
# ---------------------------------------------------------------------------


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
        If project_root is None, fall back to Path.cwd().

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

    def __repr__(self) -> str:
        """Return representation showing project_root."""
        root_repr = str(self._root) if self._root is not None else "CWD"
        return f"VirtualProjectRoot(root={root_repr!r})"

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> VirtualProjectRoot:
        """Deserialize from dict for Config.from_dict()."""
        return cls(root=data.get("root"))


# ---------------------------------------------------------------------------
# Config (REQ-601, REQ-602)
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Global configuration for the StateKanban system."""

    # LLM settings
    llm_adapter: str = (
        "mock"  # "anthropic", "cli", "mock", "codex", "iflytek", "deepseek"
    )
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.0

    # Codex settings (NEW)
    codex_cli_path: str = "codex"
    codex_timeout: float = 300.0

    # Process settings
    heartbeat_interval: int = 30  # seconds
    heartbeat_threshold: int = 90  # seconds (3x interval)
    convergence_max_rounds: int = 10

    # Viewport settings
    default_token_budget: int = 2000

    # OutputValve settings
    enable_type_check: bool = False
    enable_test_run: bool = True
    enable_human_gate: bool = False  # P2 feature

    # Tool settings
    tool_timeout_default: float = 60.0  # seconds
    shell_timeout_default: float = 60.0  # seconds

    # Snapshot settings
    snapshot_dir: str = ".statekanban/snapshots"

    # CLI input validation
    max_intent_length: int = 4096

    # REQ-501: Project space root
    project_root: str = ""  # empty string => os.getcwd() at resolution time

    # Additional settings
    extra: dict[str, Any] = field(default_factory=dict)

    # REQ-601: VirtualProjectRoot instance (derived from project_root)
    # Not a dataclass field -- computed property
    def __post_init__(self) -> None:
        # Initialize cached VPR as None; it will be lazily computed
        object.__setattr__(self, "_vpr", None)

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name == "project_root":
            # Invalidate cached VPR when project_root changes
            object.__setattr__(self, "_vpr", None)

    @property
    def vpr(self) -> VirtualProjectRoot:
        """Lazy-initialized VirtualProjectRoot derived from project_root."""
        if self._vpr is None:
            object.__setattr__(
                self,
                "_vpr",
                VirtualProjectRoot(
                    root=self.project_root if self.project_root else None
                ),
            )
        return self._vpr

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
            from statekanban.core.errors import PathEscapeError

            raise PathEscapeError(
                attempted_path=relative_path,
                project_root=str(self.vpr.root),
            )

        return str(resolved)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create a Config from a dictionary.

        Unknown keys are moved into the ``extra`` field.  If ``data``
        also contains an ``extra`` key, the two dictionaries are merged
        (data-level unknown keys take precedence over pre-existing extra).
        """
        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_keys}
        extra = {k: v for k, v in data.items() if k not in known_keys}
        config = cls(**filtered)
        config.extra = {**config.extra, **extra}
        return config

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to a dictionary."""
        import dataclasses

        return dataclasses.asdict(self)
