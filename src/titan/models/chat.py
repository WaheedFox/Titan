"""
models.chat

تمثيل مبسط لشات Telegram.

هذا الكائن يوفر واجهة سهلة للتعامل مع بيانات الشات
بدلاً من الوصول المباشر إلى JSON القادم من Telegram.
"""

from __future__ import annotations

from typing import Any


class Chat:
    """
    تمثيل مبسط لشات Telegram.

    الهدف:
    إزالة التعقيد من بنية الشات الخام
    وتحويلها إلى واجهة واضحة وسهلة الاستخدام.
    """

    def __init__(self, raw: dict[str, Any] | None) -> None:
        self.raw = raw or {}

    # -------------------------
    # Chat data
    # -------------------------

    @property
    def id(self) -> int | None:
        return self.raw.get("id")

    @property
    def type(self) -> str | None:
        return self.raw.get("type")

    @property
    def title(self) -> str | None:
        return self.raw.get("title")

    @property
    def username(self) -> str | None:
        return self.raw.get("username")

    # -------------------------
    # Helpers
    # -------------------------

    def is_group(self) -> bool:
        return self.type in ("group", "supergroup")

    def is_private(self) -> bool:
        return self.type == "private"

    # -------------------------
    # Export
    # -------------------------

    def to_dict(self) -> dict[str, Any]:
        return self.raw