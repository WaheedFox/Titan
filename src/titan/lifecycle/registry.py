"""
Internal ownership state for one polling run.

This module is deliberately not exported as public API.  A registry is created
for each ``Titan.run_async()`` invocation and owns only work created by that
polling run.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Literal


TaskKind = Literal["chat_worker", "handler"]
WorkerFactory = Callable[["asyncio.Queue[dict | None]"], Awaitable[None]]


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
        return task

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