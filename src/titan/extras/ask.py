"""
titan.extras.ask

Opt-in ask/reply conversations, applied via middleware.

Usage (recommended — registers automatically in User Data Registry):
    @bot.command("start")
    async def start(ctx):
        ask = bot.enable_ask()   # creates, registers, and wires middleware in one call
        name = await ask(ctx, "What's your name?")
        await ctx.reply(f"Hello, {name}!")

Usage (manual — does NOT register in User Data Registry automatically):
    from titan.extras.ask import AskManager

    ask = AskManager()
    bot.middleware(ask.as_middleware())

    @bot.command("start")
    async def start(ctx):
        name = await ask(ctx, "What's your name?")
        await ctx.reply(f"Hello, {name}!")

Note: when using the manual approach, register ask with bot.declare_user_data(ask)
to include it in /mydata and /forgetme coverage. bot.enable_ask() does this automatically.
"""

from __future__ import annotations

import asyncio
from typing import Any

from titan.errors import TitanError

__all__ = ["AskManager"]


class AskManager:
    """
    Manages ask/reply conversations between bot and user.

    Implements UserDataModule Protocol (ADR-016):
        - component_name: "pending_asks"
        - data_description: "Unfinished interactions waiting for user reply"
        - data_for(user_id): returns count of active asks for this user
        - erase(user_id): cancels all pending asks for this user

    Wiring via bot.enable_ask() (recommended):
        ask = bot.enable_ask()
        # AskManager is automatically registered in UserDataRegistry

    Wiring manually (opt-out of auto-registry):
        ask = AskManager()
        bot.middleware(ask.as_middleware())
        bot.declare_user_data(ask)  # manual registration for privacy compliance
    """

    # -------------------------
    # UserDataModule Protocol
    # -------------------------

    @property
    def component_name(self) -> str:
        return "pending_asks"

    @property
    def data_description(self) -> str:
        return "Unfinished interactions waiting for user reply"

    async def data_for(self, user_id: int) -> dict:
        """
        يُعيد عدد الـ asks المعلّقة لهذا المستخدم عبر كل المحادثات.
        """
        count = sum(
            1
            for (_, uid), fut in self._pending.items()
            if uid == user_id and not fut.done()
        )
        return {"count": count}

    async def erase(self, user_id: int) -> None:
        """
        يلغي كل الـ asks المعلّقة لهذا المستخدم — محو حقيقي، لا flags.

        Future مُلغاة تُثير CancelledError في الكود المنتظر لها.
        """
        keys_to_cancel = [key for key in list(self._pending) if key[1] == user_id]
        for key in keys_to_cancel:
            future = self._pending.pop(key, None)
            if future is not None and not future.done():
                future.cancel()

    # -------------------------
    # Core
    # -------------------------

    def __init__(self) -> None:
        self._pending: dict[tuple[int, int], asyncio.Future[str]] = {}
        # يُعيَّن True عند التسجيل عبر bot.enable_ask() أو bot.declare_user_data().
        # يمنع التحذير من الظهور عند الاستخدام الرسمي.
        self._privacy_registered: bool = False

    def as_middleware(self):
        """
        Return a middleware function that intercepts pending ask replies.

        .. deprecated::
            Direct use of ``as_middleware()`` bypasses the User Data Registry.
            AskManager stores User Data (pending asks) that will NOT appear in
            /mydata and will NOT be erased by /forgetme unless the instance is
            registered.

            Use ``bot.enable_ask()`` instead — it creates, registers, and wires
            the middleware in one call, ensuring full privacy compliance.

            If you must use the manual path (e.g. for testing), register the
            instance explicitly::

                ask = AskManager()
                bot.declare_user_data(ask)       # register in Privacy Registry
                bot.middleware(ask.as_middleware())

        Interception rules:
        - Only regular user messages (not callbacks, not channel posts).
        - Only when a future is pending for the exact (chat_id, user_id) pair.
        - Consumed messages do not reach any handler or subsequent middleware.
        """
        if not self._privacy_registered:
            import warnings
            warnings.warn(
                "AskManager.as_middleware() called directly on an unregistered instance. "
                "Pending asks will NOT appear in /mydata and will NOT be erased by /forgetme. "
                "Use bot.enable_ask() to ensure full privacy compliance, "
                "or call bot.declare_user_data(ask) before bot.middleware(ask.as_middleware()).",
                stacklevel=2,
            )
        pending = self._pending

        async def _middleware(ctx: Any, next: Any) -> None:
            chat_id = ctx.chat_id
            user_id = ctx.user_id
            # callbacks have callback_data; channel posts have user_id=None
            if (
                chat_id is not None
                and user_id is not None
                and ctx.callback_data is None
            ):
                future = pending.get((chat_id, user_id))
                if future is not None and not future.done():
                    future.set_result(ctx.message.text or "")
                    del pending[(chat_id, user_id)]
                    return  # consumed — do not call next()
            await next()

        return _middleware

    async def __call__(
        self,
        ctx: Any,
        text: str,
        reply_markup: Any | None = None,
    ) -> str:
        """
        Send a question and wait for the next text reply from the same user.

        Rules:
        - Requires chat_id and user_id — raises TitanError in channel handlers.
        - One pending ask per (chat_id, user_id) at a time — raises TitanError otherwise.
        - The captured reply bypasses all remaining middleware and handlers.
        - No persistence — pending asks are lost on bot restart.
        """
        chat_id = ctx.chat_id
        user_id = ctx.user_id

        if chat_id is None or user_id is None:
            raise TitanError(
                "ask() requires both chat_id and user_id. "
                "It cannot be used in channel handlers."
            )

        key = (chat_id, user_id)
        if key in self._pending and not self._pending[key].done():
            raise TitanError(
                f"An active ask() is already waiting for user {user_id} "
                "in this chat. Only one pending ask per user per chat is allowed at a time."
            )

        await ctx.reply(text, reply_markup=reply_markup)

        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        self._pending[key] = future

        try:
            return await future
        except asyncio.CancelledError:
            self._pending.pop(key, None)
            raise
