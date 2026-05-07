"""Tests for MessageBus: pub/sub, sync call, async notify."""

from __future__ import annotations

import asyncio

import pytest

from statekanban.core.errors import SubscriptionError, SyncCallTimeoutError
from statekanban.core.kanban import Signal, SignalType, make_signal_id, now_utc


class TestMessageBusSubscribe:
    """TC-MB-001 ~ TC-MB-003: Subscribe operations."""

    @pytest.mark.asyncio
    async def test_valid_subscription(self, bus):
        # TC-MB-001
        sub_id = bus.subscribe("intent", callback=lambda s: asyncio.sleep(0))
        assert isinstance(sub_id, str) and len(sub_id) > 0

    @pytest.mark.asyncio
    async def test_empty_signal_type_rejected(self, bus):
        # TC-MB-002
        with pytest.raises(SubscriptionError):
            bus.subscribe("", callback=lambda s: asyncio.sleep(0))

    @pytest.mark.asyncio
    async def test_non_callable_callback_rejected(self, bus):
        # TC-MB-003
        with pytest.raises(SubscriptionError):
            bus.subscribe("intent", callback=42)


class TestMessageBusUnsubscribe:
    """TC-MB-004 ~ TC-MB-005: Unsubscribe operations."""

    @pytest.mark.asyncio
    async def test_valid_unsubscribe(self, bus):
        # TC-MB-004
        sub_id = bus.subscribe("intent", callback=lambda s: asyncio.sleep(0))
        bus.unsubscribe(sub_id)

    @pytest.mark.asyncio
    async def test_invalid_unsubscribe(self, bus):
        # TC-MB-005
        with pytest.raises(SubscriptionError):
            bus.unsubscribe("nonexistent-sub-id")


class TestMessageBusPublish:
    """TC-MB-006 ~ TC-MB-008: Publish operations."""

    @pytest.mark.asyncio
    async def test_publish_to_matching_subscribers(self, bus):
        # TC-MB-006
        received: list[Signal] = []

        async def cb(signal: Signal) -> None:
            received.append(signal)

        bus.subscribe("intent", cb)
        signal = Signal(
            signal_id=make_signal_id(),
            signal_type=SignalType.INTENT,
            author_role="coder",
            target_id="A",
            payload={},
            timestamp=now_utc(),
            round_number=0,
        )
        await bus.publish(signal)
        # Give the event loop a chance to deliver
        await asyncio.sleep(0.1)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self, bus):
        # TC-MB-007
        signal = Signal(
            signal_id=make_signal_id(),
            signal_type=SignalType.VETO,
            author_role="reviewer",
            target_id="A",
            payload={},
            timestamp=now_utc(),
            round_number=0,
        )
        # Should not raise
        await bus.publish(signal)

    @pytest.mark.asyncio
    async def test_publish_creates_audit_entry(self, bus, kanban):
        # TC-MB-008
        initial_count = len(kanban.audit.read_entries())
        signal = Signal(
            signal_id=make_signal_id(),
            signal_type=SignalType.INTENT,
            author_role="coder",
            target_id="A",
            payload={},
            timestamp=now_utc(),
            round_number=0,
        )
        await bus.publish(signal)
        entries = kanban.audit.read_entries()
        assert len(entries) > initial_count


class TestMessageBusSyncCall:
    """TC-MB-009 ~ TC-MB-012: Sync call operations."""

    @pytest.mark.asyncio
    async def test_successful_sync_call(self, bus):
        # TC-MB-009
        async def handler(request: dict) -> dict:
            return {"status": "ok"}

        bus.register_sync_handler("reviewer", handler)
        result = await bus.sync_call("reviewer", {"data": 1})
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_sync_call_timeout(self, bus):
        # TC-MB-010
        async def slow_handler(request: dict) -> dict:
            await asyncio.sleep(10)
            return {"status": "late"}

        bus.register_sync_handler("reviewer", slow_handler)
        with pytest.raises(SyncCallTimeoutError):
            await bus.sync_call("reviewer", {"data": 1}, timeout=0.1)

    @pytest.mark.asyncio
    async def test_sync_call_no_handler(self, bus):
        # TC-MB-011
        with pytest.raises(SyncCallTimeoutError):
            await bus.sync_call("nonexistent_role", {"data": 1})

    @pytest.mark.asyncio
    async def test_sync_call_audit(self, bus, kanban):
        # TC-MB-012
        async def handler(request: dict) -> dict:
            return {"status": "ok"}

        bus.register_sync_handler("reviewer", handler)
        initial_count = len(kanban.audit.read_entries())
        await bus.sync_call("reviewer", {"data": 1})
        assert len(kanban.audit.read_entries()) > initial_count


class TestMessageBusAsyncNotify:
    """TC-MB-013 ~ TC-MB-015: Async notify operations."""

    @pytest.mark.asyncio
    async def test_valid_notification(self, bus):
        # TC-MB-013
        received: list[dict] = []

        async def handler(notification: dict) -> None:
            received.append(notification)

        bus.register_notify_handler("coder", handler)
        await bus.async_notify("coder", {"msg": "hello"})
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_no_handler_no_error(self, bus):
        # TC-MB-014
        # Should not raise
        await bus.async_notify("nonexistent_role", {"msg": "hello"})

    @pytest.mark.asyncio
    async def test_failing_handler_swallowed(self, bus):
        # TC-MB-015
        async def bad_handler(notification: dict) -> None:
            raise RuntimeError("boom")

        bus.register_notify_handler("coder", bad_handler)
        # Should not raise -- best-effort delivery
        await bus.async_notify("coder", {"msg": "hello"})
