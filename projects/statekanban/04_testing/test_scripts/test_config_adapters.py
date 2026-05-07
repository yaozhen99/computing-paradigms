"""Tests for Config and MockLLMAdapter."""

from __future__ import annotations

import pytest

from statekanban.config import Config
from statekanban.adapters.mock_adapter import MockLLMAdapter
from statekanban.core.kanban import LLMMessage, LLMResponse


class TestConfig:
    """Config creation and serialization."""

    def test_default_config(self):
        config = Config()
        assert config.llm_adapter == "mock"
        assert config.heartbeat_interval == 30
        assert config.convergence_max_rounds == 10
        assert config.default_token_budget == 2000

    def test_from_dict(self):
        data = {
            "llm_adapter": "anthropic",
            "heartbeat_interval": 60,
            "unknown_key": "ignored",
        }
        config = Config.from_dict(data)
        assert config.llm_adapter == "anthropic"
        assert config.heartbeat_interval == 60
        assert "unknown_key" in config.extra

    def test_to_dict(self):
        config = Config(llm_adapter="mock")
        d = config.to_dict()
        assert d["llm_adapter"] == "mock"
        assert "heartbeat_interval" in d


class TestMockLLMAdapter:
    """MockLLMAdapter deterministic responses."""

    @pytest.mark.asyncio
    async def test_configured_response(self):
        responses = [
            LLMResponse(content="hello", finish_reason="end_turn"),
            LLMResponse(content="world", finish_reason="end_turn"),
        ]
        adapter = MockLLMAdapter(responses={"default": responses})
        msg = [LLMMessage(role="user", content="test")]

        r1 = await adapter.complete(msg)
        assert r1.content == "hello"

        r2 = await adapter.complete(msg)
        assert r2.content == "world"

        # Cycles back
        r3 = await adapter.complete(msg)
        assert r3.content == "hello"

    @pytest.mark.asyncio
    async def test_set_response(self):
        adapter = MockLLMAdapter()
        adapter.set_response(
            "coder",
            [
                LLMResponse(content="code response", finish_reason="end_turn"),
            ],
        )
        msg = [LLMMessage(role="user", content="test")]
        r = await adapter.complete(msg)
        assert r.content == "code response"

    @pytest.mark.asyncio
    async def test_no_configured_response(self):
        adapter = MockLLMAdapter()
        msg = [LLMMessage(role="user", content="test")]
        r = await adapter.complete(msg)
        assert "no configured" in r.content
