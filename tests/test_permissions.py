import pytest
from unittest.mock import AsyncMock, MagicMock
from titan.ctx import Context
from titan.update import Update
from titan.models.permissions import ChatPermissions
from titan.errors import TitanError


def make_ctx(raw_update: dict, api=None) -> Context:
    if api is None:
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        api.get_me = AsyncMock(return_value={"id": 1, "username": "mybot"})
        api.get_chat_member = AsyncMock(return_value={"ok": True, "result": {}})
    update = Update(raw_update)
    return Context(update, api)


RAW_MESSAGE = {
    "update_id": 1,
    "message": {
        "message_id": 10,
        "text": "hello",
        "from": {"id": 99, "username": "ali", "first_name": "Ali"},
        "chat": {"id": 200, "type": "group"},
    },
}

RAW_NO_CHAT = {
    "update_id": 2,
    "message": {"message_id": 5},
}


class TestCtxPermissionsDefault:
    def test_permissions_none_by_default(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.permissions is None


class TestFetchPermissions:
    @pytest.mark.asyncio
    async def test_returns_chat_permissions(self):
        api = MagicMock()
        api.get_me = AsyncMock(return_value={"id": 1})
        api.get_chat_member = AsyncMock(return_value={
            "ok": True,
            "result": {"can_delete_messages": True},
        })
        ctx = make_ctx(RAW_MESSAGE, api=api)
        result = await ctx.fetch_permissions()
        assert isinstance(result, ChatPermissions)

    @pytest.mark.asyncio
    async def test_populates_ctx_permissions(self):
        api = MagicMock()
        api.get_me = AsyncMock(return_value={"id": 1})
        api.get_chat_member = AsyncMock(return_value={
            "ok": True,
            "result": {"can_delete_messages": True, "can_pin_messages": True},
        })
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.fetch_permissions()
        assert ctx.permissions is not None
        assert ctx.permissions.can_delete_messages is True
        assert ctx.permissions.can_pin_messages is True

    @pytest.mark.asyncio
    async def test_calls_get_me_for_bot_id(self):
        api = MagicMock()
        api.get_me = AsyncMock(return_value={"id": 42})
        api.get_chat_member = AsyncMock(return_value={"ok": True, "result": {}})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.fetch_permissions()
        api.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_get_chat_member_with_correct_args(self):
        api = MagicMock()
        api.get_me = AsyncMock(return_value={"id": 42})
        api.get_chat_member = AsyncMock(return_value={"ok": True, "result": {}})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.fetch_permissions()
        api.get_chat_member.assert_called_once_with(chat_id=200, user_id=42)

    @pytest.mark.asyncio
    async def test_raises_on_missing_chat_id(self):
        ctx = make_ctx(RAW_NO_CHAT)
        with pytest.raises(TitanError, match="chat_id"):
            await ctx.fetch_permissions()

    @pytest.mark.asyncio
    async def test_propagates_telegram_error_from_get_chat_member(self):
        from titan.telegram import TelegramError
        api = MagicMock()
        api.get_me = AsyncMock(return_value={"id": 1})
        api.get_chat_member = AsyncMock(side_effect=TelegramError("forbidden"))
        ctx = make_ctx(RAW_MESSAGE, api=api)
        with pytest.raises(TelegramError):
            await ctx.fetch_permissions()

    @pytest.mark.asyncio
    async def test_propagates_telegram_error_from_get_me(self):
        from titan.telegram import TelegramError
        api = MagicMock()
        api.get_me = AsyncMock(side_effect=TelegramError("unauthorized"))
        api.get_chat_member = AsyncMock(return_value={"ok": True, "result": {}})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        with pytest.raises(TelegramError):
            await ctx.fetch_permissions()

    @pytest.mark.asyncio
    async def test_return_value_is_same_instance_as_ctx_permissions(self):
        api = MagicMock()
        api.get_me = AsyncMock(return_value={"id": 1})
        api.get_chat_member = AsyncMock(return_value={"ok": True, "result": {}})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        result = await ctx.fetch_permissions()
        assert result is ctx.permissions

    @pytest.mark.asyncio
    async def test_permissions_reflect_api_response(self):
        api = MagicMock()
        api.get_me = AsyncMock(return_value={"id": 1})
        api.get_chat_member = AsyncMock(return_value={
            "ok": True,
            "result": {
                "can_manage_chat": True,
                "can_delete_messages": True,
                "can_restrict_members": True,
                "can_promote_members": False,
                "can_change_info": True,
                "can_invite_users": True,
                "can_pin_messages": False,
            },
        })
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.fetch_permissions()
        p = ctx.permissions
        assert p.can_manage_chat is True
        assert p.can_delete_messages is True
        assert p.can_restrict_members is True
        assert p.can_promote_members is False
        assert p.can_change_info is True
        assert p.can_invite_users is True
        assert p.can_pin_messages is False


class TestChatPermissionsModel:
    def test_all_fields_default_to_false(self):
        p = ChatPermissions({})
        assert p.can_manage_chat is False
        assert p.can_delete_messages is False
        assert p.can_manage_video_chats is False
        assert p.can_restrict_members is False
        assert p.can_promote_members is False
        assert p.can_change_info is False
        assert p.can_invite_users is False
        assert p.can_pin_messages is False
        assert p.can_manage_topics is False
        assert p.can_post_messages is False
        assert p.can_edit_messages is False

    def test_can_post_messages_channel_specific(self):
        p = ChatPermissions({"can_post_messages": True})
        assert p.can_post_messages is True

    def test_can_edit_messages_channel_specific(self):
        p = ChatPermissions({"can_edit_messages": True})
        assert p.can_edit_messages is True

    def test_can_manage_topics_forum_specific(self):
        p = ChatPermissions({"can_manage_topics": True})
        assert p.can_manage_topics is True

    def test_raw_preserved(self):
        raw = {"can_delete_messages": True, "extra": "data"}
        p = ChatPermissions(raw)
        assert p.raw is raw

    def test_to_dict_returns_raw(self):
        raw = {"can_delete_messages": True}
        p = ChatPermissions(raw)
        assert p.to_dict() == raw
