import pytest

from titan.bot import Titan
from titan.playground import RecordingTelegram, fake_callback, fake_command, fake_message


def make_bot() -> tuple[Titan, RecordingTelegram]:
    bot = Titan("dummy-token")
    api = RecordingTelegram()
    bot._api = api
    bot.telegram._api = api
    return bot, api


class TestFeedUpdateBasicRouting:
    @pytest.mark.asyncio
    async def test_feed_update_dispatches_to_message_handler(self):
        bot, _ = make_bot()
        received = []

        @bot.on("message")
        async def on_message(ctx):
            received.append(ctx.text)

        await bot.feed_update(fake_message("hello"))

        assert received == ["hello"]

    @pytest.mark.asyncio
    async def test_feed_update_dispatches_to_command_handler(self):
        bot, _ = make_bot()
        called = []

        @bot.command("start")
        async def on_start(ctx):
            called.append(ctx.chat_id)

        await bot.feed_update(fake_command("start"))

        assert called == [1]

    @pytest.mark.asyncio
    async def test_feed_update_command_does_not_trigger_message_handler(self):
        bot, _ = make_bot()
        message_calls = []
        command_calls = []

        @bot.on("message")
        async def on_message(ctx):
            message_calls.append(ctx.text)

        @bot.command("start")
        async def on_start(ctx):
            command_calls.append(True)

        await bot.feed_update(fake_command("start"))

        assert command_calls == [True]
        assert message_calls == []


class TestFeedUpdateCallbackRouting:
    @pytest.mark.asyncio
    async def test_feed_update_routes_specific_callback(self):
        bot, _ = make_bot()
        called = []

        @bot.callback("yes")
        async def on_yes(ctx):
            called.append(ctx.callback_data)

        await bot.feed_update(fake_callback("yes"))

        assert called == ["yes"]

    @pytest.mark.asyncio
    async def test_feed_update_falls_back_to_generic_callback_handler(self):
        bot, _ = make_bot()
        called = []

        @bot.on("callback")
        async def on_any_callback(ctx):
            called.append(ctx.callback_data)

        await bot.feed_update(fake_callback("unregistered"))

        assert called == ["unregistered"]


class TestFeedUpdateMiddleware:
    @pytest.mark.asyncio
    async def test_middleware_runs_before_handler(self):
        bot, _ = make_bot()
        order = []

        @bot.middleware
        async def guard(ctx, next):
            order.append("middleware")
            await next()

        @bot.on("message")
        async def on_message(ctx):
            order.append("handler")

        await bot.feed_update(fake_message("hi"))

        assert order == ["middleware", "handler"]

    @pytest.mark.asyncio
    async def test_middleware_can_block_handler(self):
        bot, _ = make_bot()
        handler_called = []

        @bot.middleware
        async def block(ctx, next):
            pass  # لا تستدعي next() — يجب أن يتوقف الـ update هنا

        @bot.on("message")
        async def on_message(ctx):
            handler_called.append(True)

        await bot.feed_update(fake_message("hi"))

        assert handler_called == []


class TestRecordingTelegram:
    @pytest.mark.asyncio
    async def test_reply_is_recorded_not_sent_over_network(self):
        bot, api = make_bot()

        @bot.on("message")
        async def on_message(ctx):
            await ctx.reply("مرحباً")

        await bot.feed_update(fake_message("hi"))

        assert len(api.calls) == 1
        assert api.calls[0]["method"] == "send_message"
        assert api.calls[0]["text"] == "مرحباً"

    @pytest.mark.asyncio
    async def test_answer_callback_is_recorded(self):
        bot, api = make_bot()

        @bot.callback("ok")
        async def on_ok(ctx):
            await ctx.answer_callback("تم")

        await bot.feed_update(fake_callback("ok"))

        methods = [c["method"] for c in api.calls]
        assert "answer_callback_query" in methods

    @pytest.mark.asyncio
    async def test_unsupported_api_method_fails_clearly(self):
        api = RecordingTelegram()

        with pytest.raises(AttributeError):
            await api.send_video(chat_id=1, video="x")


class TestNoPipelineDrift:
    """
    يثبت أن feed_update() يمر عبر نفس مسار _handle_update الحقيقي —
    بدون أي منطق dispatch موازٍ داخل Playground أو feed_update نفسها.
    """

    @pytest.mark.asyncio
    async def test_feed_update_and_handle_update_produce_identical_dispatch(self):
        bot_a, _ = make_bot()
        bot_b, _ = make_bot()

        trace_a = []
        trace_b = []

        @bot_a.on("message")
        async def handler_a(ctx):
            trace_a.append(ctx.text)

        @bot_b.on("message")
        async def handler_b(ctx):
            trace_b.append(ctx.text)

        update = fake_message("same behavior")

        await bot_a.feed_update(update)
        await bot_b._handle_update(update)

        assert trace_a == trace_b == ["same behavior"]

    def test_feed_update_delegates_directly_without_extra_logic(self):
        import inspect

        source = inspect.getsource(Titan.feed_update)
        # يجب أن يقتصر الجسم على استدعاء _handle_update — لا شروط، لا حلقات
        assert "await self._handle_update(update)" in source
        assert "if " not in source
        assert "for " not in source
