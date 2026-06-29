import pytest
from unittest.mock import AsyncMock, MagicMock
from titan.bot import Titan
from titan.ctx import Context
from titan.update import Update
from titan.middleware import MiddlewareChain


def make_bot():
    bot = Titan("fake-token")
    bot._api = MagicMock()
    bot._api.send_message = AsyncMock(return_value={"ok": True})
    return bot


RAW_MESSAGE = {
    "update_id": 1,
    "message": {
        "message_id": 10,
        "text": "hello",
        "from": {"id": 99, "username": "ali"},
        "chat": {"id": 200, "type": "private"},
    },
}

RAW_MESSAGE_USER_2 = {
    "update_id": 2,
    "message": {
        "message_id": 11,
        "text": "hi",
        "from": {"id": 55, "username": "bob"},
        "chat": {"id": 200, "type": "private"},
    },
}

RAW_NO_USER = {
    "update_id": 3,
    "message": {
        "message_id": 12,
        "chat": {"id": 300, "type": "channel"},
    },
}


class TestContextIsBanned:
    def test_is_banned_default_false(self):
        ctx = Context(Update(RAW_MESSAGE), MagicMock())
        assert ctx.is_banned is False

    def test_is_banned_is_bool(self):
        ctx = Context(Update(RAW_MESSAGE), MagicMock())
        assert isinstance(ctx.is_banned, bool)


class TestBotBannedUsers:
    def test_banned_users_initially_empty(self):
        bot = make_bot()
        assert bot.banned_users == set()

    def test_add_to_banned_users(self):
        bot = make_bot()
        bot.banned_users.add(99)
        assert 99 in bot.banned_users

    def test_remove_from_banned_users(self):
        bot = make_bot()
        bot.banned_users.add(99)
        bot.banned_users.discard(99)
        assert 99 not in bot.banned_users

    @pytest.mark.asyncio
    async def test_ctx_is_banned_true_for_banned_user(self):
        bot = make_bot()
        bot.banned_users.add(99)
        received = []

        @bot.on("message")
        async def handler(ctx):
            received.append(ctx.is_banned)

        await bot._handle_update(RAW_MESSAGE)
        assert received == [True]

    @pytest.mark.asyncio
    async def test_ctx_is_banned_false_for_non_banned_user(self):
        bot = make_bot()
        received = []

        @bot.on("message")
        async def handler(ctx):
            received.append(ctx.is_banned)

        await bot._handle_update(RAW_MESSAGE)
        assert received == [False]

    @pytest.mark.asyncio
    async def test_ctx_is_banned_false_when_no_user_id(self):
        bot = make_bot()
        bot.banned_users.add(99)
        received = []

        @bot.on("message")
        async def handler(ctx):
            received.append(ctx.is_banned)

        await bot._handle_update(RAW_NO_USER)
        assert received == [False]

    @pytest.mark.asyncio
    async def test_only_banned_user_is_marked(self):
        bot = make_bot()
        bot.banned_users.add(99)
        received = {}

        @bot.on("message")
        async def handler(ctx):
            received[ctx.user_id] = ctx.is_banned

        await bot._handle_update(RAW_MESSAGE)
        await bot._handle_update(RAW_MESSAGE_USER_2)
        assert received[99] is True
        assert received[55] is False


class TestMiddlewareChain:
    @pytest.mark.asyncio
    async def test_empty_chain_calls_handler(self):
        chain = MiddlewareChain()
        called = []

        async def handler():
            called.append(True)

        ctx = Context(Update(RAW_MESSAGE), MagicMock())
        await chain.run(ctx, handler)
        assert called == [True]

    @pytest.mark.asyncio
    async def test_middleware_calling_next_continues(self):
        chain = MiddlewareChain()
        called = []

        async def mw(ctx, next):
            called.append("mw")
            await next()

        async def handler():
            called.append("handler")

        chain.add(mw)
        ctx = Context(Update(RAW_MESSAGE), MagicMock())
        await chain.run(ctx, handler)
        assert called == ["mw", "handler"]

    @pytest.mark.asyncio
    async def test_middleware_not_calling_next_stops(self):
        chain = MiddlewareChain()
        called = []

        async def mw(ctx, next):
            called.append("mw")

        async def handler():
            called.append("handler")

        chain.add(mw)
        ctx = Context(Update(RAW_MESSAGE), MagicMock())
        await chain.run(ctx, handler)
        assert called == ["mw"]

    @pytest.mark.asyncio
    async def test_multiple_middleware_all_call_next(self):
        chain = MiddlewareChain()
        order = []

        async def m1(ctx, next):
            order.append(1)
            await next()

        async def m2(ctx, next):
            order.append(2)
            await next()

        async def handler():
            order.append("handler")

        chain.add(m1)
        chain.add(m2)
        ctx = Context(Update(RAW_MESSAGE), MagicMock())
        await chain.run(ctx, handler)
        assert order == [1, 2, "handler"]

    @pytest.mark.asyncio
    async def test_first_middleware_stops_chain(self):
        chain = MiddlewareChain()
        order = []

        async def m1(ctx, next):
            order.append(1)

        async def m2(ctx, next):
            order.append(2)
            await next()

        async def handler():
            order.append("handler")

        chain.add(m1)
        chain.add(m2)
        ctx = Context(Update(RAW_MESSAGE), MagicMock())
        await chain.run(ctx, handler)
        assert order == [1]


class TestBotMiddleware:
    def test_middleware_registers(self):
        bot = make_bot()

        async def guard(ctx, next): pass

        bot.middleware(guard)
        assert guard in bot.middleware_chain._chain

    def test_middleware_returns_fn(self):
        bot = make_bot()

        async def guard(ctx, next): pass

        result = bot.middleware(guard)
        assert result is guard

    def test_middleware_as_decorator(self):
        bot = make_bot()

        @bot.middleware
        async def guard(ctx, next): pass

        assert guard in bot.middleware_chain._chain

    @pytest.mark.asyncio
    async def test_middleware_blocks_banned_user(self):
        bot = make_bot()
        bot.banned_users.add(99)
        called = []

        @bot.middleware
        async def guard(ctx, next):
            if ctx.is_banned:
                return
            await next()

        @bot.on("message")
        async def handler(ctx):
            called.append(True)

        await bot._handle_update(RAW_MESSAGE)
        assert called == []

    @pytest.mark.asyncio
    async def test_middleware_allows_non_banned(self):
        bot = make_bot()
        called = []

        @bot.middleware
        async def guard(ctx, next):
            if ctx.is_banned:
                return
            await next()

        @bot.on("message")
        async def handler(ctx):
            called.append(True)

        await bot._handle_update(RAW_MESSAGE)
        assert called == [True]

    @pytest.mark.asyncio
    async def test_no_middleware_handler_runs(self):
        bot = make_bot()
        called = []

        @bot.on("message")
        async def handler(ctx):
            called.append(True)

        await bot._handle_update(RAW_MESSAGE)
        assert called == [True]
