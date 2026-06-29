import pytest
from titan import Titan, Router
from titan.errors import TitanError


# -------------------------
# Router Registration
# -------------------------

class TestRouterOn:
    def test_registers_handler(self):
        router = Router()

        @router.on("message")
        async def handler(ctx): ...

        assert "message" in router.handlers
        assert handler in router.handlers["message"]

    def test_registers_multiple_handlers_same_event(self):
        router = Router()

        @router.on("message")
        async def h1(ctx): ...

        @router.on("message")
        async def h2(ctx): ...

        assert len(router.handlers["message"]) == 2

    def test_returns_func(self):
        router = Router()

        @router.on("message")
        async def handler(ctx): ...

        assert callable(handler)


class TestRouterCommand:
    def test_registers_command(self):
        router = Router()

        @router.command("start")
        async def start(ctx): ...

        assert "start" in router.commands

    def test_duplicate_command_raises(self):
        router = Router()

        @router.command("start")
        async def start(ctx): ...

        with pytest.raises(TitanError):
            @router.command("start")
            async def start2(ctx): ...

    def test_returns_func(self):
        router = Router()

        @router.command("start")
        async def start(ctx): ...

        assert callable(start)


class TestRouterCallback:
    def test_registers_callback(self):
        router = Router()

        @router.callback("yes")
        async def on_yes(ctx): ...

        assert "yes" in router.callback_handlers

    def test_duplicate_callback_raises(self):
        router = Router()

        @router.callback("yes")
        async def on_yes(ctx): ...

        with pytest.raises(TitanError):
            @router.callback("yes")
            async def on_yes2(ctx): ...

    def test_returns_func(self):
        router = Router()

        @router.callback("yes")
        async def on_yes(ctx): ...

        assert callable(on_yes)


# -------------------------
# bot.include()
# -------------------------

class TestBotInclude:
    def test_include_merges_handlers(self):
        bot = Titan("token")
        router = Router()

        @router.on("message")
        async def handler(ctx): ...

        bot.include(router)
        assert handler in bot.handlers["message"]

    def test_include_merges_commands(self):
        bot = Titan("token")
        router = Router()

        @router.command("start")
        async def start(ctx): ...

        bot.include(router)
        assert "start" in bot.commands

    def test_include_merges_callbacks(self):
        bot = Titan("token")
        router = Router()

        @router.callback("yes")
        async def on_yes(ctx): ...

        bot.include(router)
        assert "yes" in bot.callback_handlers

    def test_include_multiple_routers(self):
        bot = Titan("token")

        r1 = Router()
        @r1.command("start")
        async def start(ctx): ...

        r2 = Router()
        @r2.command("help")
        async def help(ctx): ...

        bot.include(r1)
        bot.include(r2)

        assert "start" in bot.commands
        assert "help" in bot.commands

    def test_include_command_conflict_with_bot_raises(self):
        bot = Titan("token")

        @bot.command("start")
        async def start(ctx): ...

        router = Router()

        @router.command("start")
        async def start2(ctx): ...

        with pytest.raises(TitanError):
            bot.include(router)

    def test_include_callback_conflict_with_bot_raises(self):
        bot = Titan("token")

        @bot.callback("yes")
        async def on_yes(ctx): ...

        router = Router()

        @router.callback("yes")
        async def on_yes2(ctx): ...

        with pytest.raises(TitanError):
            bot.include(router)

    def test_include_does_not_affect_router(self):
        bot = Titan("token")
        router = Router()

        @router.command("start")
        async def start(ctx): ...

        bot.include(router)

        assert "start" in router.commands

    def test_include_returns_none(self):
        bot = Titan("token")
        router = Router()
        result = bot.include(router)
        assert result is None
