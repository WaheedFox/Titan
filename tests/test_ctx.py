import pytest
from unittest.mock import AsyncMock, MagicMock
from titan.ctx import Context
from titan.update import Update
from titan.errors import TitanError


def make_ctx(raw_update: dict, api=None) -> Context:
    if api is None:
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        api.edit_message_text = AsyncMock(return_value={"ok": True})
        api.delete_message = AsyncMock(return_value={"ok": True})
        api.ban_user = AsyncMock(return_value={"ok": True})
        api.leave_chat = AsyncMock(return_value={"ok": True})
        api.get_chat_member = AsyncMock(return_value={"ok": True, "result": {}})
        api.get_me = AsyncMock(return_value={"id": 1, "username": "mybot"})
        api.answer_callback_query = AsyncMock(return_value={"ok": True})
    update = Update(raw_update)
    return Context(update, api)


RAW_MESSAGE = {
    "update_id": 1,
    "message": {
        "message_id": 10,
        "text": "hello",
        "from": {"id": 99, "username": "ali", "first_name": "Ali"},
        "chat": {"id": 200, "type": "private"},
    },
}

RAW_CALLBACK = {
    "update_id": 2,
    "callback_query": {
        "id": "cq1",
        "data": "yes",
        "from": {"id": 55, "username": "bob"},
        "message": {
            "message_id": 30,
            "chat": {"id": 400, "type": "group"},
        },
    },
}

RAW_NEW_MEMBER = {
    "update_id": 3,
    "message": {
        "message_id": 40,
        "chat": {"id": 500, "type": "supergroup"},
        "new_chat_members": [{"id": 77, "first_name": "Zaid"}],
    },
}

RAW_LEFT_MEMBER = {
    "update_id": 4,
    "message": {
        "message_id": 50,
        "chat": {"id": 500, "type": "supergroup"},
        "left_chat_member": {"id": 88, "first_name": "Sara"},
    },
}


class TestContextRawContract:
    def test_ctx_raw_equals_full_update(self):
        """§3 CONTRACT: ctx.raw exposes raw JSON at the update level."""
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.raw == RAW_MESSAGE

    def test_ctx_raw_present_on_all_update_types(self):
        """§3 CONTRACT: ctx.raw is guaranteed to exist."""
        for raw in (RAW_MESSAGE, RAW_CALLBACK, RAW_NEW_MEMBER, RAW_LEFT_MEMBER):
            ctx = make_ctx(raw)
            assert hasattr(ctx, "raw")
            assert ctx.raw == raw

    def test_model_raw_present_on_message(self):
        """§3 CONTRACT: model.raw guaranteed on Message."""
        ctx = make_ctx(RAW_MESSAGE)
        assert hasattr(ctx.message, "raw")
        assert isinstance(ctx.message.raw, dict)

    def test_model_raw_present_on_sender(self):
        """§3 CONTRACT: model.raw guaranteed on Sender."""
        ctx = make_ctx(RAW_MESSAGE)
        assert hasattr(ctx.sender, "raw")
        assert isinstance(ctx.sender.raw, dict)

    def test_model_raw_present_on_chat(self):
        """§3 CONTRACT: model.raw guaranteed on Chat."""
        ctx = make_ctx(RAW_MESSAGE)
        assert hasattr(ctx.chat, "raw")
        assert isinstance(ctx.chat.raw, dict)

    def test_model_to_dict_present_on_message(self):
        """§3 CONTRACT: model.to_dict() guaranteed on Message."""
        ctx = make_ctx(RAW_MESSAGE)
        assert callable(ctx.message.to_dict)
        assert isinstance(ctx.message.to_dict(), dict)

    def test_model_to_dict_present_on_sender(self):
        """§3 CONTRACT: model.to_dict() guaranteed on Sender."""
        ctx = make_ctx(RAW_MESSAGE)
        assert callable(ctx.sender.to_dict)
        assert isinstance(ctx.sender.to_dict(), dict)

    def test_model_to_dict_present_on_chat(self):
        """§3 CONTRACT: model.to_dict() guaranteed on Chat."""
        ctx = make_ctx(RAW_MESSAGE)
        assert callable(ctx.chat.to_dict)
        assert isinstance(ctx.chat.to_dict(), dict)


class TestContextProperties:
    def test_text(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.text == "hello"

    def test_user_id(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.user_id == 99

    def test_chat_id(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.chat_id == 200

    def test_username(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.username == "ali"

    def test_message_id(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.message_id == 10

    def test_permissions_default_is_none(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.permissions is None

    def test_sender_model(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.sender.id == 99
        assert ctx.sender.username == "ali"

    def test_chat_model(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.chat.id == 200
        assert ctx.chat.type == "private"

    def test_message_model(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.message.id == 10
        assert ctx.message.text == "hello"


class TestContextCallbackProperties:
    def test_callback_data(self):
        ctx = make_ctx(RAW_CALLBACK)
        assert ctx.callback_data == "yes"

    def test_callback_id(self):
        ctx = make_ctx(RAW_CALLBACK)
        assert ctx.callback_id == "cq1"

    def test_callback_data_none_on_message(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.callback_data is None

    def test_callback_id_none_on_message(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.callback_id is None


class TestContextMemberProperties:
    def test_new_members(self):
        from titan.models.sender import Sender
        ctx = make_ctx(RAW_NEW_MEMBER)
        members = ctx.new_members
        assert members is not None
        assert len(members) == 1
        assert isinstance(members[0], Sender)
        assert members[0].id == 77
        assert members[0].first_name == "Zaid"

    def test_left_member(self):
        from titan.models.sender import Sender
        ctx = make_ctx(RAW_LEFT_MEMBER)
        member = ctx.left_member
        assert isinstance(member, Sender)
        assert member.id == 88
        assert member.first_name == "Sara"

    def test_new_members_none_on_plain_message(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.new_members is None

    def test_left_member_none_on_plain_message(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.left_member is None


class TestContextActions:
    @pytest.mark.asyncio
    async def test_reply_calls_api(self):
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.reply("hi")
        api.send_message.assert_called_once_with(
            chat_id=200,
            text="hi",
            parse_mode=None,
            reply_markup=None,
            reply_to_message_id=10,
        )

    @pytest.mark.asyncio
    async def test_send_calls_api_without_reply_to(self):
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.send("hey")
        api.send_message.assert_called_once_with(
            chat_id=200,
            text="hey",
            parse_mode=None,
            reply_markup=None,
        )

    @pytest.mark.asyncio
    async def test_edit_calls_api_in_callback(self):
        api = MagicMock()
        api.edit_message_text = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_CALLBACK, api=api)
        await ctx.edit("new text")
        api.edit_message_text.assert_called_once_with(
            chat_id=400,
            message_id=30,
            text="new text",
            parse_mode=None,
            reply_markup=None,
        )

    @pytest.mark.asyncio
    async def test_edit_raises_outside_callback(self):
        ctx = make_ctx(RAW_MESSAGE)
        with pytest.raises(TitanError, match=r"ctx\.edit\(\) requires an active callback_query context"):
            await ctx.edit("oops")

    @pytest.mark.asyncio
    async def test_delete_message_calls_api(self):
        api = MagicMock()
        api.delete_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.delete_message()
        api.delete_message.assert_called_once_with(chat_id=200, message_id=10)

    @pytest.mark.asyncio
    async def test_ban_user_calls_api(self):
        api = MagicMock()
        api.ban_user = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.ban_user()
        api.ban_user.assert_called_once_with(chat_id=200, user_id=99)

    @pytest.mark.asyncio
    async def test_ban_user_with_explicit_id(self):
        api = MagicMock()
        api.ban_user = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.ban_user(user_id=42)
        api.ban_user.assert_called_once_with(chat_id=200, user_id=42)

    @pytest.mark.asyncio
    async def test_leave_calls_api(self):
        api = MagicMock()
        api.leave_chat = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api=api)
        await ctx.leave()
        api.leave_chat.assert_called_once_with(chat_id=200)

    @pytest.mark.asyncio
    async def test_answer_callback_calls_api(self):
        api = MagicMock()
        api.answer_callback_query = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_CALLBACK, api=api)
        await ctx.answer_callback()
        api.answer_callback_query.assert_called_once_with(
            callback_query_id="cq1",
            text=None,
            show_alert=False,
        )

    @pytest.mark.asyncio
    async def test_answer_callback_raises_outside_callback(self):
        ctx = make_ctx(RAW_MESSAGE)
        with pytest.raises(TitanError, match=r"ctx\.answer_callback\(\) requires an active callback_query context"):
            await ctx.answer_callback()

class TestContextNullSafety:
    @pytest.mark.asyncio
    async def test_reply_returns_none_when_no_chat_id(self):
        raw = {"update_id": 1, "message": {"message_id": 1}}
        ctx = make_ctx(raw)
        result = await ctx.reply("hi")
        assert result is None

    @pytest.mark.asyncio
    async def test_send_returns_none_when_no_chat_id(self):
        raw = {"update_id": 1, "message": {"message_id": 1}}
        ctx = make_ctx(raw)
        result = await ctx.send("hi")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_returns_none_when_no_ids(self):
        raw = {"update_id": 1}
        ctx = make_ctx(raw)
        result = await ctx.delete_message()
        assert result is None

    @pytest.mark.asyncio
    async def test_ban_returns_none_when_no_ids(self):
        raw = {"update_id": 1}
        ctx = make_ctx(raw)
        result = await ctx.ban_user()
        assert result is None

    @pytest.mark.asyncio
    async def test_leave_returns_none_when_no_chat_id(self):
        raw = {"update_id": 1}
        ctx = make_ctx(raw)
        result = await ctx.leave()
        assert result is None

