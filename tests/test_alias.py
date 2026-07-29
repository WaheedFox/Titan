import pytest
from unittest.mock import AsyncMock, MagicMock
from titan.extras.alias import AliasMap
from titan.extras import AliasMap as ExtrasAliasMap
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

    def test_register_alias_clashing_with_ctx_property_raises(self):
        """alias يتعارض مع property موجودة في Context → TitanError فوري."""
        am = AliasMap()
        with pytest.raises(TitanError, match=r"already an attribute of Context"):
            am.register("text", "reply")  # ctx.text هي property — تعارض

    def test_register_alias_clashing_with_ctx_method_raises(self):
        """alias يتعارض مع method موجودة في Context → TitanError."""
        am = AliasMap()
        with pytest.raises(TitanError, match=r"already an attribute of Context"):
            am.register("reply", "send")  # ctx.reply موجودة

    def test_register_alias_clashing_with_ctx_method_error_message(self):
        """رسالة الخطأ تذكر الاسم المتعارض."""
        am = AliasMap()
        with pytest.raises(TitanError, match=r"'send'"):
            am.register("send", "reply")

    def test_register_unique_alias_still_works(self):
        """alias لا يتعارض مع أي attribute في Context — يُسجَّل بنجاح."""
        am = AliasMap()
        am.register("say", "reply")
        assert am._map["say"] == "reply"

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


class TestAliasAsMiddleware:
    """AliasMap.as_middleware() — opt-in wiring via standard middleware."""

    def setup_method(self):
        self.bot = Titan("fake-token")
        self.bot._api = MagicMock()
        self.bot._api.send_message = AsyncMock(return_value={"ok": True})

    def test_extras_alias_map_is_same_class(self):
        assert ExtrasAliasMap is AliasMap

    def test_as_middleware_exists(self):
        aliases = AliasMap()
        assert callable(aliases.as_middleware())

    def test_register_via_extras(self):
        aliases = ExtrasAliasMap()
        aliases.register("say", "reply")
        assert aliases._map["say"] == "reply"

    def test_invalid_target_raises(self):
        aliases = AliasMap()
        with pytest.raises(TitanError, match=r"does not exist in Context"):
            aliases.register("foo", "does_not_exist")

    @pytest.mark.asyncio
    async def test_alias_available_in_handler_via_middleware(self):
        aliases = AliasMap()
        aliases.register("say", "reply")
        self.bot.middleware(aliases.as_middleware())
        received = []

        @self.bot.on("message")
        async def handler(ctx):
            received.append(hasattr(ctx, "say"))

        await self.bot._handle_update(RAW_MESSAGE)
        assert received == [True]

    @pytest.mark.asyncio
    async def test_alias_not_applied_without_middleware(self):
        """Without middleware registration, no alias is ever applied."""
        aliases = AliasMap()
        aliases.register("say", "reply")
        received = []

        @self.bot.on("message")
        async def handler(ctx):
            received.append(hasattr(ctx, "say"))

        await self.bot._handle_update(RAW_MESSAGE)
        assert received == [False]

    @pytest.mark.asyncio
    async def test_alias_functional_in_handler(self):
        aliases = AliasMap()
        aliases.register("say", "reply")
        self.bot.middleware(aliases.as_middleware())
        calls = []

        @self.bot.on("message")
        async def handler(ctx):
            calls.append(ctx.say == ctx.reply)

        await self.bot._handle_update(RAW_MESSAGE)
        assert calls == [True]


class TestCoreHasNoAlias:
    """Core Titan must carry zero alias machinery."""

    def test_plain_titan_has_no_alias_method(self):
        bot = Titan("fake-token")
        assert not hasattr(bot, "alias"), "Core Titan must not expose alias()"

    def test_plain_titan_has_no_aliases_attr(self):
        bot = Titan("fake-token")
        assert not hasattr(bot, "aliases") and not hasattr(bot, "_aliases"), \
            "Core Titan must not carry AliasMap"
