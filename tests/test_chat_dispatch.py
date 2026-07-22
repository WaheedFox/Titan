"""
tests/test_chat_dispatch.py

اختبارات نظام dispatch التسلسلي per-chat.

تتحقق من:
1. عدم حجب محادثة لمحادثة أخرى (عزل بين الـ chats)
2. ترتيب dispatch داخل نفس الـ chat محفوظ (FIFO)
3. ask() تعمل بدون deadlock عبر run_async
4. regression: _handle_update المباشر لا يزال يعمل كما كان
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from titan.bot import Titan


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_message(text="hello", user_id=1, chat_id=100, update_id=1):
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "text": text,
            "from": {"id": user_id, "username": "user"},
            "chat": {"id": chat_id, "type": "private"},
        },
    }


def make_callback(data="yes", user_id=1, chat_id=100, update_id=1):
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


def make_bot():
    return Titan("fake-token")


# ─────────────────────────────────────────────
# 1. _chat_id_from_raw
# ─────────────────────────────────────────────

class TestChatIdFromRaw:

    def test_message(self):
        raw = make_message(chat_id=42)
        assert Titan._chat_id_from_raw(raw) == 42

    def test_callback_query(self):
        raw = make_callback(chat_id=99)
        assert Titan._chat_id_from_raw(raw) == 99

    def test_channel_post(self):
        raw = {
            "update_id": 1,
            "channel_post": {
                "message_id": 1,
                "chat": {"id": 777, "type": "channel"},
                "text": "hi",
            },
        }
        assert Titan._chat_id_from_raw(raw) == 777

    def test_edited_message(self):
        raw = {
            "update_id": 1,
            "edited_message": {
                "message_id": 1,
                "chat": {"id": 55, "type": "group"},
                "text": "edited",
                "from": {"id": 1, "is_bot": False, "first_name": "A"},
            },
        }
        assert Titan._chat_id_from_raw(raw) == 55

    def test_no_chat_returns_none(self):
        raw = {"update_id": 1, "inline_query": {"id": "iq-1", "query": "hi"}}
        assert Titan._chat_id_from_raw(raw) is None

    def test_empty_update_returns_none(self):
        assert Titan._chat_id_from_raw({"update_id": 1}) is None


# ─────────────────────────────────────────────
# 2. عزل بين الـ chats
# ─────────────────────────────────────────────

class TestChatIsolation:

    @pytest.mark.asyncio
    async def test_slow_chat_does_not_block_fast_chat(self):
        """
        محادثة تحتوي على handler بطيء لا تحجب محادثة أخرى.
        """
        bot = make_bot()
        order = []

        @bot.on("message")
        async def handler(ctx):
            if ctx.chat_id == 100:
                await asyncio.sleep(0.05)   # chat 100 بطيء
            order.append(ctx.chat_id)

        # أنشئ worker tasks لـ chat 100 و chat 200
        queue_100 = bot._ensure_chat_worker(100)
        queue_200 = bot._ensure_chat_worker(200)

        await queue_100.put(make_message(chat_id=100, update_id=1))
        await queue_200.put(make_message(chat_id=200, update_id=2))

        # انتظر كافيًا لإتمام كلا الـ handlers
        await asyncio.sleep(0.15)

        # chat 200 يجب أن ينتهي قبل chat 100 لأن الأخير بطيء
        assert 200 in order
        assert 100 in order
        assert order.index(200) < order.index(100), \
            "fast chat (200) should complete before slow chat (100)"

    @pytest.mark.asyncio
    async def test_each_chat_gets_independent_queue(self):
        bot = make_bot()
        q100 = bot._ensure_chat_worker(100)
        q200 = bot._ensure_chat_worker(200)
        q100_again = bot._ensure_chat_worker(100)

        assert q100 is q100_again,  "same chat must return same queue"
        assert q100 is not q200,    "different chats must have different queues"
        assert len(bot._chat_workers) == 2


# ─────────────────────────────────────────────
# 3. ترتيب FIFO داخل نفس الـ chat
# ─────────────────────────────────────────────

class TestChatFIFO:

    @pytest.mark.asyncio
    async def test_dispatch_order_preserved_within_chat(self):
        """
        تحقق أن كل update يبدأ dispatch بنفس الترتيب الذي وصل.
        """
        bot = make_bot()
        dispatch_order = []

        @bot.on("message")
        async def handler(ctx):
            dispatch_order.append(ctx.message.raw.get("message_id"))

        queue = bot._ensure_chat_worker(100)
        for i in range(1, 6):
            await queue.put(make_message(chat_id=100, update_id=i,
                                         text=f"msg {i}"))

        await asyncio.sleep(0.1)

        assert dispatch_order == [1, 2, 3, 4, 5], \
            f"expected FIFO order, got {dispatch_order}"


# ─────────────────────────────────────────────
# 4. ask() — لا deadlock عبر per-chat dispatch
# ─────────────────────────────────────────────

class TestAskNonBlocking:

    @pytest.mark.asyncio
    async def test_ask_resolves_via_chat_worker(self):
        """
        ask() يجب أن تنحل عندما تصل reply update عبر نفس الـ chat worker،
        بدون deadlock.
        """
        import warnings
        from titan.extras.ask import AskManager

        bot = make_bot()
        ask = AskManager()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            bot.middleware(ask.as_middleware())

        received = []

        async def mock_send(chat_id, text, **kwargs):
            return {"result": {"message_id": 99, "chat": {"id": chat_id}}}

        @bot.command("start")
        async def start(ctx):
            ctx._api.send_message = mock_send
            answer = await ask(ctx, "ما اسمك؟")
            received.append(answer)

        # الـ question update
        q_update = make_message("/start", user_id=1, chat_id=100, update_id=1)
        # الـ reply update (من نفس المستخدم، نفس الـ chat)
        r_update = make_message("Titan", user_id=1, chat_id=100, update_id=2)

        queue = bot._ensure_chat_worker(100)
        await queue.put(q_update)
        # نعطي الـ question handler فرصة ليسجّل الـ Future
        await asyncio.sleep(0.05)
        await queue.put(r_update)

        # الانتظار يجب أن ينتهي بدون deadlock
        try:
            await asyncio.wait_for(asyncio.sleep(0.2), timeout=1.0)
        except asyncio.TimeoutError:
            pytest.fail("ask() did not resolve — possible deadlock")

        assert received == ["Titan"], f"expected ['Titan'], got {received}"

    @pytest.mark.asyncio
    async def test_ask_in_one_chat_does_not_affect_another(self):
        """
        ask() معلّق في chat 100 لا يمنع chat 200 من المعالجة الطبيعية.
        """
        import warnings
        from titan.extras.ask import AskManager

        bot = make_bot()
        ask = AskManager()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            bot.middleware(ask.as_middleware())

        chat200_processed = []

        async def mock_send(chat_id, text, **kwargs):
            return {"result": {"message_id": 99, "chat": {"id": chat_id}}}

        @bot.command("start")
        async def start(ctx):
            ctx._api.send_message = mock_send
            if ctx.chat_id == 100:
                await ask(ctx, "سؤال لـ chat 100")
                # لن نرسل الرد — نتركه معلّقًا
            else:
                chat200_processed.append(ctx.chat_id)

        q100 = bot._ensure_chat_worker(100)
        q200 = bot._ensure_chat_worker(200)

        await q100.put(make_message("/start", chat_id=100, update_id=1))
        await asyncio.sleep(0.05)  # دع chat 100 يبلغ مرحلة ask()
        await q200.put(make_message("/start", chat_id=200, update_id=2))

        await asyncio.sleep(0.1)

        assert chat200_processed == [200], \
            "chat 200 must be processed independently of chat 100's pending ask()"


# ─────────────────────────────────────────────
# 5. Regression — _handle_update المباشر
# ─────────────────────────────────────────────

class TestHandleUpdateRegression:

    @pytest.mark.asyncio
    async def test_direct_handle_update_still_works(self):
        """
        _handle_update يمكن استدعاؤه مباشرة كما في الاختبارات القديمة.
        """
        bot = make_bot()
        seen = []

        @bot.on("message")
        async def handler(ctx):
            seen.append(ctx.text)

        await bot._handle_update(make_message("hello", update_id=1))
        assert seen == ["hello"]

    @pytest.mark.asyncio
    async def test_command_handler_regression(self):
        bot = make_bot()
        called = []

        @bot.command("start")
        async def start(ctx):
            called.append(True)

        await bot._handle_update(make_message("/start", update_id=1))
        assert called == [True]

    @pytest.mark.asyncio
    async def test_callback_handler_regression(self):
        bot = make_bot()
        result = []

        @bot.callback("ok")
        async def cb(ctx):
            result.append(ctx.callback_data)

        await bot._handle_update(make_callback(data="ok", update_id=1))
        assert result == ["ok"]
