from unittest.mock import AsyncMock

import pytest

from titan.telegram import Telegram, TelegramError


@pytest.mark.asyncio
async def test_send_rich_message_exact_payload():
    api = Telegram("token")
    api.request = AsyncMock(return_value={"ok": True})

    await api._send_rich_message(
        chat_id=200,
        rich_message={"html": "<b>Hello</b>"},
        reply_markup={"inline_keyboard": []},
        reply_to_message_id=10,
    )

    api.request.assert_awaited_once_with(
        "sendRichMessage",
        {
            "chat_id": 200,
            "rich_message": {"html": "<b>Hello</b>"},
            "reply_parameters": {"message_id": 10},
            "reply_markup": {"inline_keyboard": []},
        },
    )


@pytest.mark.asyncio
async def test_send_rich_message_preserves_markdown_mode():
    api = Telegram("token")
    api.request = AsyncMock(return_value={"ok": True})

    await api._send_rich_message(
        chat_id=200,
        rich_message={"markdown": "**Hello**"},
    )

    api.request.assert_awaited_once_with(
        "sendRichMessage",
        {
            "chat_id": 200,
            "rich_message": {"markdown": "**Hello**"},
        },
    )


@pytest.mark.asyncio
async def test_edit_rich_message_exact_payload():
    api = Telegram("token")
    api.request = AsyncMock(return_value={"ok": True})

    await api._edit_rich_message(
        chat_id=200,
        message_id=30,
        rich_message={"blocks": [{"type": "paragraph", "text": "Updated"}]},
        reply_markup={"inline_keyboard": []},
    )

    api.request.assert_awaited_once_with(
        "editMessageText",
        {
            "chat_id": 200,
            "message_id": 30,
            "rich_message": {
                "blocks": [{"type": "paragraph", "text": "Updated"}]
            },
            "reply_markup": {"inline_keyboard": []},
        },
    )


@pytest.mark.asyncio
async def test_rich_transport_propagates_telegram_error():
    api = Telegram("token")
    api.request = AsyncMock(side_effect=TelegramError("telegram rejected rich content"))

    with pytest.raises(TelegramError, match="telegram rejected"):
        await api._send_rich_message(
            chat_id=200,
            rich_message={"markdown": "**Hello**"},
        )


@pytest.mark.asyncio
async def test_plain_text_payload_remains_unchanged():
    api = Telegram("token")
    api.request = AsyncMock(return_value={"ok": True})

    await api.send_message(
        chat_id=200,
        text="Hello",
        parse_mode="HTML",
        reply_markup={"inline_keyboard": []},
        reply_to_message_id=10,
    )

    api.request.assert_awaited_once_with(
        "sendMessage",
        {
            "chat_id": 200,
            "text": "Hello",
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": []},
            "reply_parameters": {"message_id": 10},
        },
    )