import pytest
from unittest.mock import AsyncMock, MagicMock

from titan.ctx import Context, TypingAction
from titan.update import Update


RAW_MESSAGE = {
    "update_id": 1,
    "message": {
        "message_id": 10,
        "chat": {"id": 100, "type": "private"},
        "from": {"id": 42, "first_name": "Ali"},
        "text": "hello",
    },
}

RAW_NO_CHAT = {
    "update_id": 2,
}


def make_ctx(raw_update: dict, api=None) -> Context:
    if api is None:
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        api.send_chat_action = AsyncMock(return_value={"ok": True})
    update = Update(raw_update)
    return Context(update, api)


class TestTypingActionConstruction:
    def test_typing_returns_typing_action(self):
        ctx = make_ctx(RAW_MESSAGE)
        result = ctx.typing()
        assert isinstance(result, TypingAction)

    def test_typing_called_twice_returns_distinct_instances(self):
        ctx = make_ctx(RAW_MESSAGE)
        assert ctx.typing() is not ctx.typing()


class TestTypingActionBehavior:
    @pytest.mark.asyncio
    async def test_aenter_sends_typing_action(self):
        api = MagicMock()
        api.send_chat_action = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api=api)

        async with ctx.typing():
            pass

        api.send_chat_action.assert_called_once_with(100, "typing")

    @pytest.mark.asyncio
    async def test_aenter_returns_typing_action_instance(self):
        ctx = make_ctx(RAW_MESSAGE)
        action = ctx.typing()
        result = await action.__aenter__()
        await action.__aexit__(None, None, None)
        assert result is action

    @pytest.mark.asyncio
    async def test_aexit_does_not_make_api_calls(self):
        api = MagicMock()
        api.send_chat_action = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api=api)

        async with ctx.typing():
            pass

        assert api.send_chat_action.call_count == 1

    @pytest.mark.asyncio
    async def test_exceptions_inside_block_propagate(self):
        ctx = make_ctx(RAW_MESSAGE)

        with pytest.raises(ValueError, match="task failed"):
            async with ctx.typing():
                raise ValueError("task failed")

    @pytest.mark.asyncio
    async def test_no_api_call_when_chat_id_is_none(self):
        api = MagicMock()
        api.send_chat_action = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_NO_CHAT, api=api)

        async with ctx.typing():
            pass

        api.send_chat_action.assert_not_called()

    @pytest.mark.asyncio
    async def test_code_inside_block_executes(self):
        ctx = make_ctx(RAW_MESSAGE)
        executed = []

        async with ctx.typing():
            executed.append(True)

        assert executed == [True]

    @pytest.mark.asyncio
    async def test_typing_action_sends_correct_action_string(self):
        api = MagicMock()
        api.send_chat_action = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api=api)

        async with ctx.typing():
            pass

        _, action_arg = api.send_chat_action.call_args[0]
        assert action_arg == "typing"
