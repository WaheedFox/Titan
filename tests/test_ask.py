"""
اختبارات AskManager — متاح فقط عبر titan.extras

AskManager تُستخدم كـ callable مباشرة: await ask(ctx, "text")

تتحقق من:
- السلوك الأساسي: إرسال سؤال واستقبال الرد
- العزل الدقيق بحسب (chat_id, user_id)
- تجاهل المستخدمين والشاتات الأخرى
- تجاهل الـ callbacks أثناء الانتظار
- تجاهل منشورات القنوات أثناء الانتظار
- رفض استدعاءين متزامنين لنفس المستخدم
- عدم وجود أي ask machinery في core Titan
"""

import asyncio
import pytest
from titan.bot import Titan
from titan.extras import AskManager
from titan.errors import TitanError


def make_bot_with_ask():
    """
    بوت مع AskManager مُثبَّت عبر المسار اليدوي.

    هذا الاختبار يفحص آلية AskManager ذاتها — لا امتثالها للـ Privacy Registry.
    التحذير مكبوت هنا لأنه سلوك متوقع ومقصود في سياق هذه الاختبارات.
    """
    import warnings
    bot = Titan("fake-token")
    ask = AskManager()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        bot.middleware(ask.as_middleware())
    return bot, ask


def make_message(text="hello", user_id=1, chat_id=100, update_id=1):
    return {
        "update_id": update_id,
        "message": {
            "message_id": 10,
            "text": text,
            "from": {"id": user_id, "username": "user"},
            "chat": {"id": chat_id, "type": "private"},
        },
    }


def make_callback(data="yes", user_id=1, chat_id=100, update_id=2):
    return {
        "update_id": update_id,
        "callback_query": {
            "id": "cb-1",
            "data": data,
            "from": {"id": user_id, "username": "user"},
            "message": {
                "message_id": 10,
                "chat": {"id": chat_id, "type": "private"},
            },
        },
    }


def make_channel_post(text="post", chat_id=200, update_id=3):
    return {
        "update_id": update_id,
        "channel_post": {
            "message_id": 20,
            "text": text,
            "chat": {"id": chat_id, "type": "channel"},
        },
    }


# ─────────────────────────────────────────────
# 1. السلوك الأساسي
# ─────────────────────────────────────────────

class TestAskBasic:

    @pytest.mark.asyncio
    async def test_ask_returns_next_message_text(self):
        bot, ask = make_bot_with_ask()
        received = []

        async def mock_reply(chat_id, text, **kwargs):
            return {}

        @bot.command("start")
        async def start(ctx):
            ctx._api.send_message = mock_reply
            answer = await ask(ctx, "ما اسمك؟")
            received.append(answer)

        task = asyncio.create_task(
            bot._handle_update(make_message("/start", update_id=1))
        )
        await asyncio.sleep(0)

        await bot._handle_update(make_message("Alice", update_id=2))
        await task

        assert received == ["Alice"]

    @pytest.mark.asyncio
    async def test_ask_returns_empty_string_for_non_text_message(self):
        """رسالة بلا نص (صورة مثلاً) تُعيد سلسلة فارغة."""
        bot, ask = make_bot_with_ask()
        received = []

        no_text_update = {
            "update_id": 2,
            "message": {
                "message_id": 11,
                "photo": [{}],
                "from": {"id": 1, "username": "user"},
                "chat": {"id": 100, "type": "private"},
            },
        }

        async def mock_reply(chat_id, text, **kwargs):
            return {}

        @bot.command("start")
        async def start(ctx):
            ctx._api.send_message = mock_reply
            answer = await ask(ctx, "أرسل شيئاً")
            received.append(answer)

        task = asyncio.create_task(
            bot._handle_update(make_message("/start", update_id=1))
        )
        await asyncio.sleep(0)

        await bot._handle_update(no_text_update)
        await task

        assert received == [""]


# ─────────────────────────────────────────────
# 2. العزل بحسب (chat_id, user_id)
# ─────────────────────────────────────────────

class TestAskIsolation:

    @pytest.mark.asyncio
    async def test_message_from_different_user_does_not_resolve(self):
        bot, ask = make_bot_with_ask()
        resolved = []
        other_handler_ran = []

        async def mock_reply(chat_id, text, **kwargs):
            return {}

        @bot.command("ask")
        async def ask_cmd(ctx):
            ctx._api.send_message = mock_reply
            resolved.append(await ask(ctx, "سؤال"))

        @bot.on("message")
        async def catch_other(ctx):
            other_handler_ran.append(True)

        task = asyncio.create_task(
            bot._handle_update(make_message("/ask", user_id=1, chat_id=100, update_id=1))
        )
        await asyncio.sleep(0)

        await bot._handle_update(make_message("من مستخدم آخر", user_id=2, chat_id=100, update_id=2))

        assert not resolved, "ask() must not resolve from a different user"
        assert other_handler_ran, "message from other user must reach normal routing"

        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    @pytest.mark.asyncio
    async def test_message_from_different_chat_does_not_resolve(self):
        bot, ask = make_bot_with_ask()
        resolved = []
        other_handler_ran = []

        async def mock_reply(chat_id, text, **kwargs):
            return {}

        @bot.command("ask")
        async def ask_cmd(ctx):
            ctx._api.send_message = mock_reply
            resolved.append(await ask(ctx, "سؤال"))

        @bot.on("message")
        async def catch_other(ctx):
            other_handler_ran.append(True)

        task = asyncio.create_task(
            bot._handle_update(make_message("/ask", user_id=1, chat_id=100, update_id=1))
        )
        await asyncio.sleep(0)

        await bot._handle_update(make_message("من شات آخر", user_id=1, chat_id=999, update_id=2))

        assert not resolved, "ask() must not resolve from a different chat"
        assert other_handler_ran, "message from other chat must reach normal routing"

        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    @pytest.mark.asyncio
    async def test_two_users_simultaneously(self):
        bot, ask = make_bot_with_ask()
        results = {}

        async def mock_reply(chat_id, text, **kwargs):
            return {}

        @bot.command("ask")
        async def ask_cmd(ctx):
            ctx._api.send_message = mock_reply
            results[ctx.user_id] = await ask(ctx, "سؤال")

        task1 = asyncio.create_task(
            bot._handle_update(make_message("/ask", user_id=1, chat_id=100, update_id=1))
        )
        task2 = asyncio.create_task(
            bot._handle_update(make_message("/ask", user_id=2, chat_id=200, update_id=2))
        )
        await asyncio.sleep(0)

        await bot._handle_update(make_message("رد من 2", user_id=2, chat_id=200, update_id=3))
        await bot._handle_update(make_message("رد من 1", user_id=1, chat_id=100, update_id=4))

        await asyncio.gather(task1, task2)

        assert results[1] == "رد من 1"
        assert results[2] == "رد من 2"


# ─────────────────────────────────────────────
# 3. تجاهل callbacks وchannel posts
# ─────────────────────────────────────────────

class TestAskIgnoresNonMessages:

    @pytest.mark.asyncio
    async def test_callback_does_not_resolve_ask(self):
        bot, ask = make_bot_with_ask()
        resolved = []

        async def mock_reply(chat_id, text, **kwargs):
            return {}

        @bot.command("ask")
        async def ask_cmd(ctx):
            ctx._api.send_message = mock_reply
            resolved.append(await ask(ctx, "سؤال"))

        task = asyncio.create_task(
            bot._handle_update(make_message("/ask", user_id=1, chat_id=100, update_id=1))
        )
        await asyncio.sleep(0)

        await bot._handle_update(make_callback(user_id=1, chat_id=100, update_id=2))

        assert not resolved, "callback must not resolve a pending ask()"

        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    @pytest.mark.asyncio
    async def test_channel_post_does_not_resolve_ask(self):
        bot, ask = make_bot_with_ask()
        resolved = []

        async def mock_reply(chat_id, text, **kwargs):
            return {}

        @bot.command("ask")
        async def ask_cmd(ctx):
            ctx._api.send_message = mock_reply
            resolved.append(await ask(ctx, "سؤال"))

        task = asyncio.create_task(
            bot._handle_update(make_message("/ask", user_id=1, chat_id=100, update_id=1))
        )
        await asyncio.sleep(0)

        await bot._handle_update(make_channel_post(update_id=2))

        assert not resolved, "channel post must not resolve a pending ask()"

        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


# ─────────────────────────────────────────────
# 4. حالات الخطأ
# ─────────────────────────────────────────────

class TestAskErrors:

    @pytest.mark.asyncio
    async def test_double_ask_same_user_raises(self):
        bot, ask = make_bot_with_ask()
        error_caught = []

        async def mock_reply(chat_id, text, **kwargs):
            return {}

        @bot.command("ask")
        async def ask_cmd(ctx):
            ctx._api.send_message = mock_reply
            task_inner = asyncio.create_task(ask(ctx, "سؤال أول"))
            await asyncio.sleep(0)
            try:
                await ask(ctx, "سؤال ثانٍ")
            except TitanError as e:
                error_caught.append(str(e))
            task_inner.cancel()
            try:
                await task_inner
            except (asyncio.CancelledError, Exception):
                pass

        await bot._handle_update(make_message("/ask", update_id=1))

        assert error_caught, "expected TitanError for double ask() on same user"
        assert "already waiting" in error_caught[0]


# ─────────────────────────────────────────────
# 5. Core isolation
# ─────────────────────────────────────────────

class TestCoreHasNoAskMachinery:

    def test_plain_titan_has_no_pending_asks(self):
        bot = Titan("fake-token")
        assert not hasattr(bot, "_pending_asks"), \
            "Core Titan must not carry _pending_asks machinery"

    def test_ask_manager_leaves_no_footprint_except_middleware(self):
        import warnings
        bot = Titan("fake-token")
        ask = AskManager()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            bot.middleware(ask.as_middleware())
        assert len(bot.middleware_chain._chain) == 1
        assert not hasattr(bot, "_pending_asks")
        assert not hasattr(bot, "ask")
