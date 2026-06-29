from __future__ import annotations

from typing import Awaitable, Callable

from titan.ctx import Context


Next = Callable[[], Awaitable[None]]
Middleware = Callable[[Context, Next], Awaitable[None]]


class MiddlewareChain:
    """
    سلسلة middleware تُنفَّذ قبل كل handler.

    كل middleware تستلم ctx وnext.
    استدعاء next() → يكمل الـ update لبقية الـ middleware ثم الـ handler.
    عدم استدعاء next() → يتوقف الـ update هنا.

    لا state ولا logic هنا — فقط تنفيذ متسلسل.
    """

    def __init__(self) -> None:
        self._chain: list[Middleware] = []

    def add(self, fn: Middleware) -> None:
        self._chain.append(fn)

    async def run(self, ctx: Context, handler: Callable[[], Awaitable[None]]) -> None:
        async def build(index: int) -> None:
            if index >= len(self._chain):
                await handler()
                return

            async def next_fn() -> None:
                await build(index + 1)

            await self._chain[index](ctx, next_fn)

        await build(0)
