"""
Contract tests for @bot.error_handler.

Covers all four execution routes where exceptions may arise:
  1. @bot.on() handlers  → via _dispatch
  2. @bot.command()      → direct invocation in _handle_update
  3. @bot.callback()     → direct invocation in _handle_update
  4. Middleware          → exception from middleware itself

Also covers cross-cutting contract behaviors:
  - error handler receives the correct ctx and exc
  - fallback to stdout when no error handler is registered
  - error handler that raises does not break the update cycle
  - second registration replaces the first
  - multiple failing handlers each invoke the error handler
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from titan.bot import Titan
from titan.ctx import Context


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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

RAW_COMMAND = {
    "update_id": 2,
    "message": {
        "message_id": 11,
        "text": "/start",
        "from": {"id": 99, "username": "ali"},
        "chat": {"id": 200, "type": "private"},
    },
}

RAW_CALLBACK = {
    "update_id": 3,
    "callback_query": {
        "id": "cq1",
        "data": "confirm",
        "from": {"id": 99, "username": "ali"},
        "message": {
            "message_id": 12,
            "chat": {"id": 200, "type": "private"},
        },
    },
}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestErrorHandlerRegistration:
    def setup_method(self):
        self.bot = make_bot()

    def test_no_error_handler_by_default(self):
        assert self.bot._error_handler is None

    def test_registration_stores_function(self):
        async def on_error(ctx, exc): pass
        self.bot.error_handler(on_error)
        assert self.bot._error_handler is on_error

    def test_decorator_returns_function(self):
        async def on_error(ctx, exc): pass
        result = self.bot.error_handler(on_error)
        assert result is on_error

    def test_second_registration_replaces_first(self):
        async def first(ctx, exc): pass
        async def second(ctx, exc): pass
        self.bot.error_handler(first)
        self.bot.error_handler(second)
        assert self.bot._error_handler is second

    @pytest.mark.asyncio
    async def test_no_error_no_handler_called(self):
        called = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            called.append(exc)

        @self.bot.on("message")
        async def handler(ctx):
            pass  # no exception

        await self.bot._handle_update(RAW_MESSAGE)
        assert called == []


# ---------------------------------------------------------------------------
# Route 1: @bot.on() handlers via _dispatch
# ---------------------------------------------------------------------------

class TestDispatchRoute:
    def setup_method(self):
        self.bot = make_bot()

    @pytest.mark.asyncio
    async def test_on_handler_exception_calls_error_handler(self):
        error = RuntimeError("dispatch-route failure")
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(exc)

        @self.bot.on("message")
        async def bad(ctx):
            raise error

        await self.bot._handle_update(RAW_MESSAGE)
        assert received == [error]

    @pytest.mark.asyncio
    async def test_error_handler_receives_correct_exception_type(self):
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(type(exc))

        @self.bot.on("message")
        async def bad(ctx):
            raise ValueError("bad value")

        await self.bot._handle_update(RAW_MESSAGE)
        assert received == [ValueError]

    @pytest.mark.asyncio
    async def test_error_handler_receives_ctx(self):
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(ctx)

        @self.bot.on("message")
        async def bad(ctx):
            raise RuntimeError()

        await self.bot._handle_update(RAW_MESSAGE)
        assert len(received) == 1
        assert isinstance(received[0], Context)

    @pytest.mark.asyncio
    async def test_multiple_failing_on_handlers_each_invoke_error_handler(self):
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(exc)

        err1 = RuntimeError("first")
        err2 = RuntimeError("second")

        @self.bot.on("message")
        async def bad1(ctx):
            raise err1

        @self.bot.on("message")
        async def bad2(ctx):
            raise err2

        await self.bot._handle_update(RAW_MESSAGE)
        assert err1 in received
        assert err2 in received
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_second_on_handler_runs_even_if_first_raises(self):
        ran = []

        @self.bot.error_handler
        async def on_error(ctx, exc): pass

        @self.bot.on("message")
        async def bad(ctx):
            raise RuntimeError()

        @self.bot.on("message")
        async def good(ctx):
            ran.append("good")

        await self.bot._handle_update(RAW_MESSAGE)
        assert ran == ["good"]


# ---------------------------------------------------------------------------
# Route 2: @bot.command() handlers
# ---------------------------------------------------------------------------

class TestCommandRoute:
    def setup_method(self):
        self.bot = make_bot()

    @pytest.mark.asyncio
    async def test_command_exception_calls_error_handler(self):
        error = RuntimeError("command-route failure")
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(exc)

        @self.bot.command("start")
        async def bad(ctx):
            raise error

        await self.bot._handle_update(RAW_COMMAND)
        assert received == [error]

    @pytest.mark.asyncio
    async def test_command_error_handler_receives_ctx(self):
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(ctx)

        @self.bot.command("start")
        async def bad(ctx):
            raise RuntimeError()

        await self.bot._handle_update(RAW_COMMAND)
        assert len(received) == 1
        assert isinstance(received[0], Context)

    @pytest.mark.asyncio
    async def test_command_exception_does_not_propagate(self):
        @self.bot.error_handler
        async def on_error(ctx, exc): pass

        @self.bot.command("start")
        async def bad(ctx):
            raise RuntimeError("should not propagate")

        await self.bot._handle_update(RAW_COMMAND)  # must not raise


# ---------------------------------------------------------------------------
# Route 3: @bot.callback() handlers
# ---------------------------------------------------------------------------

class TestCallbackRoute:
    def setup_method(self):
        self.bot = make_bot()

    @pytest.mark.asyncio
    async def test_callback_exception_calls_error_handler(self):
        error = RuntimeError("callback-route failure")
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(exc)

        @self.bot.callback("confirm")
        async def bad(ctx):
            raise error

        await self.bot._handle_update(RAW_CALLBACK)
        assert received == [error]

    @pytest.mark.asyncio
    async def test_callback_error_handler_receives_ctx(self):
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(ctx)

        @self.bot.callback("confirm")
        async def bad(ctx):
            raise RuntimeError()

        await self.bot._handle_update(RAW_CALLBACK)
        assert len(received) == 1
        assert isinstance(received[0], Context)

    @pytest.mark.asyncio
    async def test_callback_exception_does_not_propagate(self):
        @self.bot.error_handler
        async def on_error(ctx, exc): pass

        @self.bot.callback("confirm")
        async def bad(ctx):
            raise RuntimeError("should not propagate")

        await self.bot._handle_update(RAW_CALLBACK)  # must not raise


# ---------------------------------------------------------------------------
# Route 4: Middleware exceptions
# ---------------------------------------------------------------------------

class TestMiddlewareRoute:
    def setup_method(self):
        self.bot = make_bot()

    @pytest.mark.asyncio
    async def test_middleware_exception_calls_error_handler(self):
        error = RuntimeError("middleware-route failure")
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(exc)

        @self.bot.middleware
        async def bad_middleware(ctx, next):
            raise error

        @self.bot.on("message")
        async def handler(ctx): pass

        await self.bot._handle_update(RAW_MESSAGE)
        assert received == [error]

    @pytest.mark.asyncio
    async def test_middleware_error_handler_receives_ctx(self):
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(ctx)

        @self.bot.middleware
        async def bad_middleware(ctx, next):
            raise RuntimeError()

        await self.bot._handle_update(RAW_MESSAGE)
        assert len(received) == 1
        assert isinstance(received[0], Context)

    @pytest.mark.asyncio
    async def test_middleware_exception_does_not_trigger_polling_backoff(self):
        """
        A middleware exception must be caught by _handle_error and must not
        propagate out of _handle_update. If it did, the polling loop would
        treat it as a network error and apply backoff.
        """
        @self.bot.error_handler
        async def on_error(ctx, exc): pass

        @self.bot.middleware
        async def bad_middleware(ctx, next):
            raise RuntimeError("should not escape _handle_update")

        await self.bot._handle_update(RAW_MESSAGE)  # must not raise


# ---------------------------------------------------------------------------
# Cross-cutting contract behaviors
# ---------------------------------------------------------------------------

class TestErrorHandlerContract:
    def setup_method(self):
        self.bot = make_bot()

    @pytest.mark.asyncio
    async def test_fallback_to_log_when_no_error_handler_registered(self):
        logged = []

        @self.bot.on("message")
        async def bad(ctx):
            raise RuntimeError("unhandled")

        with patch.object(self.bot, "_log") as mock_log:
            await self.bot._handle_update(RAW_MESSAGE)
            assert mock_log.called
            logged_message = mock_log.call_args[0][0]
            assert "Unhandled exception" in logged_message

    @pytest.mark.asyncio
    async def test_error_handler_that_raises_does_not_break_update_cycle(self):
        """
        If the error handler itself raises, that inner exception must be
        caught and logged. The update cycle must not crash.
        """
        @self.bot.error_handler
        async def bad_error_handler(ctx, exc):
            raise RuntimeError("error handler itself blew up")

        @self.bot.on("message")
        async def bad(ctx):
            raise RuntimeError("original error")

        with patch.object(self.bot, "_log") as mock_log:
            await self.bot._handle_update(RAW_MESSAGE)  # must not raise
            assert mock_log.called
            logged_message = mock_log.call_args[0][0]
            assert "error handler" in logged_message.lower()

    @pytest.mark.asyncio
    async def test_error_handler_ctx_has_correct_user_id(self):
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(ctx.user_id)

        @self.bot.on("message")
        async def bad(ctx):
            raise RuntimeError()

        await self.bot._handle_update(RAW_MESSAGE)
        assert received == [99]

    @pytest.mark.asyncio
    async def test_error_handler_ctx_has_correct_chat_id(self):
        received = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received.append(ctx.chat_id)

        @self.bot.command("start")
        async def bad(ctx):
            raise RuntimeError()

        await self.bot._handle_update(RAW_COMMAND)
        assert received == [200]

    @pytest.mark.asyncio
    async def test_successful_handler_after_registration_not_affected(self):
        """
        Registering an error handler must not change behavior for handlers
        that do not raise.
        """
        results = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            results.append("error")

        @self.bot.on("message")
        async def good(ctx):
            results.append("ok")

        await self.bot._handle_update(RAW_MESSAGE)
        assert results == ["ok"]

    @pytest.mark.asyncio
    async def test_all_four_routes_share_same_error_handler(self):
        """
        A single registered error handler must intercept exceptions
        regardless of which route they originate from.
        """
        received_routes = []

        @self.bot.error_handler
        async def on_error(ctx, exc):
            received_routes.append(str(exc))

        @self.bot.on("message")
        async def bad_on(ctx):
            raise RuntimeError("from-on")

        @self.bot.command("start")
        async def bad_cmd(ctx):
            raise RuntimeError("from-command")

        @self.bot.callback("confirm")
        async def bad_cb(ctx):
            raise RuntimeError("from-callback")

        await self.bot._handle_update(RAW_MESSAGE)
        await self.bot._handle_update(RAW_COMMAND)
        await self.bot._handle_update(RAW_CALLBACK)

        assert "from-on" in received_routes
        assert "from-command" in received_routes
        assert "from-callback" in received_routes
