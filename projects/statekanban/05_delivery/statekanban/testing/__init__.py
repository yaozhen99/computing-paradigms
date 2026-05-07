"""E2E test infrastructure for StateKanban.

Provides E2ETestRunner, preset scenarios, and result validators.
REQ-003: End-to-end test infrastructure.
"""

from statekanban.testing.e2e_helpers import E2ETestRunner, ScenarioResult

__all__ = ["E2ETestRunner", "ScenarioResult"]
