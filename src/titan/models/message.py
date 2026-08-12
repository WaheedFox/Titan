"""
models.message

تمثيل مبسط لرسالة Telegram.

data-only object — لا يحتوي على أي عمليات أو API calls.
جميع العمليات (reply, send, delete, edit) تتم عبر ctx.
"""

from __future__ import annotations

from typing import Any


class Message:
    """
    تمثيل مبسط لرسالة Telegram.

    يحتوي على بيانات الرسالة فقط.
    للتفاعل مع الرسالة استخدم ctx مباشرة.
    """

    def __init__(self, raw: dict[str, Any] | None) -> None:
        self.raw = raw or {}

    # -------------------------
    # Message data
    # -------------------------

    @property
    def id(self) -> int | None:
        return self.raw.get("message_id")

    @property
    def text(self) -> str | None:
        return self.raw.get("text")

    @property
    def chat_id(self) -> int | None:
        chat = self.raw.get("chat")
        return chat.get("id") if chat else None

    # -------------------------
    # Export
    # -------------------------

    def to_dict(self) -> dict[str, Any]:
        return self.raw
