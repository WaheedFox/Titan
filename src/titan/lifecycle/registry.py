"""
Internal ownership state for one polling run.

This module is deliberately not exported as public API.  A registry is created
for each ``Titan.run_async()`` invocation and owns only work created by that
polling run.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Literal


TaskKind = Literal["chat_worker", "handler"]
WorkerFactory = Callable[["asyncio.Queue[dict | None]"], Awaitable[None]]
_log = logging.getLogger("titan")


class LifecycleRegistry:
    """Own the queues and tasks created by one polling run."""

    def __init__(self) -> None:
        self.chat_queues: dict[int, asyncio.Queue[dict | None]] = {}
        self.chat_workers: dict[int, asyncio.Task[Any]] = {}
        self.handler_tasks: set[asyncio.Task[Any]] = set()
        self.tasks: set[asyncio.Task[Any]] = set()

    def create_task(
        self,
        awaitable: Awaitable[Any],
        *,
        name: str,
        kind: TaskKind,
    ) -> asyncio.Task[Any]:
        """Create and register one task owned by this polling run."""
        task = asyncio.create_task(awaitable, name=name)
        self.tasks.add(task)
        if kind == "handler":
            self.handler_tasks.add(task)
        task.add_done_callback(self._observe_task)
        return task

    def _observe_task(self, task: asyncio.Task[Any]) -> None:
        """
        Observe one owned task exactly once, then release its registry entries.

        Handler-level exceptions are normally consumed by Titan's
        ``_handle_update`` error contract before reaching this callback.  This
        callback is therefore reserved for lifecycle failures that escape
        their coroutine, preventing both silent task failures and duplicate
        calls to the user's error handler.
        """
        self.tasks.discard(task)
        self.handler_tasks.discard(task)

        if task.cancelled():
            return

        exception = task.exception()
        if exception is not None:
            _log.error(
                "Unhandled exception in lifecycle task %s",
                task.get_name(),
                exc_info=(
                    type(exception),
                    exception,
                    exception.__traceback__,
                ),
            )

    def ensure_chat_worker(
        self,
        chat_id: int,
        worker_factory: WorkerFactory,
    ) -> "asyncio.Queue[dict | None]":
        """Return a chat queue, creating and registering its worker once."""
        if chat_id not in self.chat_queues:
            queue: "asyncio.Queue[dict | None]" = asyncio.Queue()
            self.chat_queues[chat_id] = queue
            self.chat_workers[chat_id] = self.create_task(
                worker_factory(queue),
                name=f"titan-chat-{chat_id}",
                kind="chat_worker",
            )
        return self.chat_queues[chat_id]