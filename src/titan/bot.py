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
import logging
from typing import Any, Callable, Awaitable

_log = logging.getLogger("titan")

from titan.errors import TitanError
from titan.telegram import Telegram
from titan.update import Update
from titan.ctx import Context
from titan.middleware import MiddlewareChain, Middleware
from titan.adapter import TelegramAdapter
from titan.router import Router
from titan.models.capabilities import BotCapabilities
from titan.health.models import HealthFinding
from titan.health.runner import run_checks
from titan.inspector import BotSnapshot, build_snapshot
from titan.links.manager import LinksManager
from titan.privacy.registry import UserDataRegistry
from titan.validation import validate_handler, validate_middleware, validate_error_handler


Handler = Callable[[Context], Awaitable[Any]]
ErrorHandler = Callable[[Context, Exception], Awaitable[None]]
MydataFormatHook = Callable[..., Awaitable[str]]
ForgetmeCompleteHook = Callable[..., Awaitable[None]]
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
        _log.info(msg)

    async def _handle_error(self, ctx: Context, exc: Exception) -> None:
        if self._error_handler is not None:
            try:
                await self._error_handler(ctx, exc)
            except Exception as inner:
                _log.error("Exception raised inside error handler", exc_info=inner)
        else:
            _log.error("Unhandled exception", exc_info=exc)

    @property
    def router_count(self) -> int:
        """عدد الـ routers المدمجة عبر bot.include()."""
        return len(self._included_routers)

    @property
    def capabilities(self) -> "BotCapabilities | None":
        """
        يعرض ما هو معروف حالياً عن قدرات البوت على مستوى الحساب.

        يُعيد None عندما لا تكون المعلومات متاحة بعد.
        لا يُجري أي API call — يعكس حالة الكاش الحالية فقط،
        ولا يضمن توفّر البيانات في أي وقت.

        هذه القدرات عامة وثابتة — لا تتعلق بأي update أو شات محدد.

        مثال:
            if bot.capabilities and bot.capabilities.can_join_groups:
                ...
        """
        me = self._api._me
        if me is None:
            return None
        return BotCapabilities(me)

    def __init__(self, token: str) -> None:
        self._api = Telegram(token)
        self.telegram = TelegramAdapter(self._api)

        self.commands: dict[str, Handler] = {}
        self.handlers: dict[str, list[Handler]] = {}
        self.callback_handlers: dict[str, Handler] = {}
        self.middleware_chain = MiddlewareChain()
        self.banned_users: set[int] = set()
        self._error_handler: ErrorHandler | None = None
        self._included_routers: set[int] = set()
        self._included_router_objects: list[Router] = []
        self._on_offset: OffsetCallback | None = None

        # Internal: tracks where each command/callback was first registered.
        # Used to produce actionable conflict messages in include().
        self._command_sources: dict[str, str] = {}
        self._callback_sources: dict[str, str] = {}

        # أوامر محجوزة داخلياً من Titan — لا تظهر في bot.commands
        # حتى لا تؤثر على Inspector أو Health checks.
        # تُفعَّل في routing بنفس آلية bot.commands.
        self._reserved_commands: dict[str, Handler] = {}

        self.offset: int = 0

        # Per-chat dispatch queues and workers.
        # Each chat_id gets its own asyncio.Queue and a dedicated worker Task.
        # Updates within a chat are dispatched in arrival order (FIFO).
        # Handlers within the same chat may run concurrently if they suspend
        # (e.g. while waiting for ask() to resolve a pending Future).
        self._chat_queues: dict[int, asyncio.Queue] = {}
        self._chat_workers: dict[int, asyncio.Task] = {}

        # Message Links Protocol — يُهيَّأ تلقائياً، لا opt-in.
        self.links = LinksManager()
        self._register_link_command()

        # Privacy Protocol — ADR-015/016/017
        self._user_data_registry = UserDataRegistry()
        self._mydata_format_hook: MydataFormatHook | None = None
        self._forgetme_complete_hook: ForgetmeCompleteHook | None = None
        self._register_privacy_commands()

    # -------------------------
    # Privacy Protocol
    # -------------------------
    def _register_privacy_commands(self) -> None:
        """
        تسجيل /mydata و/forgetme كأوامر محجوزة لـ Privacy Protocol.

        يحدث تلقائياً في __init__ — المطوّر لا يستدعي هذا.
        محاولة تسجيل @bot.command("mydata") أو @bot.command("forgetme")
        ستُثير TitanError برسالة صريحة.
        """
        from titan.privacy.handler import handle_mydata_command, handle_forgetme_command

        registry = self._user_data_registry
        bot_ref = self

        async def _mydata_handler(ctx: Context) -> None:
            await handle_mydata_command(ctx, registry, bot_ref._mydata_format_hook)

        async def _forgetme_handler(ctx: Context) -> None:
            await handle_forgetme_command(ctx, registry, bot_ref._forgetme_complete_hook)

        _privacy_source = (
            "reserved by Titan's privacy protocol — "
            "this command is part of the user data transparency contract "
            "and cannot be overridden"
        )

        self._reserved_commands["mydata"] = _mydata_handler
        self._command_sources["mydata"] = _privacy_source

        self._reserved_commands["forgetme"] = _forgetme_handler
        self._command_sources["forgetme"] = _privacy_source

    def declare_user_data(self, module: object) -> None:
        """
        تسجيل module خارجي (Third-party) في User Data Registry.

        يُستخدم للـ modules التي كتبها المطوّر خارج titan.* — مرة واحدة
        في مرحلة التهيئة. بعدها: erase_user() وdata_held_for() يشملانه
        تلقائياً.

        يتحقق من تطبيق UserDataModule Protocol ويرفع TitanError
        برسالة واضحة إذا كان module ناقصاً.

        إذا كان الـ module يحمل خاصية _privacy_registered (مثل AskManager)،
        يُعيَّنها True تلقائياً حتى لا يُطلق as_middleware() تحذيراً بعدها.

        مثال:
            class MyPrefs:
                component_name = "preferences"
                data_description = "User preferences"
                async def data_for(self, user_id): ...
                async def erase(self, user_id): ...

            bot.declare_user_data(MyPrefs())

            # مع AskManager يدوياً:
            ask = AskManager()
            bot.declare_user_data(ask)           # يُسجِّل ويُعيِّن الـ flag
            bot.middleware(ask.as_middleware())  # لا تحذير
        """
        self._user_data_registry.register(module)
        # إذا كان الـ module يدعم privacy_registered flag (مثل AskManager)
        # يُعيَّن بعد نجاح التسجيل — يمنع التحذير في as_middleware() لاحقاً.
        if hasattr(module, "_privacy_registered"):
            module._privacy_registered = True

    def enable_ask(self) -> "AskManager":
        """
        تفعيل AskManager وتسجيله تلقائياً في User Data Registry.

        هذه النقطة الرسمية لـ AskManager — الاستدعاء الواحد يُنشئ
        الـ AskManager ويُسجّله في Registry ويُضيف middleware.

        المُعاد: AskManager callable جاهز للاستخدام مباشرةً.

        مثال:
            ask = bot.enable_ask()

            @bot.command("start")
            async def start(ctx):
                name = await ask(ctx, "ما اسمك؟")
                await ctx.reply(f"أهلاً {name}!")

        ADR-016: First-party اختياري → تسجيل تلقائي عند الربط الرسمي.
        """
        from titan.extras.ask import AskManager

        ask = AskManager()
        self._user_data_registry.register(ask)
        ask._privacy_registered = True   # يمنع التحذير في as_middleware()
        self.middleware_chain.add(ask.as_middleware())
        return ask

    def on_mydata_format(self, fn: MydataFormatHook) -> MydataFormatHook:
        """
        تسجيل hook لتنسيق تقرير /mydata.

        التوقيع المطلوب:
            async def format_report(ctx, report: MappingProxyType) -> str:
                ...

        report: read-only — MappingProxyType.
        أي محاولة تعديل أو حذف مفتاح تُثير TypeError من Python مباشرةً.
        المطوّر يتحكم في *كيف* يُعرض التقرير — لا في *ماذا* يحتوي.

        مثال:
            @bot.on_mydata_format
            async def format_report(ctx, report):
                lines = [f"• {k}: {v['count']}" for k, v in report.items()]
                return "بياناتك:\\n" + "\\n".join(lines)
        """
        self._mydata_format_hook = fn
        return fn

    def on_forgetme_complete(self, fn: ForgetmeCompleteHook) -> ForgetmeCompleteHook:
        """
        تسجيل hook تُستدعى بعد اكتمال المحو عبر /forgetme.

        التوقيع المطلوب:
            async def after_erasure(ctx) -> None:
                ...

        يُستدعى *بعد* نجاح erase_user() فقط — لا قبله بأي حال.
        مناسب لحذف بيانات خارج Titan يديرها المطوّر.

        لا يوجد on_forgetme_before — الغياب قصد لا سهو.

        مثال:
            @bot.on_forgetme_complete
            async def after_erasure(ctx):
                await my_external_db.delete_user(ctx.user_id)
        """
        self._forgetme_complete_hook = fn
        return fn

    async def erase_user(self, user_id: int) -> None:
        """
        محو حقيقي لكل User Data مُسجَّلة لهذا المستخدم.

        يُوزَّع على كل module في UserDataRegistry — اليوم وكل module
        يُضاف مستقبلاً. Module جديد يُسجَّل = يُشمَل تلقائياً.

        هذا عقد نهائي — لا cache، لا index، لا إمكانية استرجاع عبر Titan.

        لا يشمل: بيانات المطوّر خارج Titan، Permanent Resource Identity.

        مثال:
            await bot.erase_user(user_id=123456789)
        """
        await self._user_data_registry.erase_user(user_id)

    async def data_held_for(self, user_id: int) -> dict:
        """
        يجمع ما تعرفه Titan عن هذا المستخدم من كل module مُسجَّل.

        المُعاد:
            {
                "pending_asks": {
                    "description": "Unfinished interactions waiting for user reply",
                    "count": 1
                },
                ...
            }

        يُستخدم داخلياً بواسطة /mydata. متاح أيضاً للمطوّر مباشرةً.

        مثال:
            report = await bot.data_held_for(user_id=123456789)
        """
        return await self._user_data_registry.data_held_for(user_id)

    # -------------------------
    # Message Links Protocol
    # -------------------------
    def _register_link_command(self) -> None:
        """
        تسجيل /link كأمر محجوز لـ Message Links Protocol.

        يحدث تلقائياً في __init__ — المطور لا يستدعي هذا.
        محاولة تسجيل @bot.command("link") ستُثير TitanError
        برسالة صريحة تشير لـ Message Links Protocol.
        """
        from titan.links.handler import handle_link_command

        links = self.links

        async def _link_handler(ctx: Context) -> None:
            await handle_link_command(ctx, links)

        # /link يُخزَّن في _reserved_commands لا commands —
        # كي لا يظهر في Inspector أو يؤثر على Health checks.
        # يُسجَّل في _command_sources فقط لاكتشاف التعارض.
        self._reserved_commands["link"] = _link_handler
        self._command_sources["link"] = (
            "reserved by Message Links Protocol — "
            "this command is part of Titan's identity system and cannot be overridden"
        )

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
            validate_handler(func, kind="event handler")
            self.handlers.setdefault(event, []).append(func)
            return func
        return decorator

    def command(self, name: str):
        """
        تسجيل أمر محدد مثل /start أو /help.

        يرمي TitanError إذا كان الأمر مسجلاً مسبقاً.
        """

        def decorator(func: Handler):
            validate_handler(func, kind="command handler")
            # يفحص bot.commands وكذلك _command_sources لاكتشاف الأوامر المحجوزة
            if name in self.commands or name in self._command_sources:
                source = self._command_sources.get(name, "elsewhere")
                raise TitanError(
                    f"Command '{name}' is already registered ({source}). "
                    "Each command can only have one handler. "
                    "Use @bot.on('message') if you need multiple handlers for the same input."
                )
            self.commands[name] = func
            self._command_sources[name] = "directly with @bot.command()"
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

        validate_middleware(fn)
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

        validate_error_handler(fn)
        self._error_handler = fn
        return fn

    def include(self, router: Router) -> None:
        """
        دمج handlers مسجلة في Router داخل البوت.

        ينقل:
        - handlers → bot.handlers
        - commands → bot.commands
        - callback_handlers → bot.callback_handlers

        يرمي TitanError عند تعارض في command أو callback_data،
        أو إذا تم تمرير نفس الـ Router مرتين.
        """

        if id(router) in self._included_routers:
            raise TitanError(
                "This router has already been included. "
                "Each Router instance can only be passed to bot.include() once."
            )

        for event, handlers in router.handlers.items():
            for handler in handlers:
                validate_handler(handler, kind="event handler")
            self.handlers.setdefault(event, []).extend(handlers)

        for name, handler in router.commands.items():
            validate_handler(handler, kind="command handler")
            # يفحص bot.commands وكذلك _command_sources لاكتشاف الأوامر المحجوزة
            if name in self.commands or name in self._command_sources:
                source = self._command_sources.get(name, "elsewhere")
                raise TitanError(
                    f"Command '{name}' conflicts on include(): already registered "
                    f"{source}. Each command can only have one handler."
                )
            self.commands[name] = handler
            self._command_sources[name] = "via a previously included router"

        for data, handler in router.callback_handlers.items():
            validate_handler(handler, kind="callback handler")
            if data in self.callback_handlers:
                source = self._callback_sources.get(data, "elsewhere")
                raise TitanError(
                    f"Callback data '{data}' conflicts on include(): already registered "
                    f"{source}. Each callback_data value can only have one handler."
                )
            self.callback_handlers[data] = handler
            self._callback_sources[data] = "via a previously included router"

        self._included_routers.add(id(router))
        self._included_router_objects.append(router)

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
            validate_handler(func, kind="callback handler")
            if data in self.callback_handlers:
                source = self._callback_sources.get(data, "elsewhere")
                raise TitanError(
                    f"Callback data '{data}' is already registered ({source}). "
                    "Each callback_data value can only have one handler. "
                    "Use a unique callback_data string per button."
                )
            self.callback_handlers[data] = func
            self._callback_sources[data] = "directly with @bot.callback()"
            return func
        return decorator

    # -------------------------
    # Inspector
    # -------------------------
    def inspect(self) -> BotSnapshot:
        """
        تُرجع snapshot وصفية عن الحالة التسجيلية الكاملة للبوت.

        تعمل في أي وقت — قبل bot.run() وبعده.
        لا تُقيّم، لا تُصدر أحكاماً. تصف فقط ما تم تسجيله.

        الحقول المُرجعة:
            commands:               أسماء الأوامر المسجلة
            callbacks:              قيم callback_data المسجلة
            events:                 dict من اسم الحدث → عدد handlers
            middleware_count:       عدد الـ middlewares
            has_error_handler:      وجود error handler
            included_router_count:  عدد الـ routers المدمجة
            capabilities_available: توفر بيانات الحساب (بعد bot.run())

        مثال:
            snapshot = bot.inspect()
            print(snapshot.commands)          # ("help", "start")
            print(snapshot.middleware_count)  # 2
            print(snapshot.has_error_handler) # True

        للتقييم والمشكلات، استخدم bot.health() بدلاً من هذه الطريقة.
        """
        return build_snapshot(self)

    # -------------------------
    # Health
    # -------------------------
    def health(self) -> list[HealthFinding]:
        """
        تُقيّم حالة البوت الهيكلية والتشغيلية.

        تُعيد قائمة من الـ findings. إذا كانت القائمة فارغة — البوت سليم.
        كل finding يحمل: level (ERROR/WARNING/INFO)، code، message.

        الفحوصات الهيكلية تعمل دائماً (قبل وبعد bot.run()).
        الفحوصات التشغيلية (capabilities) تعمل فقط بعد bot.run()
        عندما تكون bot.capabilities متاحة — تُتجاهل بصمت قبل ذلك.

        Project Health تُقيّم ولا تُصلح.
        قرار التصرف بناءً على النتائج يعود للمطور.

        مثال:
            for finding in bot.health():
                print(f"[{finding.level}] {finding.message}")
        """
        return run_checks(self)

    def lint(self) -> list["LintFinding"]:
        """
        تفحص ما إذا كان تصميم البوت يحترم فلسفة Titan واتفاقياتها.

        تُعيد قائمة من LintFinding. إذا كانت فارغة — لا انتهاكات مكتشفة.
        كل finding يحمل: level (WARNING في v1)، code، message، hint.

        الفرق عن الأدوات الأخرى:
          bot.inspect() → ماذا يحتوي البوت؟ (وصف، لا حكم)
          bot.health()  → هل البنية مكتملة؟ (ERROR/WARNING/INFO)
          bot.lint()    → هل الاتفاقيات محترمة؟ (WARNING فقط)

        تعمل دائماً pre/post run() ما عدا TITAN_LINT_003 (on_offset async)
        التي تتطلب استدعاء run() أولاً.

        مثال:
            for finding in bot.lint():
                print(finding)
        """
        from titan.lint.engine import run_lint
        return run_lint(self)

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
    # Event Feed
    # -------------------------
    async def feed_update(self, update: dict[str, Any]) -> None:
        """
        نقطة الدخول الرسمية لتغذية Titan بـ update من أي مصدر غير
        Telegram polling.

        تمرر الـ update عبر نفس مسار المعالجة الحقيقي الذي يستخدمه
        run_async() — middleware ثم routing ثم الـ handler المطابق —
        بدون أي منطق موازٍ أو مختصر.

        الاستخدامات: titan.playground، اختبارات متقدمة، ومصادر أحداث
        مستقبلية غير polling (مثل Userbot Support).

        مثال:
            await bot.feed_update({
                "update_id": 1,
                "message": {"message_id": 1, "chat": {"id": 1}, "text": "/start"},
            })
        """
        await self._handle_update(update)

    # -------------------------
    # Update handling
    # -------------------------
    async def _handle_update(self, raw_update: dict[str, Any]) -> None:
        update = Update(raw_update)
        ctx = Context(update, self._api, links=self.links)

        if ctx.user_id is not None:
            ctx.is_banned = ctx.user_id in self.banned_users

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

            # update with no route — unsupported or unknown type.
            # سياسة صريحة: لا handler، لا خطأ، لا أثر على polling.
            # المسؤولية تعيش هنا في dispatch، لا في طبقة الترجمة.
            # (تحقيق: docs/internal/investigations/api-evolution-unknown-types.md)
            raw_msg = update.get_message()
            if raw_msg is None:
                _log.debug(
                    "Update with no route dropped (unsupported or unknown type): "
                    "update_id=%s",
                    raw_update.get("update_id"),
                )
                return

            # semantic event aliases
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
                handler = self.commands.get(command) or self._reserved_commands.get(command)
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
    # Per-chat dispatch
    # -------------------------

    @staticmethod
    def _chat_id_from_raw(raw: dict) -> int | None:
        """
        Extract chat_id from a raw Telegram update dict without full parsing.

        Covers all update types that carry a chat: message, edited_message,
        channel_post, edited_channel_post, my_chat_member, chat_member,
        and callback_query.  Returns None for any update type that has no
        associated chat (e.g. inline_query, shipping_query).
        """
        for key in (
            "message",
            "edited_message",
            "channel_post",
            "edited_channel_post",
            "my_chat_member",
            "chat_member",
        ):
            entry = raw.get(key)
            if entry:
                chat = entry.get("chat")
                if chat:
                    return chat.get("id")
        cq = raw.get("callback_query")
        if cq:
            msg = cq.get("message") or {}
            return (msg.get("chat") or {}).get("id")
        return None

    def _ensure_chat_worker(self, chat_id: int) -> "asyncio.Queue[dict | None]":
        """
        Return the dispatch queue for *chat_id*, creating a worker Task
        on first access.  The worker persists for the lifetime of run_async.
        """
        if chat_id not in self._chat_queues:
            queue: asyncio.Queue = asyncio.Queue()
            self._chat_queues[chat_id] = queue
            task = asyncio.create_task(
                self._chat_worker(chat_id, queue),
                name=f"titan-chat-{chat_id}",
            )
            self._chat_workers[chat_id] = task
        return self._chat_queues[chat_id]

    async def _chat_worker(self, chat_id: int, queue: "asyncio.Queue[dict | None]") -> None:
        """
        Worker coroutine for a single chat.

        Updates are dispatched in arrival order (FIFO).  Each update is
        launched as an independent asyncio.Task so that a handler that
        suspends (e.g. while awaiting ask()) does not block subsequent
        updates for the same chat — which would otherwise cause a deadlock
        when the reply that resolves the ask() Future arrives.

        Ordering guarantee: dispatch *start* order is preserved within a
        chat.  Handler *completion* order is not guaranteed and must not
        be relied upon.
        """
        while True:
            raw = await queue.get()
            if raw is None:          # shutdown sentinel
                break
            asyncio.create_task(
                self._handle_update(raw),
                name=f"titan-update-{raw.get('update_id')}",
            )

    # -------------------------
    # Runtime
    # -------------------------
    async def run_async(
        self,
        debug: bool = False,
        offset: int = 0,
        on_offset: OffsetCallback | None = None,
    ) -> None:
        self._on_offset = on_offset
        self.offset = offset
        await self._api.start()
        self._log("Bot started")

        try:
            me = await self._api.get_me()
            username = me.get("username", "unknown")
            self._log(f"Running as @{username}")
        except Exception as exc:
            _log.warning(
                "Could not fetch bot identity at startup: %s — continuing.", exc
            )

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

                        if debug:
                            self._log(f"update received: {raw}")

                        chat_id = self._chat_id_from_raw(raw)
                        if chat_id is not None:
                            await self._ensure_chat_worker(chat_id).put(raw)
                        else:
                            # Updates with no chat context (inline queries, etc.)
                            # are dispatched directly as independent Tasks.
                            asyncio.create_task(
                                self._handle_update(raw),
                                name=f"titan-update-{update_id}",
                            )

                        self.offset = update_id

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
            # Send shutdown sentinel to every chat worker and wait for them
            # to drain before closing the API connection.
            for queue in self._chat_queues.values():
                await queue.put(None)
            if self._chat_workers:
                await asyncio.gather(
                    *self._chat_workers.values(), return_exceptions=True
                )
            self._chat_queues.clear()
            self._chat_workers.clear()
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
