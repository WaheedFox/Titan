# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.bot

المحرك الأساسي لـ Titan.

مسؤوليته:
- تشغيل البوت
- جلب التحديثات من Telegram
- تمريرها إلى Update ثم Context
- تنفيذ الـ handlers المسجلة

لا يحتوي على أي منطق خاص بالبوت نفسه.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Awaitable

from titan.errors import TitanError
from titan.telegram import Telegram
from titan.update import Update
from titan.ctx import Context
from titan.alias import AliasMap
from titan.middleware import MiddlewareChain, Middleware
from titan.adapter import TelegramAdapter
from titan.router import Router


Handler = Callable[[Context], Awaitable[Any]]
ErrorHandler = Callable[[Context, Exception], Awaitable[None]]
OffsetCallback = Callable[[int], None]

_BACKOFF_BASE: float = 1.0
_BACKOFF_MAX: float = 30.0


class Titan:
    """
    الكلاس الرئيسي الذي يستخدمه المطور.

    هذا هو Public API الخاص بـ Titan.
    """

    # -------------------------
    # Logging
    # -------------------------
    def _log(self, msg: str) -> None:
        print(f"[Titan] {msg}")

    async def _handle_error(self, ctx: Context, exc: Exception) -> None:
        if self._error_handler is not None:
            try:
                await self._error_handler(ctx, exc)
            except Exception as inner:
                self._log(f"Exception raised inside error handler: {inner}")
        else:
            self._log(f"Unhandled exception: {exc}")

    def __init__(self, token: str) -> None:
        self._api = Telegram(token)
        self.telegram = TelegramAdapter(self._api)

        self.commands: dict[str, Handler] = {}
        self.handlers: dict[str, list[Handler]] = {}
        self.callback_handlers: dict[str, Handler] = {}
        self.aliases = AliasMap()
        self.middleware_chain = MiddlewareChain()
        self.banned_users: set[int] = set()
        self._error_handler: ErrorHandler | None = None

        self.offset: int = 0

    # -------------------------
    # Utilities
    # -------------------------
    def _extract_command(self, text: str) -> str | None:
        """
        استخراج اسم الأمر من النص.

        يدعم:
        - /start
        - /start@BotName
        """

        if not text.startswith("/"):
            return None

        command = text.split(maxsplit=1)[0][1:]
        if not command:
            return None

        return command.split("@", 1)[0]

    # -------------------------
    # Registration
    # -------------------------
    def on(self, event: str):
        """
        تسجيل handler لحدث معين.

        يدعم أي اسم حدث:
        - "message"
        - "channel"
        - "callback"
        - "new_member"
        - "left_member"
        """

        def decorator(func: Handler):
            self.handlers.setdefault(event, []).append(func)
            return func
        return decorator

    def command(self, name: str):
        """
        تسجيل أمر محدد مثل /start أو /help.

        يرمي TitanError إذا كان الأمر مسجلاً مسبقاً.
        """

        def decorator(func: Handler):
            if name in self.commands:
                raise TitanError(
                    f"Command '{name}' is already registered. "
                    "Each command can only have one handler. "
                    "Use @bot.on('message') if you need multiple handlers for the same input."
                )
            self.commands[name] = func
            return func
        return decorator

    def middleware(self, fn: Middleware) -> Middleware:
        """
        تسجيل middleware تُنفَّذ قبل كل handler.

        كل middleware تستلم ctx وnext.
        استدعاء next() → يكمل الـ update.
        عدم استدعاء next() → يتوقف الـ update هنا.

        مثال:
            @bot.middleware
            async def guard(ctx, next):
                if ctx.is_banned:
                    return
                await next()
        """

        self.middleware_chain.add(fn)
        return fn

    def error_handler(self, fn: ErrorHandler) -> ErrorHandler:
        """
        تسجيل دالة تُستدعى عند حدوث استثناء غير معالج في أي handler.

        التوقيع المطلوب:
            async def on_error(ctx, exc):
                ...

        إذا لم يُسجَّل error handler، يُطبع الخطأ في stdout.
        استثناء داخل error handler نفسه يُطبع ولا يُسكَت.

        مثال:
            @bot.error_handler
            async def on_error(ctx, exc):
                await ctx.reply("Something went wrong.")
                raise exc  # إعادة الرفع اختيارية
        """

        self._error_handler = fn
        return fn

    def alias(self, alias: str, target: str) -> None:
        """
        تعريف اسم بديل لـ method موجودة في Context.

        مثال:
            bot.alias("say", "reply")

        الاسم الأصلي يبقى ثابتاً بدون أي تغيير.
        إذا كان الاسم الهدف غير موجود في Context → TitanError.
        """

        self.aliases.register(alias, target)

    def include(self, router: Router) -> None:
        """
        دمج handlers مسجلة في Router داخل البوت.

        ينقل:
        - handlers → bot.handlers
        - commands → bot.commands
        - callback_handlers → bot.callback_handlers

        يرمي TitanError عند تعارض في command أو callback_data.

        تحذير: استدعاء include() على نفس الـ Router مرتين يُضاعف handlers
        المسجلة عبر on() بصمت دون خطأ. commands وcallbacks محمية من التكرار،
        لكن on() handlers ليست كذلك. كل router يجب أن يُدمج مرة واحدة فقط.
        """

        for event, handlers in router.handlers.items():
            self.handlers.setdefault(event, []).extend(handlers)

        for name, handler in router.commands.items():
            if name in self.commands:
                raise TitanError(
                    f"Command '{name}' is already registered. "
                    "Each command can only have one handler."
                )
            self.commands[name] = handler

        for data, handler in router.callback_handlers.items():
            if data in self.callback_handlers:
                raise TitanError(
                    f"Callback data '{data}' is already registered. "
                    "Each callback_data value can only have one handler."
                )
            self.callback_handlers[data] = handler

    def callback(self, data: str):
        """
        تسجيل handler لزر callback محدد بناءً على callback_data.

        يرمي TitanError إذا كانت الـ data مسجلة مسبقاً.

        مثال:
            @bot.callback("yes")
            async def on_yes(ctx):
                await ctx.answer_callback()
                await ctx.reply("اخترت نعم")

        إذا لم يوجد handler مطابق لـ data، يُرسل الـ update
        إلى on("callback") إن وجد.
        """

        def decorator(func: Handler):
            if data in self.callback_handlers:
                raise TitanError(
                    f"Callback data '{data}' is already registered. "
                    "Each callback_data value can only have one handler. "
                    "Use a unique callback_data string per button."
                )
            self.callback_handlers[data] = func
            return func
        return decorator

    # -------------------------
    # Dispatch
    # -------------------------
    async def _dispatch(self, event: str, ctx: Context) -> None:
        """تشغيل جميع الـ handlers المسجلة لحدث معين."""

        for handler in self.handlers.get(event, []):
            try:
                await handler(ctx)
            except Exception as e:
                await self._handle_error(ctx, e)

    # -------------------------
    # Update handling
    # -------------------------
    async def _handle_update(self, raw_update: dict[str, Any]) -> None:
        update = Update(raw_update)
        ctx = Context(update, self._api)

        if ctx.user_id is not None:
            ctx.is_banned = ctx.user_id in self.banned_users

        self.aliases.apply(ctx)

        async def dispatch() -> None:
            # channel
            if update.channel_post is not None:
                await self._dispatch("channel", ctx)
                return

            # callback_query — route by data first, fallback to on("callback")
            if update.callback_query is not None:
                data = ctx.callback_data
                specific = self.callback_handlers.get(data) if data else None
                if specific is not None:
                    try:
                        await specific(ctx)
                    except Exception as e:
                        await self._handle_error(ctx, e)
                else:
                    await self._dispatch("callback", ctx)
                return

            # semantic event aliases — قبل dispatch الرسائل العامة
            raw_msg = update.get_message()
            if raw_msg:
                if raw_msg.get("new_chat_members"):
                    await self._dispatch("new_member", ctx)
                    return
                if raw_msg.get("left_chat_member"):
                    await self._dispatch("left_member", ctx)
                    return

            # message / command
            text = update.text
            command = self._extract_command(text) if text else None

            if command is not None:
                handler = self.commands.get(command)
                if handler is not None:
                    try:
                        await handler(ctx)
                    except Exception as e:
                        await self._handle_error(ctx, e)
                    return

            await self._dispatch("message", ctx)

        try:
            await self.middleware_chain.run(ctx, dispatch)
        except Exception as e:
            await self._handle_error(ctx, e)

    # -------------------------
    # Runtime
    # -------------------------
    async def run_async(
        self,
        debug: bool = False,
        offset: int = 0,
        on_offset: OffsetCallback | None = None,
    ) -> None:
        self.offset = offset
        await self._api.start()
        self._log("Bot started")

        try:
            me = await self._api.get_me()
            username = me.get("username", "unknown")
            self._log(f"Running as @{username}")
        except Exception:
            pass

        backoff: float = 0.0

        try:
            while True:
                try:
                    updates = await self._api.get_updates(
                        offset=self.offset + 1
                    )

                    backoff = 0.0

                    for raw in updates:
                        update_id = raw.get("update_id")
                        if update_id is None:
                            self._log(f"Skipping update with no update_id: {raw}")
                            continue

                        self.offset = update_id

                        if debug:
                            self._log(f"update received: {raw}")

                        await self._handle_update(raw)

                        if on_offset is not None:
                            on_offset(self.offset)

                except Exception as e:
                    backoff = min(
                        backoff * 2 if backoff else _BACKOFF_BASE,
                        _BACKOFF_MAX,
                    )
                    self._log(f"Polling error: {e}. Retrying in {backoff:.0f}s...")
                    await asyncio.sleep(backoff)

        finally:
            self._log("Bot stopped")
            await self._api.close()

    # -------------------------
    # Entry point
    # -------------------------
    def run(
        self,
        debug: bool = False,
        offset: int = 0,
        on_offset: OffsetCallback | None = None,
    ) -> None:
        asyncio.run(self.run_async(debug=debug, offset=offset, on_offset=on_offset))
