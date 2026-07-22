"""
اختبارات تكامل Message Links Protocol مع ctx وbot.

تتحقق من:
- تسجيل الهوية تلقائياً بعد ctx.reply() وctx.send().
- رسائل الفشل لا تُسجَّل هوية.
- /link محجوز في bot.commands عند التهيئة.
- محاولة تسجيل @bot.command("link") تُثير TitanError.
- bot.links متاح ومن النوع الصحيح.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from titan.bot import Titan
from titan.ctx import Context
from titan.update import Update
from titan.errors import TitanError
from titan.links.manager import LinksManager
from titan.links.store import SqliteMessageStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ctx(raw: dict, api=None, links=None) -> Context:
    if api is None:
        api = MagicMock()
        api.send_message = AsyncMock(
            return_value={"ok": True, "result": {"message_id": 42}}
        )
        api._me = {"id": 1, "username": "TestBot"}
    update = Update(raw)
    return Context(update, api, links=links)


def make_links() -> LinksManager:
    m = LinksManager()
    m._sqlite_store = SqliteMessageStore(":memory:")
    m._store = m._sqlite_store
    return m


RAW_MESSAGE = {
    "update_id": 1,
    "message": {
        "message_id": 10,
        "text": "hello",
        "from": {"id": 99, "username": "user"},
        "chat": {"id": 200, "type": "private"},
    },
}


# ---------------------------------------------------------------------------
# ctx.reply() — تسجيل الهوية
# ---------------------------------------------------------------------------

class TestCtxReplyRegistersIdentity:
    @pytest.mark.asyncio
    async def test_reply_registers_identity(self):
        links = make_links()
        ctx = make_ctx(RAW_MESSAGE, links=links)
        await ctx.reply("مرحبا")

        addr = await links.get_address_for_telegram_id(
            chat_id=200,
            telegram_message_id=42,
        )
        assert addr is not None
        assert addr.bot_username == "TestBot"
        assert addr.titan_id == 1

    @pytest.mark.asyncio
    async def test_reply_without_links_no_error(self):
        """ctx بدون links يعمل كالمعتاد بدون استثناء."""
        ctx = make_ctx(RAW_MESSAGE, links=None)
        result = await ctx.reply("مرحبا")
        assert result is not None

    @pytest.mark.asyncio
    async def test_failed_send_no_identity_registered(self):
        """الرسائل الفاشلة لا تحصل على هوية."""
        links = make_links()
        api = MagicMock()
        from titan.telegram import TelegramError
        api.send_message = AsyncMock(side_effect=TelegramError("network error"))
        api._me = {"id": 1, "username": "TestBot"}

        ctx = make_ctx(RAW_MESSAGE, api=api, links=links)

        with pytest.raises(TelegramError):
            await ctx.reply("هذه الرسالة ستفشل")

        # لا هوية مسجّلة
        result = await links.get_address_for_telegram_id(200, 42)
        assert result is None

    @pytest.mark.asyncio
    async def test_identity_registration_failure_is_non_fatal(self):
        """فشل تسجيل الهوية لا يكسر ctx.reply()."""
        links = make_links()
        links._store.save_identity = AsyncMock(side_effect=RuntimeError("store down"))

        ctx = make_ctx(RAW_MESSAGE, links=links)
        # لا يجب أن يُثير استثناء
        result = await ctx.reply("رسالة اختبار")
        assert result is not None


# ---------------------------------------------------------------------------
# ctx.send() — تسجيل الهوية
# ---------------------------------------------------------------------------

class TestCtxSendRegistersIdentity:
    @pytest.mark.asyncio
    async def test_send_registers_identity(self):
        links = make_links()
        ctx = make_ctx(RAW_MESSAGE, links=links)
        await ctx.send("تم الإرسال")

        addr = await links.get_address_for_telegram_id(
            chat_id=200,
            telegram_message_id=42,
        )
        assert addr is not None


# ---------------------------------------------------------------------------
# Update.reply_to_message_id
# ---------------------------------------------------------------------------

class TestUpdateReplyToMessageId:
    def test_reply_to_present(self):
        raw = {
            "update_id": 1,
            "message": {
                "message_id": 99,
                "text": "/link",
                "from": {"id": 1},
                "chat": {"id": 10, "type": "private"},
                "reply_to_message": {
                    "message_id": 50,
                    "from": {"id": 5, "is_bot": True, "username": "Bot"},
                },
            },
        }
        u = Update(raw)
        assert u.reply_to_message_id == 50

    def test_reply_to_absent(self):
        u = Update(RAW_MESSAGE)
        assert u.reply_to_message_id is None

    def test_reply_to_sender_is_bot_true(self):
        raw = {
            "update_id": 1,
            "message": {
                "message_id": 99,
                "text": "/link",
                "from": {"id": 1},
                "chat": {"id": 10, "type": "private"},
                "reply_to_message": {
                    "message_id": 50,
                    "from": {"id": 5, "is_bot": True},
                },
            },
        }
        u = Update(raw)
        assert u.reply_to_sender_is_bot is True

    def test_reply_to_sender_is_bot_false(self):
        raw = {
            "update_id": 1,
            "message": {
                "message_id": 99,
                "text": "/link",
                "from": {"id": 1},
                "chat": {"id": 10, "type": "private"},
                "reply_to_message": {
                    "message_id": 50,
                    "from": {"id": 5, "is_bot": False},
                },
            },
        }
        u = Update(raw)
        assert u.reply_to_sender_is_bot is False

    def test_reply_to_absent_sender_is_bot_false(self):
        u = Update(RAW_MESSAGE)
        assert u.reply_to_sender_is_bot is False


# ---------------------------------------------------------------------------
# ctx.reply_to_message_id property
# ---------------------------------------------------------------------------

class TestCtxReplyToMessageId:
    def test_delegates_to_update(self):
        raw = {
            "update_id": 1,
            "message": {
                "message_id": 99,
                "text": "/link",
                "from": {"id": 1},
                "chat": {"id": 10, "type": "private"},
                "reply_to_message": {
                    "message_id": 77,
                    "from": {"id": 5, "is_bot": True},
                },
            },
        }
        ctx = make_ctx(raw)
        assert ctx.reply_to_message_id == 77

    def test_none_when_no_reply(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.reply_to_message_id is None


# ---------------------------------------------------------------------------
# Titan bot — /link محجوز
# ---------------------------------------------------------------------------

class TestBotUsernameWarning:
    """
    فشل تسجيل الهوية عند غياب bot_username يجب أن ينتج warning واضح،
    لا تجاهل صامت، ولا استثناء يُوقف الرسالة.
    """

    def _capture_titan_warnings(self):
        """Context manager يلتقط سجلات logging على مستوى WARNING من logger 'titan'."""
        import logging
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            records: list[str] = []

            class _Handler(logging.Handler):
                def emit(self, record):
                    records.append(record.getMessage())

            handler = _Handler()
            logger = logging.getLogger("titan")
            old_level = logger.level
            logger.addHandler(handler)
            logger.setLevel(logging.WARNING)
            try:
                yield records
            finally:
                logger.removeHandler(handler)
                logger.setLevel(old_level)

        return _ctx()

    @pytest.mark.asyncio
    async def test_missing_username_in_me_logs_warning(self):
        """_me موجود لكن بدون username → warning، الرسالة تصل."""
        links = make_links()
        api = MagicMock()
        api.send_message = AsyncMock(
            return_value={"ok": True, "result": {"message_id": 42}}
        )
        api._me = {"id": 1}  # بدون username

        ctx = make_ctx(RAW_MESSAGE, api=api, links=links)

        with self._capture_titan_warnings() as warnings:
            result = await ctx.reply("رسالة بدون username")

        # الرسالة وصلت رغم فشل تسجيل الهوية
        assert result is not None
        assert result["ok"] is True

        # warning صريح — لا صمت
        assert any("bot_username" in msg or "username" in msg for msg in warnings), (
            f"Expected warning about bot_username, got: {warnings}"
        )

    @pytest.mark.asyncio
    async def test_none_api_me_logs_warning(self):
        """_me = None → warning واضح، الرسالة تصل."""
        links = make_links()
        api = MagicMock()
        api.send_message = AsyncMock(
            return_value={"ok": True, "result": {"message_id": 42}}
        )
        api._me = None

        ctx = make_ctx(RAW_MESSAGE, api=api, links=links)

        with self._capture_titan_warnings() as warnings:
            result = await ctx.reply("رسالة")

        assert result is not None
        assert len(warnings) > 0, (
            "Expected a warning log when api._me is None"
        )

    @pytest.mark.asyncio
    async def test_warning_does_not_raise(self):
        """غياب bot_username لا يُثير استثناء في أي حال."""
        for me_value in [None, {}, {"id": 1}]:
            links = make_links()
            api = MagicMock()
            api.send_message = AsyncMock(
                return_value={"ok": True, "result": {"message_id": 42}}
            )
            api._me = me_value
            ctx = make_ctx(RAW_MESSAGE, api=api, links=links)
            # يجب ألا يُثير أي استثناء
            result = await ctx.reply("test")
            assert result is not None


class TestBotLinkReservation:
    def test_link_reserved_in_reserved_commands(self):
        """link يُخزَّن في _reserved_commands لا commands حتى لا يؤثر على Inspector."""
        bot = Titan("fake_token")
        assert "link" in bot._reserved_commands
        assert "link" not in bot.commands

    def test_bot_links_is_links_manager(self):
        bot = Titan("fake_token")
        assert isinstance(bot.links, LinksManager)

    def test_register_link_raises_titan_error(self):
        bot = Titan("fake_token")
        with pytest.raises(TitanError) as exc_info:
            @bot.command("link")
            async def my_link(ctx):
                pass
        error_msg = str(exc_info.value).lower()
        # الرسالة يجب أن تذكر message links protocol
        assert "message links protocol" in error_msg

    def test_include_router_with_link_raises_titan_error(self):
        from titan.router import Router
        bot = Titan("fake_token")
        router = Router()

        @router.command("link")
        async def router_link(ctx):
            pass

        with pytest.raises(TitanError) as exc_info:
            bot.include(router)
        error_msg = str(exc_info.value).lower()
        assert "message links protocol" in error_msg

    def test_link_command_source_mentions_protocol(self):
        bot = Titan("fake_token")
        source = bot._command_sources.get("link", "")
        assert "message links protocol" in source.lower()
