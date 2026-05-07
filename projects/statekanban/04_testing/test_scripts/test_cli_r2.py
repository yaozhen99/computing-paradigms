"""Tests for CLI options (R2 updated for argparse-based CLI).

TC-CL-001..005: --adapter, --max-rounds, --verbose, intent validation.
Uses argparse (not Click) as per actual implementation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pytest

from statekanban.cli.main import main as cli_main, build_parser
from statekanban.config import Config


# ---------------------------------------------------------------------------
# Helper: invoke CLI via subprocess
# ---------------------------------------------------------------------------

def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the CLI with given arguments."""
    return subprocess.run(
        [sys.executable, "-m", "statekanban.cli.main", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# TC-CL-001: --adapter option
# ---------------------------------------------------------------------------

class TestCLIAdapter:
    """TC-CL-001..002: --adapter option."""

    def test_adapter_mock_accepted(self):
        """--adapter mock is accepted by parser."""
        parser = build_parser()
        args = parser.parse_args(["drive", "test task", "--adapter", "mock"])
        assert args.adapter == "mock"

    def test_adapter_codex_accepted(self):
        """--adapter codex is accepted by parser."""
        parser = build_parser()
        args = parser.parse_args(["drive", "test task", "--adapter", "codex"])
        assert args.adapter == "codex"


# ---------------------------------------------------------------------------
# TC-CL-003: --max-rounds option
# ---------------------------------------------------------------------------

class TestCLIMaxRounds:
    """TC-CL-003: --max-rounds option."""

    def test_max_rounds_default(self):
        """Default max-rounds is 10."""
        config = Config()
        assert config.convergence_max_rounds == 10

    def test_max_rounds_custom(self):
        """Config from_dict overrides convergence_max_rounds."""
        config = Config.from_dict({"convergence_max_rounds": 5})
        assert config.convergence_max_rounds == 5

    def test_max_rounds_cli_option(self):
        """--rounds CLI option parsed correctly."""
        parser = build_parser()
        args = parser.parse_args(["drive", "test task", "--rounds", "5"])
        assert args.rounds == 5


# ---------------------------------------------------------------------------
# TC-CL-004: --verbose flag
# ---------------------------------------------------------------------------

class TestCLIVerbose:
    """TC-CL-004: --verbose flag."""

    def test_verbose_flag_parsed(self):
        """--verbose flag parsed correctly."""
        parser = build_parser()
        args = parser.parse_args(["drive", "test task", "--verbose"])
        assert args.verbose is True

    def test_verbose_default_false(self):
        """Verbose defaults to False."""
        parser = build_parser()
        args = parser.parse_args(["drive", "test task"])
        assert args.verbose is False


# ---------------------------------------------------------------------------
# TC-CL-005: Intent validation
# ---------------------------------------------------------------------------

class TestCLIIntentValidation:
    """TC-CL-005: Intent string parsing."""

    def test_intent_parsed(self):
        """Intent argument is parsed correctly."""
        parser = build_parser()
        args = parser.parse_args(["drive", "implement feature X"])
        assert args.intent == "implement feature X"


# ---------------------------------------------------------------------------
# Config from_dict tests
# ---------------------------------------------------------------------------

class TestConfigFromDict:
    """Config.from_dict with codex settings."""

    def test_config_defaults(self):
        config = Config()
        assert config.codex_cli_path == "codex"
        assert config.codex_timeout == 300.0
        assert config.llm_adapter == "mock"

    def test_config_from_dict_codex(self):
        config = Config.from_dict({
            "codex_cli_path": "/custom/codex",
            "codex_timeout": 120.0,
            "llm_adapter": "codex",
        })
        assert config.codex_cli_path == "/custom/codex"
        assert config.codex_timeout == 120.0
        assert config.llm_adapter == "codex"

    def test_config_from_dict_ignores_unknown(self):
        config = Config.from_dict({"unknown_key": "value"})
        assert config.extra.get("unknown_key") == "value"

    def test_config_to_dict_roundtrip(self):
        config = Config()
        d = config.to_dict()
        config2 = Config.from_dict(d)
        assert config2.llm_adapter == config.llm_adapter
        assert config2.convergence_max_rounds == config.convergence_max_rounds
        assert config2.codex_cli_path == config.codex_cli_path