"""Global configuration for StateKanban."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Config:
    """Global configuration for the StateKanban system."""

    # LLM settings
    llm_adapter: str = "mock"  # "anthropic", "cli", "mock"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.0

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

    # Additional settings
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create a Config from a dictionary, ignoring unknown keys."""
        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_keys}
        extra = {k: v for k, v in data.items() if k not in known_keys}
        config = cls(**filtered)
        config.extra = extra
        return config

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to a dictionary."""
        import dataclasses
        result = dataclasses.asdict(self)
        return result
