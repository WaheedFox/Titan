"""
اختبارات /link command handler.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from titan.links.handler import handle_link_command
from titan.links.manager import LinksManager
from titan.links.address import TitanMessageAddress
from titan.links.store import SqliteMessageStore
from titan.update import Update
from titan.ctx import Context


def make_ctx_with_reply(
    reply_to_message_id: int | None,
    reply_to_is_bot: bool = True,
    chat_id: int = 100,
) -> tuple[Context, MagicMock]:
    """
    بناء ctx يحاكي رسالة /link مع رد على رسالة.
    """
    raw: dict = {
        "update_id": 1,
        "message": {
            "message_id": 200,
            "text": "/link",
            "from": {"id": 99, "username": "user"},
            "chat": {"id": chat_id, "type": "private"},
        },
    }

    if reply_to_message_id is not None:
        raw["message"]["reply_to_message"] = {
            "message_id": reply_to_message_id,
            "from": {
                "id": 1,
                "is_bot": reply_to_is_bot,
                "username": "MyBot",
            },
        }

    api = MagicMock()
    api.send_message = AsyncMock(return_value={"ok": True, "result": {"message_id": 999}})
    api._me = {"id": 1, "username": "MyBot"}

    update = Update(raw)
    ctx = Context(update, api)
    return ctx, api


@pytest.fixture
def links():
    m = LinksManager()
    m._sqlite_store = SqliteMessageStore(":memory:")
    m._store = m._sqlite_store
    return m


class TestHandleLinkCommand:
    @pytest.mark.asyncio
    async def test_no_reply_sends_instructions(self, links):
        ctx, api = make_ctx_with_reply(reply_to_message_id=None)
        await handle_link_command(ctx, links)
        api.send_message.assert_called_once()
        sent_text = api.send_message.call_args.kwargs.get("text", "")
        assert "رد" in sent_text or "link" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_reply_to_user_message_sends_error(self, links):
        ctx, api = make_ctx_with_reply(
            reply_to_message_id=50,
            reply_to_is_bot=False,
        )
        await handle_link_command(ctx, links)
        api.send_message.assert_called_once()
        sent_text = api.send_message.call_args.kwargs.get("text", "")
        # يجب أن ينص على أن /link يعمل فقط مع رسائل البوت
        assert "بوت" in sent_text or "bot" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_reply_to_unregistered_bot_message(self, links):
        """رسالة البوت القديمة لا تملك هوية Titan."""
        ctx, api = make_ctx_with_reply(
            reply_to_message_id=482,
            reply_to_is_bot=True,
        )
        await handle_link_command(ctx, links)
        api.send_message.assert_called_once()
        sent_text = api.send_message.call_args.kwargs.get("text", "")
        assert "قبل" in sent_text or "message links" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_reply_to_registered_bot_message(self, links):
        """رسالة البوت المسجّلة تُعيد TitanMessageAddress."""
        # نسجّل الرسالة أولاً
        await links.register_sent_message(
            chat_id=100,
            telegram_message_id=482,
            bot_username="MyBot",
        )

        ctx, api = make_ctx_with_reply(
            reply_to_message_id=482,
            reply_to_is_bot=True,
            chat_id=100,
        )
        await handle_link_command(ctx, links)
        api.send_message.assert_called_once()
        sent_text = api.send_message.call_args.kwargs.get("text", "")
        assert "https://t.me/MyBot/1" == sent_text

    @pytest.mark.asyncio
    async def test_store_failure_sends_error_message(self, links):
        """فشل الـ store لا يكسر البوت — يُعيد رسالة خطأ."""
        links._store.get_by_telegram_id = AsyncMock(side_effect=RuntimeError("db error"))

        ctx, api = make_ctx_with_reply(
            reply_to_message_id=50,
            reply_to_is_bot=True,
        )
        await handle_link_command(ctx, links)
        api.send_message.assert_called_once()
        sent_text = api.send_message.call_args.kwargs.get("text", "")
        assert "خطأ" in sent_text
