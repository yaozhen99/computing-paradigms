"""E2E test helpers: runner, scenarios, and result validators.

REQ-003: End-to-end test infrastructure.

Provides:
  - E2ETestRunner: orchestrates full pipeline runs with MockLLMAdapter.
  - ScenarioResult: structured result of a scenario run.
  - Preset scenarios: happy_path, collision_convergence, circuit_break.
  - Result validators: assert functions for common outcomes.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from statekanban.core.kanban import (
    ArtifactType,
    SignalType,
    StateKanban,
    ViewportSpec,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.adapters.mock_adapter import (
    MockLLMAdapter,
    MockCoderBehavior,
    MockReviewerBehavior,
)
from statekanban.engine.engine import Engine
from statekanban.config import Config
from statekanban.tools.call_llm import create_call_llm_tool

# ---------------------------------------------------------------------------
# ScenarioResult
# ---------------------------------------------------------------------------


@dataclass
class ScenarioResult:
    """Result of an E2E scenario run."""

    scenario_name: str
    success: bool
    converged: bool
    forced_terminate: bool
    total_rounds: int
    artifact_count: int
    signal_summary: dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Preset scenarios
# ---------------------------------------------------------------------------


def happy_path_scenario() -> dict[str, Any]:
    """Happy path: coder produces, reviewer approves, converges in 1 round.

    Uses ALWAYS_APPROVE + GENERATE_SIMPLE behavior modes.
    """
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode(
        reviewer_behavior=MockReviewerBehavior.ALWAYS_APPROVE,
        coder_behavior=MockCoderBehavior.GENERATE_SIMPLE,
    )
    config = Config()
    config.convergence_max_rounds = 5
    return {
        "adapter": adapter,
        "config": config,
        "description": "Happy path: produce and approve",
    }


def collision_convergence_scenario() -> dict[str, Any]:
    """Collision convergence: reviewer rejects then approves, converges in 2 rounds.

    Uses REJECT_THEN_APPROVE behavior mode.
    """
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode(
        reviewer_behavior=MockReviewerBehavior.REJECT_THEN_APPROVE,
        coder_behavior=MockCoderBehavior.GENERATE_SIMPLE,
    )
    config = Config()
    config.convergence_max_rounds = 5
    return {
        "adapter": adapter,
        "config": config,
        "description": "Collision convergence: reject then approve",
    }


def circuit_break_scenario() -> dict[str, Any]:
    """Circuit break: always reject, forced terminate after max rounds.

    Uses ALWAYS_REJECT + GENERATE_WITH_BUG behavior modes.
    """
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode(
        reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT,
        coder_behavior=MockCoderBehavior.GENERATE_WITH_BUG,
    )
    config = Config()
    config.convergence_max_rounds = 3
    return {
        "adapter": adapter,
        "config": config,
        "description": "Circuit break: always reject",
    }


# ---------------------------------------------------------------------------
# Result validators
# ---------------------------------------------------------------------------


def validate_converged(result: ScenarioResult) -> bool:
    """Validate that the scenario converged successfully."""
    return result.converged and not result.forced_terminate


def validate_forced_terminate(result: ScenarioResult) -> bool:
    """Validate that the scenario hit circuit break."""
    return result.forced_terminate


def validate_artifact_count(result: ScenarioResult, expected: int) -> bool:
    """Validate that the scenario produced exactly N artifacts."""
    return result.artifact_count == expected


def validate_max_rounds(result: ScenarioResult, max_rounds: int) -> bool:
    """Validate that the scenario completed within max rounds."""
    return result.total_rounds <= max_rounds


# ---------------------------------------------------------------------------
# E2ETestRunner
# ---------------------------------------------------------------------------


class E2ETestRunner:
    """Orchestrates end-to-end scenario runs.

    Usage:
        runner = E2ETestRunner()
        result = runner.run_scenario("happy_path", happy_path_scenario())
        assert validate_converged(result)
    """

    def __init__(self) -> None:
        self._results: list[ScenarioResult] = []

    def run_scenario(
        self,
        name: str,
        scenario: dict[str, Any],
        intent: str = "Test task",
    ) -> ScenarioResult:
        """Run a scenario and return the result.

        Args:
            name: Scenario name.
            scenario: Dict with 'adapter' and 'config' keys.
            intent: Task intent string.

        Returns:
            ScenarioResult with outcome details.
        """
        adapter = scenario.get("adapter", MockLLMAdapter())
        config = scenario.get("config", Config())

        start_time = time.monotonic()
        try:
            result = asyncio.run(self._run_drive(intent, adapter, config))
            duration = time.monotonic() - start_time

            scenario_result = ScenarioResult(
                scenario_name=name,
                success=True,
                converged=result.converged,
                forced_terminate=result.forced_terminate,
                total_rounds=result.total_rounds,
                artifact_count=len(result.artifact_files),
                signal_summary=result.signal_summary,
                duration_seconds=duration,
            )
        except Exception as exc:
            duration = time.monotonic() - start_time
            scenario_result = ScenarioResult(
                scenario_name=name,
                success=False,
                converged=False,
                forced_terminate=False,
                total_rounds=0,
                artifact_count=0,
                duration_seconds=duration,
                error=str(exc),
            )

        self._results.append(scenario_result)
        return scenario_result

    @property
    def results(self) -> list[ScenarioResult]:
        """All scenario results from this runner."""
        return list(self._results)

    async def _run_drive(
        self,
        intent: str,
        adapter: MockLLMAdapter,
        config: Config,
    ) -> Any:
        """Construct a full system and run the drive loop.

        Returns:
            EngineResult from engine.drive().
        """
        # Build system components
        kanban = StateKanban()
        bus = MessageBus(kanban)
        registry = ToolRegistry(kanban)
        valve = OutputValve(kanban=kanban, project_root=config.project_root)

        # Set up viewport specs
        specs = _default_viewport_specs()
        for spec in specs.values():
            kanban.register_viewport(spec)
        slicer = ViewportSlicer(kanban, specs)

        pm = ProcessManager(kanban, bus)

        # Create engine
        engine = Engine(
            kanban=kanban,
            bus=bus,
            registry=registry,
            valve=valve,
            slicer=slicer,
            pm=pm,
            adapter=adapter,
            config=config,
        )

        # Register call_llm tool
        from statekanban.core.kanban import ToolDef

        registry.register(
            ToolDef(
                name="call_llm",
                description="Invoke LLM via adapter",
                param_schema={
                    "type": "object",
                    "properties": {
                        "messages": {"type": "array"},
                        "max_tokens": {"type": "integer"},
                        "temperature": {"type": "number"},
                    },
                    "required": ["messages"],
                },
                required_permissions={"all_roles"},
                timeout_seconds=120.0,
            ),
            create_call_llm_tool(adapter),
        )

        # Create and activate a coder process
        coder_spec = kanban.get_viewport_spec("coder")
        if coder_spec:
            coder_info = pm.create_process(
                role="coder",
                tool_permits={"write_file", "read_file", "call_llm"},
                viewport_spec=coder_spec,
            )
            pm.activate(coder_info.process_id)

        # Run the drive loop
        return await engine.drive(intent)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _default_viewport_specs() -> dict[str, ViewportSpec]:
    """Create default viewport specs for built-in roles."""
    return {
        "coder": ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
        "reviewer": ViewportSpec(
            role="reviewer",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[
                ArtifactType.CODE,
                ArtifactType.CONFIG,
                ArtifactType.DOC,
            ],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
        "tester": ViewportSpec(
            role="tester",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.TEST],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
        "integrator": ViewportSpec(
            role="integrator",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[
                ArtifactType.CODE,
                ArtifactType.CONFIG,
                ArtifactType.TEST,
            ],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
    }
