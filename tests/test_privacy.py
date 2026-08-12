"""
tests/test_privacy.py

اختبارات نظام الخصوصية — User Data Registry & Privacy Commands.

تُغطّي الحالات الخمس الجوهرية من docs/internal/expected-failure-cases.md:
    1. تسجيل /mydata أو /forgetme يدوياً → TitanError
    2. Module ناقص عند declare_user_data → TitanError
    3. Hook تحاول تعديل report → TypeError
    4. /forgetme يُوزَّع erase على كل modules
    5. Module مُسجَّل يظهر في /mydata تلقائياً
"""

from __future__ import annotations

import asyncio
import pytest
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

from titan import Titan, TitanError
from titan.privacy.registry import UserDataRegistry
from titan.extras.ask import AskManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_bot() -> Titan:
    """بوت بـ token وهمي — لا يتصل بـ Telegram."""
    with patch("titan.telegram.Telegram.__init__", return_value=None):
        bot = Titan.__new__(Titan)
        from titan.telegram import Telegram
        bot._api = MagicMock()
        bot._api._me = None
        from titan.adapter import TelegramAdapter
        bot.telegram = TelegramAdapter(bot._api)
        bot.commands = {}
        bot.handlers = {}
        bot.callback_handlers = {}
        from titan.middleware import MiddlewareChain
        bot.middleware_chain = MiddlewareChain()
        bot.banned_users = set()
        bot._error_handler = None
        bot._included_routers = set()
        bot._included_router_objects = []
        bot._on_offset = None
        bot._command_sources = {}
        bot._callback_sources = {}
        bot._reserved_commands = {}
        bot.offset = 0
        from titan.links.manager import LinksManager
        bot.links = LinksManager()
        bot._user_data_registry = UserDataRegistry()
        bot._mydata_format_hook = None
        bot._forgetme_complete_hook = None
        bot._register_link_command()
        bot._register_privacy_commands()
        return bot


class GoodModule:
    """Module صحيح يُطبّق كل العقد."""
    component_name = "test_data"
    data_description = "Test user data"

    def __init__(self):
        self.erased_ids: list[int] = []

    async def data_for(self, user_id: int) -> dict:
        return {"count": 1, "user": user_id}

    async def erase(self, user_id: int) -> None:
        self.erased_ids.append(user_id)


class MissingEraseModule:
    """Module ينقصه erase()."""
    component_name = "bad_module"
    data_description = "Missing erase"

    async def data_for(self, user_id: int) -> dict:
        return {}


class MissingNameModule:
    """Module ينقصه component_name."""
    data_description = "Missing name"

    async def data_for(self, user_id: int) -> dict:
        return {}

    async def erase(self, user_id: int) -> None:
        pass


# ---------------------------------------------------------------------------
# Case 1: تسجيل /mydata أو /forgetme يدوياً → TitanError
# ---------------------------------------------------------------------------

class TestReservedCommands:
    def test_mydata_reserved_via_bot_command(self):
        bot = make_bot()

        with pytest.raises(TitanError) as exc:
            @bot.command("mydata")
            async def handler(ctx): pass

        assert "mydata" in str(exc.value)
        assert "reserved" in str(exc.value).lower()

    def test_forgetme_reserved_via_bot_command(self):
        bot = make_bot()

        with pytest.raises(TitanError) as exc:
            @bot.command("forgetme")
            async def handler(ctx): pass

        assert "forgetme" in str(exc.value)
        assert "reserved" in str(exc.value).lower()

    def test_mydata_reserved_via_router_include(self):
        from titan.router import Router
        bot = make_bot()
        router = Router()

        @router.command("mydata")
        async def handler(ctx): pass

        with pytest.raises(TitanError) as exc:
            bot.include(router)

        assert "mydata" in str(exc.value)

    def test_forgetme_reserved_via_router_include(self):
        from titan.router import Router
        bot = make_bot()
        router = Router()

        @router.command("forgetme")
        async def handler(ctx): pass

        with pytest.raises(TitanError) as exc:
            bot.include(router)

        assert "forgetme" in str(exc.value)

    def test_mydata_and_forgetme_in_command_sources_from_init(self):
        """يجب أن يكون /mydata و/forgetme محجوزَين منذ __init__ مباشرةً."""
        bot = make_bot()
        assert "mydata" in bot._command_sources
        assert "forgetme" in bot._command_sources

    def test_mydata_and_forgetme_in_reserved_commands(self):
        bot = make_bot()
        assert "mydata" in bot._reserved_commands
        assert "forgetme" in bot._reserved_commands

    def test_reserved_commands_not_in_bot_commands(self):
        """الأوامر المحجوزة لا تظهر في bot.commands — لا تؤثر على inspect/health."""
        bot = make_bot()
        assert "mydata" not in bot.commands
        assert "forgetme" not in bot.commands


# ---------------------------------------------------------------------------
# Case 2: Module ناقص → TitanError عند التسجيل
# ---------------------------------------------------------------------------

class TestRegistryValidation:
    def test_missing_erase_raises_on_register(self):
        registry = UserDataRegistry()

        with pytest.raises(TitanError) as exc:
            registry.register(MissingEraseModule())

        assert "erase" in str(exc.value)
        assert "MissingEraseModule" in str(exc.value)

    def test_missing_component_name_raises_on_register(self):
        registry = UserDataRegistry()

        with pytest.raises(TitanError) as exc:
            registry.register(MissingNameModule())

        assert "component_name" in str(exc.value)

    def test_missing_all_raises_on_register(self):
        registry = UserDataRegistry()

        with pytest.raises(TitanError):
            registry.register(object())

    def test_good_module_registers_successfully(self):
        registry = UserDataRegistry()
        registry.register(GoodModule())
        assert len(registry) == 1
        assert "test_data" in registry.module_names

    def test_declare_user_data_on_bot_validates(self):
        bot = make_bot()

        with pytest.raises(TitanError):
            bot.declare_user_data(MissingEraseModule())

    def test_declare_user_data_on_bot_succeeds_for_good_module(self):
        bot = make_bot()
        bot.declare_user_data(GoodModule())
        assert "test_data" in bot._user_data_registry.module_names


# ---------------------------------------------------------------------------
# Case 3: Hook تحاول تعديل report → TypeError
# ---------------------------------------------------------------------------

class TestMydataHookReadOnly:
    def test_mappingproxy_rejects_item_deletion(self):
        data = {"pending_asks": {"description": "...", "count": 1}}
        read_only = MappingProxyType(data)

        with pytest.raises(TypeError):
            del read_only["pending_asks"]

    def test_mappingproxy_rejects_item_assignment(self):
        data = {"pending_asks": {"description": "...", "count": 1}}
        read_only = MappingProxyType(data)

        with pytest.raises(TypeError):
            read_only["new_key"] = "injected"

    @pytest.mark.asyncio
    async def test_mydata_handler_passes_mappingproxy_to_hook(self):
        from titan.privacy.handler import handle_mydata_command
        from titan.privacy.registry import UserDataRegistry

        registry = UserDataRegistry()
        registry.register(GoodModule())

        received_report = {}

        async def format_hook(ctx, report):
            received_report["type"] = type(report).__name__
            received_report["report"] = report
            return "formatted"

        ctx = MagicMock()
        ctx.user_id = 123
        ctx.reply = AsyncMock()

        await handle_mydata_command(ctx, registry, format_hook=format_hook)

        assert received_report["type"] == "mappingproxy"
        with pytest.raises(TypeError):
            received_report["report"]["injected"] = "attempt"


# ---------------------------------------------------------------------------
# Case 4: /forgetme يُوزَّع erase على كل modules
# ---------------------------------------------------------------------------

class TestForgetmeContract:
    @pytest.mark.asyncio
    async def test_forgetme_erases_all_registered_modules(self):
        from titan.privacy.handler import handle_forgetme_command
        from titan.privacy.registry import UserDataRegistry

        registry = UserDataRegistry()
        mod1 = GoodModule()
        mod2 = GoodModule()
        mod2.__class__ = type("SecondModule", (GoodModule,), {
            "component_name": "second_data",
            "data_description": "Second module data",
        })
        # نسخة منفصلة
        m1 = GoodModule()
        m2_cls = type("SecondModule", (), {
            "component_name": "second_data",
            "data_description": "Second module data",
            "erased_ids": [],
            "data_for": GoodModule.data_for,
            "erase": GoodModule.erase,
        })
        m2 = m2_cls()
        m2.erased_ids = []

        registry.register(m1)
        registry.register(m2)

        ctx = MagicMock()
        ctx.user_id = 999
        ctx.reply = AsyncMock()

        await handle_forgetme_command(ctx, registry)

        assert 999 in m1.erased_ids
        assert 999 in m2.erased_ids

    @pytest.mark.asyncio
    async def test_forgetme_erase_happens_before_hook(self):
        """erase_user() يجب أن يكتمل قبل استدعاء on_forgetme_complete."""
        from titan.privacy.handler import handle_forgetme_command
        from titan.privacy.registry import UserDataRegistry

        call_order: list[str] = []

        class OrderTracker:
            component_name = "tracker"
            data_description = "Order tracker"

            async def data_for(self, user_id: int) -> dict:
                return {"count": 0}

            async def erase(self, user_id: int) -> None:
                call_order.append("erase")

        registry = UserDataRegistry()
        registry.register(OrderTracker())

        async def complete_hook(ctx):
            call_order.append("hook")

        ctx = MagicMock()
        ctx.user_id = 1
        ctx.reply = AsyncMock()

        await handle_forgetme_command(ctx, registry, complete_hook=complete_hook)

        assert call_order == ["erase", "hook"], (
            "erase_user() must complete before on_forgetme_complete is called"
        )

    @pytest.mark.asyncio
    async def test_forgetme_sends_confirmation(self):
        from titan.privacy.handler import handle_forgetme_command
        from titan.privacy.registry import UserDataRegistry

        registry = UserDataRegistry()

        ctx = MagicMock()
        ctx.user_id = 42
        ctx.reply = AsyncMock()

        await handle_forgetme_command(ctx, registry)

        ctx.reply.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_erase_user_on_bot(self):
        bot = make_bot()
        module = GoodModule()
        bot.declare_user_data(module)

        await bot.erase_user(user_id=555)

        assert 555 in module.erased_ids


# ---------------------------------------------------------------------------
# Case 5: Module مُسجَّل يظهر في /mydata تلقائياً
# ---------------------------------------------------------------------------

class TestMydataAggregation:
    @pytest.mark.asyncio
    async def test_registered_module_appears_in_mydata_report(self):
        from titan.privacy.handler import handle_mydata_command
        from titan.privacy.registry import UserDataRegistry

        registry = UserDataRegistry()
        registry.register(GoodModule())

        sent_text: list[str] = []

        ctx = MagicMock()
        ctx.user_id = 77

        async def capture_reply(text, **kwargs):
            sent_text.append(text)

        ctx.reply = capture_reply

        await handle_mydata_command(ctx, registry)

        assert sent_text, "يجب أن يُرسل /mydata ردًّا"
        report_text = sent_text[0]
        assert "Test user data" in report_text

    @pytest.mark.asyncio
    async def test_no_modules_shows_empty_message(self):
        from titan.privacy.handler import handle_mydata_command
        from titan.privacy.registry import UserDataRegistry

        registry = UserDataRegistry()
        sent_text: list[str] = []

        ctx = MagicMock()
        ctx.user_id = 1

        async def capture_reply(text, **kwargs):
            sent_text.append(text)

        ctx.reply = capture_reply

        await handle_mydata_command(ctx, registry)

        assert "لا توجد" in sent_text[0]

    @pytest.mark.asyncio
    async def test_data_held_for_on_bot(self):
        bot = make_bot()
        bot.declare_user_data(GoodModule())

        report = await bot.data_held_for(user_id=10)

        assert "test_data" in report
        assert report["test_data"]["description"] == "Test user data"
        assert report["test_data"]["count"] == 1


# ---------------------------------------------------------------------------
# AskManager — UserDataModule Protocol
# ---------------------------------------------------------------------------

class TestAskManagerPrivacy:
    @pytest.mark.asyncio
    async def test_ask_manager_implements_user_data_module(self):
        registry = UserDataRegistry()
        ask = AskManager()
        # يجب أن يُسجَّل بدون خطأ
        registry.register(ask)
        assert "pending_asks" in registry.module_names

    @pytest.mark.asyncio
    async def test_ask_data_for_returns_count(self):
        ask = AskManager()
        loop = asyncio.get_event_loop()
        # أضف future وهمية
        fut: asyncio.Future[str] = loop.create_future()
        ask._pending[(100, 200)] = fut

        result = await ask.data_for(200)
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_ask_erase_cancels_pending(self):
        ask = AskManager()
        loop = asyncio.get_event_loop()
        fut: asyncio.Future[str] = loop.create_future()
        ask._pending[(100, 200)] = fut

        await ask.erase(200)

        assert (100, 200) not in ask._pending
        assert fut.cancelled()

    @pytest.mark.asyncio
    async def test_ask_erase_only_affects_target_user(self):
        ask = AskManager()
        loop = asyncio.get_event_loop()
        fut_target: asyncio.Future[str] = loop.create_future()
        fut_other: asyncio.Future[str] = loop.create_future()
        ask._pending[(100, 200)] = fut_target
        ask._pending[(100, 300)] = fut_other

        await ask.erase(200)

        assert (100, 200) not in ask._pending
        assert (100, 300) in ask._pending
        assert not fut_other.cancelled()

    def test_enable_ask_registers_in_registry(self):
        bot = make_bot()
        bot.enable_ask()
        assert "pending_asks" in bot._user_data_registry.module_names

    def test_enable_ask_does_not_warn(self):
        """bot.enable_ask() لا يُطلق تحذيراً — المسار الرسمي."""
        import warnings
        bot = make_bot()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            bot.enable_ask()
        privacy_warnings = [w for w in caught if "as_middleware" in str(w.message).lower()
                            or "registry" in str(w.message).lower()]
        assert not privacy_warnings, f"bot.enable_ask() should not warn, got: {privacy_warnings}"

    def test_manual_as_middleware_warns(self):
        """as_middleware() مباشرةً بدون تسجيل يُطلق UserWarning."""
        import warnings
        ask = AskManager()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ask.as_middleware()
        assert any("NOT registered" in str(w.message) or "unregistered" in str(w.message)
                   for w in caught), "Expected warning about unregistered AskManager"

    def test_declare_user_data_then_as_middleware_does_not_warn(self):
        """declare_user_data() ثم as_middleware() — لا تحذير."""
        import warnings
        bot = make_bot()
        ask = AskManager()
        bot.declare_user_data(ask)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ask.as_middleware()
        privacy_warnings = [w for w in caught if "NOT registered" in str(w.message)
                            or "unregistered" in str(w.message)]
        assert not privacy_warnings


# ---------------------------------------------------------------------------
# erase_user — failure handling
# ---------------------------------------------------------------------------

class TestEraseUserFailureHandling:
    @pytest.mark.asyncio
    async def test_erase_continues_after_one_module_fails(self):
        """فشل module واحد لا يمنع بقية الـ modules من استلام erase."""
        from titan.privacy.registry import UserDataRegistry

        class FailingModule:
            component_name = "failing"
            data_description = "يفشل دائماً"
            async def data_for(self, user_id): return {"count": 0}
            async def erase(self, user_id): raise RuntimeError("db down")

        erased: list[int] = []

        class SucceedingModule:
            component_name = "succeeding"
            data_description = "يعمل"
            async def data_for(self, user_id): return {"count": 1}
            async def erase(self, user_id): erased.append(user_id)

        registry = UserDataRegistry()
        registry.register(FailingModule())
        registry.register(SucceedingModule())

        # asyncio.gather(return_exceptions=True) يمسك الـ exception دون الاعتماد
        # على try/except في pytest-asyncio — أكثر ثباتاً عند التشغيل مع السوييت كاملاً.
        results = await asyncio.gather(
            registry.erase_user(42),
            return_exceptions=True,
        )
        raised = results[0]

        # نتحقق من اسم الكلاس لا هويتها — تجنباً لمشكلة إعادة تحميل الـ module في pytest
        assert type(raised).__name__ == "TitanError", f"Expected TitanError, got: {raised!r}"
        # SucceedingModule يجب أن تكون قد استلمت erase رغم فشل FailingModule
        assert 42 in erased, "SucceedingModule.erase() must be called even after FailingModule fails"
        assert "failing" in str(raised)
        assert "successfully" in str(raised)

    @pytest.mark.asyncio
    async def test_erase_collects_all_errors(self):
        """يجمع أخطاء كل الـ modules الفاشلة في رسالة واحدة."""
        from titan.privacy.registry import UserDataRegistry

        class Fail1:
            component_name = "fail1"
            data_description = "أول فاشل"
            async def data_for(self, user_id): return {}
            async def erase(self, user_id): raise ValueError("error_one")

        class Fail2:
            component_name = "fail2"
            data_description = "ثاني فاشل"
            async def data_for(self, user_id): return {}
            async def erase(self, user_id): raise ValueError("error_two")

        registry = UserDataRegistry()
        registry.register(Fail1())
        registry.register(Fail2())

        results = await asyncio.gather(
            registry.erase_user(1),
            return_exceptions=True,
        )
        raised = results[0]

        assert type(raised).__name__ == "TitanError", f"Expected TitanError, got: {raised!r}"
        msg = str(raised)
        assert "fail1" in msg
        assert "fail2" in msg

    @pytest.mark.asyncio
    async def test_erase_no_error_when_all_succeed(self):
        """لا exception عندما تنجح كل الـ modules."""
        from titan.privacy.registry import UserDataRegistry

        registry = UserDataRegistry()
        registry.register(GoodModule())

        # يجب أن ينتهي بدون exception
        await registry.erase_user(1)


# ---------------------------------------------------------------------------
# /mydata — deep immutability
# ---------------------------------------------------------------------------

class TestMydataDeepFreeze:
    def test_deep_freeze_dict(self):
        """dict داخلي يصبح MappingProxyType."""
        from titan.privacy.handler import _deep_freeze
        result = _deep_freeze({"outer": {"inner": 1}})
        assert type(result).__name__ == "mappingproxy"
        assert type(result["outer"]).__name__ == "mappingproxy"

    def test_deep_freeze_list_becomes_tuple(self):
        """list داخلية تصبح tuple."""
        from titan.privacy.handler import _deep_freeze
        result = _deep_freeze({"questions": ["a", "b"]})
        assert isinstance(result["questions"], tuple)

    def test_deep_freeze_nested_list_immutable(self):
        """لا يمكن تعديل list داخلية بعد التجميد."""
        from titan.privacy.handler import _deep_freeze
        result = _deep_freeze({"questions": ["ما اسمك؟"]})
        with pytest.raises(TypeError):
            result["questions"] += ("x",)  # tuple لا يدعم +=

    def test_deep_freeze_nested_dict_immutable(self):
        """لا يمكن تعديل dict داخلي بعد التجميد."""
        from titan.privacy.handler import _deep_freeze
        result = _deep_freeze({"ask": {"count": 1}})
        with pytest.raises(TypeError):
            result["ask"]["injected"] = 99

    def test_deep_freeze_primitives_unchanged(self):
        """القيم البدائية تمر كما هي."""
        from titan.privacy.handler import _deep_freeze
        result = _deep_freeze({"n": 1, "s": "hello", "b": True, "none": None})
        assert result["n"] == 1
        assert result["s"] == "hello"
        assert result["b"] is True
        assert result["none"] is None

    @pytest.mark.asyncio
    async def test_mydata_handler_provides_deep_frozen_report(self):
        """الـ hook تستلم تقريراً مجمَّداً بعمق."""
        from titan.privacy.handler import handle_mydata_command
        from titan.privacy.registry import UserDataRegistry

        class ModuleWithList:
            component_name = "mod"
            data_description = "has list"
            async def data_for(self, user_id): return {"items": ["x", "y"]}
            async def erase(self, user_id): pass

        registry = UserDataRegistry()
        registry.register(ModuleWithList())

        received: dict = {}

        async def format_hook(ctx, report):
            received["items_type"] = type(report["mod"]["items"]).__name__
            return "ok"

        ctx = MagicMock()
        ctx.user_id = 1
        ctx.reply = AsyncMock()

        await handle_mydata_command(ctx, registry, format_hook=format_hook)

        assert received["items_type"] == "tuple", (
            "list inside report must be converted to tuple (deep freeze)"
        )
