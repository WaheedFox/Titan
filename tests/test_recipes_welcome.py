import pytest
from unittest.mock import AsyncMock, MagicMock

from titan.ctx import Context
from titan.update import Update
from titan.recipes import Welcome


def make_ctx(raw_update: dict, api=None) -> Context:
    if api is None:
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
    update = Update(raw_update)
    return Context(update, api)


def make_new_member_update(*members: dict) -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "chat": {"id": 500, "type": "supergroup"},
            "new_chat_members": list(members),
        },
    }


HUMAN = {"id": 77, "first_name": "Zaid", "is_bot": False}
BOT = {"id": 88, "first_name": "MyBot", "is_bot": True}
NO_NAME = {"id": 99, "is_bot": False}

RAW_MESSAGE = {
    "update_id": 2,
    "message": {
        "message_id": 20,
        "text": "hello",
        "from": {"id": 1, "first_name": "Ali"},
        "chat": {"id": 300, "type": "private"},
    },
}


class TestWelcomeDefaults:
    async def test_default_message_is_used(self):
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(HUMAN), api)

        await welcome(ctx)

        call_text = api.send_message.call_args.kwargs["text"]
        assert call_text == "Welcome, Zaid!"

    async def test_custom_message_is_used(self):
        welcome = Welcome("Hello, {name}! Glad you joined.")
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(HUMAN), api)

        await welcome(ctx)

        call_text = api.send_message.call_args.kwargs["text"]
        assert call_text == "Hello, Zaid! Glad you joined."

    async def test_message_attribute_stored(self):
        welcome = Welcome("Hi, {name}!")
        assert welcome.message == "Hi, {name}!"

    async def test_default_message_attribute(self):
        welcome = Welcome()
        assert welcome.message == "Welcome, {name}!"


class TestWelcomeSingleMember:
    async def test_single_human_member_is_greeted(self):
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(HUMAN), api)

        await welcome(ctx)

        assert api.send_message.call_count == 1

    async def test_greeting_sent_to_correct_chat(self):
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(HUMAN), api)

        await welcome(ctx)

        assert api.send_message.call_args.kwargs["chat_id"] == 500

    async def test_name_appears_in_message(self):
        welcome = Welcome("Hey {name}!")
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(HUMAN), api)

        await welcome(ctx)

        call_text = api.send_message.call_args.kwargs["text"]
        assert "Zaid" in call_text


class TestWelcomeMultipleMembers:
    async def test_multiple_humans_each_greeted(self):
        member_a = {"id": 1, "first_name": "Ali", "is_bot": False}
        member_b = {"id": 2, "first_name": "Sara", "is_bot": False}
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(member_a, member_b), api)

        await welcome(ctx)

        assert api.send_message.call_count == 2

    async def test_each_member_receives_own_name(self):
        member_a = {"id": 1, "first_name": "Ali", "is_bot": False}
        member_b = {"id": 2, "first_name": "Sara", "is_bot": False}
        welcome = Welcome("Welcome, {name}!")
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(member_a, member_b), api)

        await welcome(ctx)

        texts = [call.kwargs["text"] for call in api.send_message.call_args_list]
        assert "Welcome, Ali!" in texts
        assert "Welcome, Sara!" in texts


class TestWelcomeBotFiltering:
    async def test_bot_member_is_skipped(self):
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(BOT), api)

        await welcome(ctx)

        api.send_message.assert_not_called()

    async def test_human_greeted_bot_skipped(self):
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(HUMAN, BOT), api)

        await welcome(ctx)

        assert api.send_message.call_count == 1
        call_text = api.send_message.call_args.kwargs["text"]
        assert "Zaid" in call_text

    async def test_all_bots_nothing_sent(self):
        bot_a = {"id": 1, "first_name": "BotA", "is_bot": True}
        bot_b = {"id": 2, "first_name": "BotB", "is_bot": True}
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(bot_a, bot_b), api)

        await welcome(ctx)

        api.send_message.assert_not_called()

    async def test_multiple_humans_and_bots_only_humans_greeted(self):
        member_a = {"id": 1, "first_name": "Ali", "is_bot": False}
        member_b = {"id": 2, "first_name": "BotX", "is_bot": True}
        member_c = {"id": 3, "first_name": "Sara", "is_bot": False}
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(member_a, member_b, member_c), api)

        await welcome(ctx)

        assert api.send_message.call_count == 2


class TestWelcomeFallbacks:
    async def test_missing_first_name_falls_back_to_there(self):
        welcome = Welcome("Welcome, {name}!")
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(NO_NAME), api)

        await welcome(ctx)

        call_text = api.send_message.call_args.kwargs["text"]
        assert call_text == "Welcome, there!"

    async def test_empty_first_name_falls_back_to_there(self):
        member = {"id": 1, "first_name": "", "is_bot": False}
        welcome = Welcome("Welcome, {name}!")
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(member), api)

        await welcome(ctx)

        call_text = api.send_message.call_args.kwargs["text"]
        assert call_text == "Welcome, there!"


class TestWelcomeEdgeCases:
    async def test_non_new_member_update_does_nothing(self):
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(RAW_MESSAGE, api)

        await welcome(ctx)

        api.send_message.assert_not_called()

    async def test_empty_new_members_list_does_nothing(self):
        raw = {
            "update_id": 1,
            "message": {
                "message_id": 10,
                "chat": {"id": 500, "type": "supergroup"},
                "new_chat_members": [],
            },
        }
        welcome = Welcome()
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(raw, api)

        await welcome(ctx)

        api.send_message.assert_not_called()

    async def test_recipe_is_reusable_across_updates(self):
        welcome = Welcome("Welcome, {name}!")
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})

        ctx_a = make_ctx(make_new_member_update(HUMAN), api)
        ctx_b = make_ctx(
            make_new_member_update({"id": 2, "first_name": "Sara", "is_bot": False}),
            api,
        )

        await welcome(ctx_a)
        await welcome(ctx_b)

        assert api.send_message.call_count == 2

    async def test_message_without_name_placeholder_is_valid(self):
        welcome = Welcome("A new member has joined!")
        api = MagicMock()
        api.send_message = AsyncMock(return_value={"ok": True})
        ctx = make_ctx(make_new_member_update(HUMAN), api)

        await welcome(ctx)

        call_text = api.send_message.call_args.kwargs["text"]
        assert call_text == "A new member has joined!"
