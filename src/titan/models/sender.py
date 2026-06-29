"""
models.sender

تمثيل مبسط لصاحب الرسالة.

هذا الكائن يوفر واجهة سهلة للتعامل مع بيانات المستخدم
بدلاً من الوصول المباشر إلى JSON القادم من Telegram.
"""

from __future__ import annotations

from typing import Any


class Sender:
    """
    تمثيل مبسط لمستخدم Telegram.

    الهدف:
    إزالة التعقيد من بنية المستخدم الخام
    وتحويلها إلى واجهة واضحة وسهلة الاستخدام.
    """

    def __init__(self, raw: dict[str, Any] | None) -> None:
        self.raw = raw or {}

    # -------------------------
    # User data
    # -------------------------

    @property
    def id(self) -> int | None:
        return self.raw.get("id")

    @property
    def username(self) -> str | None:
        return self.raw.get("username")

    @property
    def first_name(self) -> str | None:
        return self.raw.get("first_name")

    @property
    def last_name(self) -> str | None:
        return self.raw.get("last_name")

    @property
    def is_bot(self) -> bool:
        return self.raw.get("is_bot", False)

    # -------------------------
    # Export
    # -------------------------

    def to_dict(self) -> dict[str, Any]:
        return self.raw