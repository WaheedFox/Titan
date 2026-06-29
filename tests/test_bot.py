import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from titan.bot import Titan
from titan.errors import TitanError


def make_bot():
    return Titan("fake-token")


class TestExtractCommand:
    def setup_method(self):
        self.bot = make_bot()

    def test_simple_command(self):
        assert self.bot._extract_command("/start") == "start"

    def test_command_with_bot_name(self):
        assert self.bot._extract_command("/start@MyBot") == "start"

    def test_command_with_args(self):
        assert self.bot._extract_command("/help me please") == "help"

    def test_not_a_command(self):
        assert self.bot._extract_command("hello") is None

    def test_empty_string(self):
        assert self.bot._extract_command("") is None

    def test_slash_only(self):
        assert self.bot._extract_command("/") is None

    def test_command_with_at_and_args(self):
        assert self.bot._extract_command("/ban@MyBot user123") == "ban"


class TestHandlerRegistration:
    def setup_method(self):
        self.bot = make_bot()

    def test_on_registers_handler(self):
        async def handler(ctx): pass
        self.bot.on("message")(handler)
        assert handler in self.bot.handlers["message"]

    def test_on_multiple_handlers_same_event(self):
        async def h1(ctx): pass
        async def h2(ctx): pass
        self.bot.on("message")(h1)
        self.bot.on("message")(h2)
        assert len(self.bot.handlers["message"]) == 2

    def test_on_returns_func(self):
        async def handler(ctx): pass
        result = self.bot.on("message")(handler)
        assert result is handler

    def test_command_registers(self):
        async def start(ctx): pass
        self.bot.command("start")(start)
        assert self.bot.commands["start"] is start

    def test_command_duplicate_raises(self):
        async def h(ctx): pass
        self.bot.command("start")(h)
        with pytest.raises(TitanError, match=r"Command 'start' is already registered"):
            self.bot.command("start")(h)

    def test_command_returns_func(self):
        async def start(ctx): pass
        result = self.bot.command("start")(start)
        assert result is start

    def test_callback_registers(self):
        async def on_yes(ctx): pass
        self.bot.callback("yes")(on_yes)
        assert self.bot.callback_handlers["yes"] is on_yes

    def test_callback_duplicate_raises(self):
        async def h(ctx): pass
        self.bot.callback("yes")(h)
        with pytest.raises(TitanError, match=r"Callback data 'yes' is already registered"):
            self.bot.callback("yes")(h)

    def test_callback_returns_func(self):
        async def h(ctx): pass
        result = self.bot.callback("yes")(h)
        assert result is h


class TestDispatch:
    def setup_method(self):
        self.bot = make_bot()

    @pytest.mark.asyncio
    async def test_dispatch_calls_handler(self):
        called = []

        async def h(ctx):
            called.append(True)

        self.bot.on("message")(h)
        mock_ctx = MagicMock()
        await self.bot._dispatch("message", mock_ctx)
        assert called == [True]

    @pytest.mark.asyncio
    async def test_dispatch_calls_multiple_handlers(self):
        results = []

        async def h1(ctx): results.append("h1")
        async def h2(ctx): results.append("h2")

        self.bot.on("message")(h1)
        self.bot.on("message")(h2)
        await self.bot._dispatch("message", MagicMock())
        assert results == ["h1", "h2"]

    @pytest.mark.asyncio
    async def test_dispatch_no_handler_is_safe(self):
        await self.bot._dispatch("unknown_event", MagicMock())

    @pytest.mark.asyncio
    async def test_dispatch_handler_exception_is_caught(self):
        async def bad(ctx):
            raise RuntimeError("oops")

        self.bot.on("message")(bad)
        await self.bot._dispatch("message", MagicMock())


class TestHandleUpdate:
    def setup_method(self):
        self.bot = make_bot()
        self.bot._api = MagicMock()
        self.bot._api.send_message = AsyncMock(return_value={"ok": True})

    @pytest.mark.asyncio
    async def test_routes_message_to_message_handler(self):
        calls = []

        @self.bot.on("message")
        async def h(ctx):
            calls.append("message")

        raw = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "text": "hi",
                "from": {"id": 1, "username": "u"},
                "chat": {"id": 1, "type": "private"},
            },
        }
        await self.bot._handle_update(raw)
        assert calls == ["message"]

    @pytest.mark.asyncio
    async def test_routes_command_to_command_handler(self):
        calls = []

        @self.bot.command("start")
        async def h(ctx):
            calls.append("start")

        raw = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "text": "/start",
                "from": {"id": 1, "username": "u"},
                "chat": {"id": 1, "type": "private"},
            },
        }
        await self.bot._handle_update(raw)
        assert calls == ["start"]

    @pytest.mark.asyncio
    async def test_unknown_command_falls_through_to_message(self):
        calls = []

        @self.bot.on("message")
        async def h(ctx):
            calls.append("message")

        raw = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "text": "/unknown",
                "from": {"id": 1, "username": "u"},
                "chat": {"id": 1, "type": "private"},
            },
        }
        await self.bot._handle_update(raw)
        assert calls == ["message"]

    @pytest.mark.asyncio
    async def test_routes_channel_post(self):
        calls = []

        @self.bot.on("channel")
        async def h(ctx):
            calls.append("channel")

        raw = {
            "update_id": 2,
            "channel_post": {
                "message_id": 2,
                "text": "news",
                "chat": {"id": 2, "type": "channel"},
            },
        }
        await self.bot._handle_update(raw)
        assert calls == ["channel"]

    @pytest.mark.asyncio
    async def test_routes_callback_to_specific_handler(self):
        calls = []

        @self.bot.callback("yes")
        async def h(ctx):
            calls.append("yes")

        raw = {
            "update_id": 3,
            "callback_query": {
                "id": "cq1",
                "data": "yes",
                "from": {"id": 1, "username": "u"},
                "message": {"message_id": 1, "chat": {"id": 1, "type": "private"}},
            },
        }
        await self.bot._handle_update(raw)
        assert calls == ["yes"]

    @pytest.mark.asyncio
    async def test_callback_falls_back_to_generic_handler(self):
        calls = []

        @self.bot.on("callback")
        async def h(ctx):
            calls.append("generic")

        raw = {
            "update_id": 3,
            "callback_query": {
                "id": "cq1",
                "data": "unknown",
                "from": {"id": 1, "username": "u"},
                "message": {"message_id": 1, "chat": {"id": 1, "type": "private"}},
            },
        }
        await self.bot._handle_update(raw)
        assert calls == ["generic"]

    @pytest.mark.asyncio
    async def test_routes_new_member(self):
        calls = []

        @self.bot.on("new_member")
        async def h(ctx):
            calls.append("new_member")

        raw = {
            "update_id": 4,
            "message": {
                "message_id": 4,
                "chat": {"id": 1, "type": "supergroup"},
                "new_chat_members": [{"id": 77, "first_name": "Ali"}],
            },
        }
        await self.bot._handle_update(raw)
        assert calls == ["new_member"]

    @pytest.mark.asyncio
    async def test_routes_left_member(self):
        calls = []

        @self.bot.on("left_member")
        async def h(ctx):
            calls.append("left_member")

        raw = {
            "update_id": 5,
            "message": {
                "message_id": 5,
                "chat": {"id": 1, "type": "supergroup"},
                "left_chat_member": {"id": 88, "first_name": "Sara"},
            },
        }
        await self.bot._handle_update(raw)
        assert calls == ["left_member"]

    @pytest.mark.asyncio
    async def test_command_handler_exception_is_caught(self):
        @self.bot.command("crash")
        async def h(ctx):
            raise RuntimeError("crash!")

        raw = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "text": "/crash",
                "from": {"id": 1, "username": "u"},
                "chat": {"id": 1, "type": "private"},
            },
        }
        await self.bot._handle_update(raw)

    @pytest.mark.asyncio
    async def test_callback_handler_exception_is_caught(self):
        @self.bot.callback("boom")
        async def h(ctx):
            raise RuntimeError("boom!")

        raw = {
            "update_id": 1,
            "callback_query": {
                "id": "cq1",
                "data": "boom",
                "from": {"id": 1, "username": "u"},
                "message": {"message_id": 1, "chat": {"id": 1, "type": "private"}},
            },
        }
        await self.bot._handle_update(raw)
