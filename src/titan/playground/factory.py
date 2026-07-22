"""
titan.playground.factory

مصنع سيناريوهات — يبني updates متوافقة مع شكل Telegram الحقيقي من
مدخلات مبسطة، للاستخدام مع Titan.feed_update().

v1: fake_message(), fake_command(), fake_callback() فقط.
لا مُصنِّع update عام قابل للتخصيص الكامل — راجع
docs/decisions/011-playground.md — القرار #4.
"""

from __future__ import annotations

from typing import Any

_next_update_id = 1


def _update_id() -> int:
    global _next_update_id
    update_id = _next_update_id
    _next_update_id += 1
    return update_id


def fake_message(
    text: str,
    chat_id: int = 1,
    user_id: int = 1,
    message_id: int = 1,
) -> dict[str, Any]:
    """
    يبني update متوافق مع رسالة نصية عادية.

    مثال:
        await bot.feed_update(fake_message("مرحباً"))
    """
    return {
        "update_id": _update_id(),
        "message": {
            "message_id": message_id,
            "date": 0,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "Playground"},
            "text": text,
        },
    }


def fake_command(
    name: str,
    chat_id: int = 1,
    user_id: int = 1,
    message_id: int = 1,
) -> dict[str, Any]:
    """
    يبني update متوافق مع أمر (مثل /start).

    مثال:
        await bot.feed_update(fake_command("start"))
    """
    return fake_message(
        text=f"/{name}",
        chat_id=chat_id,
        user_id=user_id,
        message_id=message_id,
    )


def fake_callback(
    data: str,
    chat_id: int = 1,
    user_id: int = 1,
    message_id: int = 1,
    callback_id: str = "playground-callback",
) -> dict[str, Any]:
    """
    يبني update متوافق مع ضغط زر callback.

    مثال:
        await bot.feed_update(fake_callback("yes"))
    """
    return {
        "update_id": _update_id(),
        "callback_query": {
            "id": callback_id,
            "data": data,
            "from": {"id": user_id, "is_bot": False, "first_name": "Playground"},
            "message": {
                "message_id": message_id,
                "date": 0,
                "chat": {"id": chat_id, "type": "private"},
            },
        },
    }
