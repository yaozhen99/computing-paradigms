"""StateKanban Live API Smoke Tests -- R4

These tests hit the real Anthropic API and are ONLY executed
when --run-live is passed to pytest. They validate that the
Engine.drive() loop works end-to-end with a real LLM backend.

Requirements:
- ANTHROPIC_API_KEY environment variable must be set
- --run-live pytest flag must be passed

Run:  pytest 04_testing/test_scripts/test_live_api.py --run-live -v
"""

from __future__ import annotations

import os

import pytest

from statekanban.core.kanban import (
    ArtifactType,
    SignalType,
    StateKanban,
    ViewportSpec,
    ToolDef,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.core.process import ProcessManager
from statekanban.engine.engine import Engine
from statekanban.adapters.anthropic_adapter import AnthropicMessagesAdapter
from statekanban.tools.call_llm import create_call_llm_tool
from statekanban.config import Config


def _make_viewports() -> dict:
    """Standard 4-role viewport specs."""
    return {
        "coder": ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG],
            visible_target_patterns=["*"],
            max_tokens=4000,
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
            max_tokens=4000,
        ),
        "tester": ViewportSpec(
            role="tester",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.TEST],
            visible_target_patterns=["*"],
            max_tokens=4000,
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
            max_tokens=4000,
        ),
    }


def _has_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


@pytest.mark.live_api
@pytest.mark.asyncio
@pytest.mark.skipif(not _has_api_key(), reason="ANTHROPIC_API_KEY not set")
async def test_live_api_smoke_drive():
    """LIVE-01: Engine.drive() completes a single round with real Anthropic API."""
    kanban = StateKanban()
    bus = MessageBus(kanban)
    registry = ToolRegistry(kanban)
    valve = OutputValve(kanban=kanban)

    vp = _make_viewports()
    for spec in vp.values():
        kanban.register_viewport(spec)
    slicer = ViewportSlicer(kanban, vp)

    pm = ProcessManager(kanban, bus)
    adapter = AnthropicMessagesAdapter()
    config = Config()
    config.convergence_max_rounds = 2

    registry.register(
        ToolDef(
            name="call_llm",
            description="Invoke LLM via adapter",
            param_schema={
                "type": "object",
                "properties": {"messages": {"type": "array"}},
                "required": ["messages"],
            },
            required_permissions={"all_roles"},
            timeout_seconds=120.0,
        ),
        create_call_llm_tool(adapter),
    )

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

    result = await engine.drive("Write a hello world function in Python")

    assert result is not None
    assert isinstance(result.converged, bool)
    assert result.total_rounds > 0


@pytest.mark.live_api
@pytest.mark.asyncio
@pytest.mark.skipif(not _has_api_key(), reason="ANTHROPIC_API_KEY not set")
async def test_live_api_smoke_adapter_complete():
    """LIVE-02: AnthropicMessagesAdapter.complete() returns valid LLMResponse."""
    adapter = AnthropicMessagesAdapter()
    from statekanban.core.kanban import LLMMessage

    messages = [LLMMessage(role="user", content="Say 'pong' and nothing else.")]
    response = await adapter.complete(messages=messages, max_tokens=64)

    assert response is not None
    assert response.content is not None
    assert len(response.content) > 0
    assert response.finish_reason in ("end_turn", "stop_sequence", "max_tokens")


@pytest.mark.live_api
@pytest.mark.asyncio
@pytest.mark.skipif(not _has_api_key(), reason="ANTHROPIC_API_KEY not set")
async def test_live_api_smoke_auth_error():
    """LIVE-03: Invalid API key raises LLMAuthError."""
    from statekanban.core.errors import LLMAuthError

    adapter = AnthropicMessagesAdapter(api_key="sk-invalid-key-0000000000")
    from statekanban.core.kanban import LLMMessage

    messages = [LLMMessage(role="user", content="test")]
    with pytest.raises(LLMAuthError):
        await adapter.complete(messages=messages, max_tokens=16)
