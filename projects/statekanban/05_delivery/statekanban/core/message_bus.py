"""MessageBus: in-memory pub/sub and synchronous call infrastructure.

Thread safety via asyncio event loop (single-threaded concurrency).
No persistence -- StateKanban is the durability layer.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Awaitable, Callable

from statekanban.core.errors import SubscriptionError, SyncCallTimeoutError
from statekanban.core.kanban import Signal, StateKanban

# Type alias for async signal callbacks
SignalCallback = Callable[[Signal], Awaitable[None]]


class MessageBus:
    """In-memory pub/sub and synchronous call infrastructure."""

    def __init__(self, kanban: StateKanban) -> None:
        """
        Args:
            kanban: StateKanban instance for audit logging.
        """
        self._kanban = kanban
        self._subscriptions: dict[str, dict[str, SignalCallback]] = {}
        # signal_type -> {subscription_id: callback}
        self._sync_handlers: dict[
            str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
        ] = {}
        # target_role -> handler
        self._notify_handlers: dict[
            str, Callable[[dict[str, Any]], Awaitable[None]]
        ] = {}
        # target_role -> notification handler

    def subscribe(
        self,
        signal_type: str,
        callback: SignalCallback,
    ) -> str:
        """Subscribe to a signal type.

        Args:
            signal_type: The signal type to listen for.
            callback: Async callback invoked when matching signal is published.

        Returns:
            Subscription ID (for unsubscribe).

        Raises:
            SubscriptionError: Invalid signal type or callback.
        """
        if not signal_type:
            raise SubscriptionError("signal_type must not be empty")
        if not callable(callback):
            raise SubscriptionError("callback must be callable")

        subscription_id = str(uuid.uuid4())
        if signal_type not in self._subscriptions:
            self._subscriptions[signal_type] = {}
        self._subscriptions[signal_type][subscription_id] = callback
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove a subscription.

        Raises:
            SubscriptionError: subscription_id not found.
        """
        found = False
        for signal_type, subs in self._subscriptions.items():
            if subscription_id in subs:
                del subs[subscription_id]
                found = True
                break
        if not found:
            raise SubscriptionError(f"Subscription ID not found: {subscription_id}")

    async def publish(self, signal: Signal) -> None:
        """Publish a signal to all matching subscribers.

        Delivery is async -- callbacks are scheduled, not awaited inline.
        """
        signal_type_key = signal.signal_type.value
        subs = self._subscriptions.get(signal_type_key, {})

        # Audit the publish event
        self._kanban.audit.log(
            event_type="signal_published",
            actor="MessageBus",
            action="publish",
            details={
                "signal_id": signal.signal_id,
                "signal_type": signal_type_key,
                "subscriber_count": len(subs),
            },
        )

        # Schedule all callbacks
        for sub_id, callback in subs.items():
            try:
                asyncio.get_running_loop().create_task(callback(signal))
            except RuntimeError:
                # No running loop, call directly (for testing)
                pass

    async def sync_call(
        self,
        target_role: str,
        request: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Synchronously call another role and await its response.

        Args:
            target_role: The role to call.
            request: Request payload.
            timeout: Maximum wait time in seconds.

        Returns:
            Response payload from the target.

        Raises:
            SyncCallTimeoutError: Target did not respond within timeout.
        """
        handler = self._sync_handlers.get(target_role)
        if handler is None:
            raise SyncCallTimeoutError(
                f"No sync handler registered for role: {target_role}"
            )

        try:
            result = await asyncio.wait_for(handler(request), timeout=timeout)
        except asyncio.TimeoutError:
            self._kanban.audit.log(
                event_type="sync_call_timeout",
                actor="MessageBus",
                action="sync_call",
                details={
                    "target_role": target_role,
                    "timeout": timeout,
                },
            )
            raise SyncCallTimeoutError(
                f"Sync call to '{target_role}' timed out after {timeout}s"
            )

        self._kanban.audit.log(
            event_type="sync_call_completed",
            actor="MessageBus",
            action="sync_call",
            details={"target_role": target_role},
        )
        return result

    async def async_notify(
        self,
        target_role: str,
        notification: dict[str, Any],
    ) -> None:
        """Send a fire-and-forget notification.

        No response expected. Delivery is best-effort within the process.
        """
        handler = self._notify_handlers.get(target_role)
        if handler is not None:
            try:
                await handler(notification)
            except Exception:
                # Best-effort: swallow errors
                pass

        self._kanban.audit.log(
            event_type="async_notify",
            actor="MessageBus",
            action="async_notify",
            details={"target_role": target_role},
        )

    def register_sync_handler(
        self,
        role: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        """Register a sync call handler for a role."""
        self._sync_handlers[role] = handler

    def register_notify_handler(
        self,
        role: str,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Register a notification handler for a role."""
        self._notify_handlers[role] = handler
