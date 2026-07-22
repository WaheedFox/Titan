"""
اختبارات السيناريوهات الحقيقية — محاولة كسر API من منظور المطور.

كل اختبار يمثل موقفاً واقعياً قد يقع فيه مطور عند بناء بوت حقيقي.
"""

import pytest
import asyncio
from titan.bot import Titan
from titan.router import Router
from titan.errors import TitanError
from titan.keyboard import InlineKeyboard, InlineButton


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_bot():
    return Titan("fake-token")


def make_message_update(text="hello", user_id=1, chat_id=100, message_id=10):
    return {
        "update_id": 1,
        "message": {
            "message_id": message_id,
            "text": text,
            "from": {"id": user_id, "username": "user"},
            "chat": {"id": chat_id, "type": "private"},
        },
    }


def make_callback_update(data="yes", user_id=1, chat_id=100, message_id=10):
    return {
        "update_id": 2,
        "callback_query": {
            "id": "cb-id-1",
            "data": data,
            "from": {"id": user_id, "username": "user"},
            "message": {
                "message_id": message_id,
                "chat": {"id": chat_id, "type": "private"},
            },
        },
    }


# ─────────────────────────────────────────────
# 1. Middleware يستدعي next() مرتين
# ─────────────────────────────────────────────

class TestDoubleNextInMiddleware:
    """
    سيناريو: مطور يكتب middleware ينتظر next() مرتين عن طريق الخطأ.
    المتوقع: الـ handlers تُنفَّذ مرتين → رسائل مكررة للمستخدم.
    """

    @pytest.mark.asyncio
    async def test_double_next_runs_handlers_twice(self):
        bot = make_bot()
        call_count = 0

        @bot.middleware
        async def buggy_middleware(ctx, next):
            await next()
            await next()  # خطأ: استدعاء مرتين

        @bot.on("message")
        async def handler(ctx):
            nonlocal call_count
            call_count += 1

        await bot._handle_update(make_message_update())

        # المشكلة: المطور يتوقع 1، لكن النتيجة 2
        assert call_count == 2, (
            f"handler ran {call_count} times — double next() silently duplicates execution"
        )

    @pytest.mark.asyncio
    async def test_double_next_with_command_runs_twice(self):
        bot = make_bot()
        call_count = 0

        @bot.middleware
        async def double_next(ctx, next):
            await next()
            await next()

        @bot.command("start")
        async def start(ctx):
            nonlocal call_count
            call_count += 1

        await bot._handle_update(make_message_update("/start"))

        assert call_count == 2, (
            f"command handler ran {call_count} times due to double next()"
        )


# ─────────────────────────────────────────────
# 2. تسجيل الأمر بشرطة مائلة /start بدلاً من start
# ─────────────────────────────────────────────

class TestCommandWithLeadingSlash:
    """
    سيناريو: مطور يكتب @bot.command("/start") بدلاً من @bot.command("start").
    المتوقع (ما يتوقعه المطور): handler يُنفَّذ عند إرسال /start.
    الواقع: لا يُنفَّذ أبداً — يسقط إلى on("message").
    """

    @pytest.mark.asyncio
    async def test_command_with_slash_never_fires(self):
        bot = make_bot()
        command_fired = False
        message_fired = False

        # المطور يكتب الأمر بشرطة مائلة — خطأ شائع جداً
        @bot.command("/start")
        async def start(ctx):
            nonlocal command_fired
            command_fired = True

        @bot.on("message")
        async def on_message(ctx):
            nonlocal message_fired
            message_fired = True

        await bot._handle_update(make_message_update("/start"))

        assert not command_fired, "handler registered as '/start' should not fire"
        assert message_fired, "update silently falls through to on('message')"

    def test_slash_command_is_registered_under_wrong_key(self):
        bot = make_bot()

        @bot.command("/start")
        async def start(ctx): pass

        # مسجل بمفتاح خاطئ
        assert "/start" in bot.commands
        assert "start" not in bot.commands


# ─────────────────────────────────────────────
# 3. callback_data فارغة ""
# ─────────────────────────────────────────────

class TestEmptyStringCallbackData:
    """
    سيناريو: مطور يسجل @bot.callback("") لزر بدون data.
    الواقع: الـ handler لا يُنفَّذ أبداً — الشرط `if data` يُسقط السلسلة الفارغة.
    """

    @pytest.mark.asyncio
    async def test_empty_callback_data_handler_never_fires(self):
        bot = make_bot()
        specific_fired = False
        fallback_fired = False

        @bot.callback("")
        async def on_empty(ctx):
            nonlocal specific_fired
            specific_fired = True

        @bot.on("callback")
        async def fallback(ctx):
            nonlocal fallback_fired
            fallback_fired = True

        await bot._handle_update(make_callback_update(data=""))

        assert not specific_fired, (
            "handler registered with callback('') never fires — "
            "empty string is falsy, routing skips it"
        )
        assert fallback_fired, "falls back to on('callback') instead"

    def test_empty_callback_data_is_registered(self):
        """التسجيل يمر بنجاح — لا يوجد تحذير للمطور."""
        bot = make_bot()

        @bot.callback("")
        async def handler(ctx): pass

        assert "" in bot.callback_handlers


# ─────────────────────────────────────────────
# 4. bot.include() تطبيق جزئي عند التعارض
# ─────────────────────────────────────────────

class TestPartialIncludeOnConflict:
    """
    سيناريو: router يحتوي على handlers + أمر يتعارض مع أمر مسجل مسبقاً.
    الواقع: handlers تُضاف أولاً، ثم TitanError تُرمى — البوت في حالة جزئية.
    """

    def test_handlers_added_before_command_conflict_raises(self):
        bot = make_bot()

        # أمر مسجل مسبقاً في البوت
        @bot.command("start")
        async def existing_start(ctx): pass

        # router يحتوي على handler + أمر متعارض
        router = Router()

        @router.on("message")
        async def router_message(ctx): pass

        @router.command("start")  # سيتعارض
        async def router_start(ctx): pass

        with pytest.raises(TitanError):
            bot.include(router)

        # المشكلة: رغم الخطأ، handler الـ message أُضيف بالفعل
        assert router_message in bot.handlers.get("message", []), (
            "message handler was added before the TitanError — bot is in partial state"
        )

    def test_bot_remains_usable_after_partial_include(self):
        """البوت يعمل لكن مع handlers غير مقصودة."""
        bot = make_bot()

        @bot.command("start")
        async def existing_start(ctx): pass

        router = Router()

        @router.on("message")
        async def unexpected_handler(ctx): pass

        @router.command("start")
        async def conflict(ctx): pass

        with pytest.raises(TitanError):
            bot.include(router)

        # unexpected_handler أصبح مسجلاً رغم الفشل الكلي للـ include
        assert len(bot.handlers.get("message", [])) == 1


# ─────────────────────────────────────────────
# 5. تسجيل error_handler مرتين
# ─────────────────────────────────────────────

class TestErrorHandlerOverwrite:
    """
    سيناريو: مطور يسجل error_handler مرتين عن طريق الخطأ.
    الواقع: الأول يُحذف بصمت، لا يوجد أي تحذير.
    """

    def test_second_error_handler_silently_replaces_first(self):
        bot = make_bot()
        calls = []

        @bot.error_handler
        async def first_handler(ctx, exc):
            calls.append("first")

        @bot.error_handler
        async def second_handler(ctx, exc):
            calls.append("second")

        # الأول اختفى بصمت
        assert bot._error_handler is second_handler
        assert bot._error_handler is not first_handler

    @pytest.mark.asyncio
    async def test_only_second_error_handler_runs(self):
        bot = make_bot()
        calls = []

        @bot.error_handler
        async def first(ctx, exc):
            calls.append("first")

        @bot.error_handler
        async def second(ctx, exc):
            calls.append("second")

        @bot.on("message")
        async def broken_handler(ctx):
            raise ValueError("boom")

        await bot._handle_update(make_message_update())

        assert calls == ["second"]
        assert "first" not in calls


# ─────────────────────────────────────────────
# 6. InlineButton بدون callback_data ولا url
# ─────────────────────────────────────────────

class TestInlineButtonWithNoAction:
    """
    سيناريو: مطور ينشئ زراً بدون callback_data ولا url.
    الواقع: Titan لا يرمي خطأ — يُنتج dict ناقص يرفضه Telegram API.
    """

    def test_button_with_no_action_produces_text_only_dict(self):
        btn = InlineButton("Click me")
        result = btn.to_dict()

        assert result == {"text": "Click me"}, (
            "button with no action silently produces incomplete dict"
        )
        assert "callback_data" not in result
        assert "url" not in result

    def test_keyboard_with_actionless_button_passes_to_dict(self):
        kb = InlineKeyboard().button("Broken button")
        result = kb.to_dict()

        rows = result["inline_keyboard"]
        assert len(rows) == 1
        assert rows[0][0] == {"text": "Broken button"}


# ─────────────────────────────────────────────
# 7. is_banned لا يتحدث داخل نفس الـ update
# ─────────────────────────────────────────────

class TestIsBannedSnapshot:
    """
    سيناريو: مطور يضيف المستخدم لـ bot.banned_users داخل handler.
    المتوقع: ctx.is_banned يصبح True فوراً.
    الواقع: is_banned snapshot عند بداية الـ update — لا يتغير داخله.
    """

    @pytest.mark.asyncio
    async def test_banning_user_mid_handler_does_not_affect_current_ctx(self):
        bot = make_bot()
        user_id = 42
        is_banned_after_ban = None

        @bot.on("message")
        async def handler(ctx):
            nonlocal is_banned_after_ban
            bot.banned_users.add(user_id)   # المطور يحظر المستخدم
            is_banned_after_ban = ctx.is_banned  # هل تغير؟

        await bot._handle_update(make_message_update(user_id=user_id))

        assert is_banned_after_ban is False, (
            "is_banned is a snapshot taken at update start — "
            "banning mid-handler does not affect current ctx"
        )
        # لكن الـ update التالي سيكون صحيحاً
        assert user_id in bot.banned_users


# ─────────────────────────────────────────────
# 8. ctx.answer_callback() خارج callback context
# ─────────────────────────────────────────────

class TestAnswerCallbackOutsideCallback:
    """
    سيناريو: مطور يستدعي ctx.answer_callback() في message handler.
    المتوقع: ربما يحدث شيء أو يُرمى خطأ.
    الواقع: يُعيد None بصمت — لا شيء يحدث، لا تحذير.
    """

    @pytest.mark.asyncio
    async def test_answer_callback_in_message_context_returns_none(self):
        bot = make_bot()
        result = None

        @bot.on("message")
        async def handler(ctx):
            nonlocal result
            result = await ctx.answer_callback()

        await bot._handle_update(make_message_update())

        assert result is None, (
            "answer_callback() in message context silently returns None"
        )


# ─────────────────────────────────────────────
# 9. command مسجل في router وآخر في bot — ثم include
# ─────────────────────────────────────────────

class TestRouterCommandConflictWithBot:
    """
    سيناريو: نفس الأمر مسجل مرتين — مرة في bot ومرة في router.
    المتوقع: TitanError عند include() — صحيح.
    لكن: ماذا لو سجّله في router مرتين؟ هل يُكتشف قبل include؟
    """

    def test_router_catches_duplicate_command_before_include(self):
        router = Router()

        @router.command("help")
        async def h1(ctx): pass

        with pytest.raises(TitanError):
            @router.command("help")
            async def h2(ctx): pass

    def test_two_routers_with_same_command_conflict_on_second_include(self):
        bot = make_bot()

        r1 = Router()
        r2 = Router()

        @r1.command("help")
        async def h1(ctx): pass

        @r2.command("help")
        async def h2(ctx): pass

        bot.include(r1)

        with pytest.raises(TitanError):
            bot.include(r2)


# ─────────────────────────────────────────────
# 10. on("message") handler لا يوقف تنفيذ handler آخر عند رميه خطأ
# ─────────────────────────────────────────────

class TestMultipleHandlersContinueAfterException:
    """
    سيناريو: مطور يسجل handler-ين. الأول يرمي خطأ.
    المتوقع (المنطقي): الثاني لا يعمل.
    الواقع: الثاني يعمل — كل handler مستقل في try/except.
    """

    @pytest.mark.asyncio
    async def test_second_handler_runs_even_if_first_raises(self):
        bot = make_bot()
        second_ran = False

        @bot.on("message")
        async def first(ctx):
            raise RuntimeError("intentional crash")

        @bot.on("message")
        async def second(ctx):
            nonlocal second_ran
            second_ran = True

        await bot._handle_update(make_message_update())

        assert second_ran, (
            "second handler runs even though first raised — "
            "exceptions don't stop the handler chain"
        )
