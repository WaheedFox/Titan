import pytest
from unittest.mock import AsyncMock, MagicMock
from titan.alias import AliasMap
from titan.bot import Titan
from titan.ctx import Context
from titan.update import Update
from titan.errors import TitanError


def make_ctx(raw_update: dict) -> Context:
    api = MagicMock()
    api.send_message = AsyncMock(return_value={"ok": True})
    api.edit_message_text = AsyncMock(return_value={"ok": True})
    api.delete_message = AsyncMock(return_value={"ok": True})
    api.ban_user = AsyncMock(return_value={"ok": True})
    api.leave_chat = AsyncMock(return_value={"ok": True})
    api.get_chat_member = AsyncMock(return_value={"ok": True, "result": {}})
    api.get_me = AsyncMock(return_value={"id": 1})
    api.answer_callback_query = AsyncMock(return_value={"ok": True})
    return Context(Update(raw_update), api)


RAW_MESSAGE = {
    "update_id": 1,
    "message": {
        "message_id": 10,
        "text": "hello",
        "from": {"id": 99, "username": "ali"},
        "chat": {"id": 200, "type": "private"},
    },
}


class TestAliasMap:
    def test_register_valid_alias(self):
        am = AliasMap()
        am.register("say", "reply")
        assert "say" in am._map
        assert am._map["say"] == "reply"

    def test_register_invalid_target_raises(self):
        am = AliasMap()
        with pytest.raises(TitanError, match=r"does not exist in Context"):
            am.register("foo", "nonexistent_method")

    def test_apply_sets_alias_on_ctx(self):
        am = AliasMap()
        am.register("say", "reply")
        ctx = make_ctx(RAW_MESSAGE)
        am.apply(ctx)
        assert hasattr(ctx, "say")
        assert ctx.say == ctx.reply

    def test_apply_multiple_aliases(self):
        am = AliasMap()
        am.register("say", "reply")
        am.register("shout", "send")
        ctx = make_ctx(RAW_MESSAGE)
        am.apply(ctx)
        assert ctx.say == ctx.reply
        assert ctx.shout == ctx.send

    def test_original_method_unchanged_after_apply(self):
        am = AliasMap()
        am.register("say", "reply")
        ctx = make_ctx(RAW_MESSAGE)
        original_reply = ctx.reply
        am.apply(ctx)
        assert ctx.reply == original_reply

    def test_empty_alias_map_apply_is_safe(self):
        am = AliasMap()
        ctx = make_ctx(RAW_MESSAGE)
        am.apply(ctx)

    def test_register_property_alias(self):
        am = AliasMap()
        am.register("who", "user_id")
        ctx = make_ctx(RAW_MESSAGE)
        am.apply(ctx)
        assert ctx.who == ctx.user_id

    def test_register_multiple_aliases_to_same_target(self):
        am = AliasMap()
        am.register("say", "reply")
        am.register("respond", "reply")
        ctx = make_ctx(RAW_MESSAGE)
        am.apply(ctx)
        assert ctx.say == ctx.reply
        assert ctx.respond == ctx.reply


class TestBotAlias:
    def setup_method(self):
        self.bot = Titan("fake-token")
        self.bot._api = MagicMock()
        self.bot._api.send_message = AsyncMock(return_value={"ok": True})

    def test_bot_has_alias_method(self):
        assert hasattr(self.bot, "alias")

    def test_bot_alias_registers(self):
        self.bot.alias("say", "reply")
        assert self.bot.aliases._map["say"] == "reply"

    def test_bot_alias_invalid_raises(self):
        with pytest.raises(TitanError, match=r"does not exist in Context"):
            self.bot.alias("foo", "does_not_exist")

    @pytest.mark.asyncio
    async def test_alias_available_in_handler(self):
        self.bot.alias("say", "reply")
        received = []

        @self.bot.on("message")
        async def handler(ctx):
            received.append(hasattr(ctx, "say"))

        await self.bot._handle_update(RAW_MESSAGE)
        assert received == [True]

    @pytest.mark.asyncio
    async def test_alias_not_applied_when_none_registered(self):
        received = []

        @self.bot.on("message")
        async def handler(ctx):
            received.append(hasattr(ctx, "say"))

        await self.bot._handle_update(RAW_MESSAGE)
        assert received == [False]

    @pytest.mark.asyncio
    async def test_alias_functional_in_handler(self):
        self.bot.alias("say", "reply")
        calls = []

        @self.bot.on("message")
        async def handler(ctx):
            calls.append(ctx.say == ctx.reply)

        await self.bot._handle_update(RAW_MESSAGE)
        assert calls == [True]
