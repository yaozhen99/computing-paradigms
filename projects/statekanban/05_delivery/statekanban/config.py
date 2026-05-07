"""Global configuration for StateKanban."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Config:
    """Global configuration for the StateKanban system."""

    # LLM settings
    llm_adapter: str = "mock"  # "anthropic", "cli", "mock", "codex"
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

    def resolve_path(self, relative_path: str) -> str:
        """Resolve a path relative to project_root.

        If project_root is empty string, falls back to os.getcwd().
        If relative_path is already absolute, returns it unchanged.

        Args:
            relative_path: Path to resolve (typically relative).

        Returns:
            Absolute path resolved against project_root (or CWD).
        """
        if "\x00" in relative_path:
            raise ValueError("Path contains null bytes")
        if os.path.isabs(relative_path):
            return relative_path
        base = self.project_root if self.project_root else os.getcwd()
        return os.path.join(base, relative_path)

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
