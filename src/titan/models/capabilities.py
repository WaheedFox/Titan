"""
models.capabilities

تمثيل قدرات البوت على مستوى الحساب.

البيانات مصدرها getMe — محفوظة في الذاكرة بعد أول استدعاء.
لا تتعلق بأي update أو شات محدد.

يُكشَف هذا النموذج عبر bot.capabilities بعد تشغيل البوت.
"""

from __future__ import annotations

from typing import Any


class BotCapabilities:
    """
    قدرات البوت على مستوى الحساب، مستخرجة من استجابة getMe.

    هذه القدرات ثابتة خلال دورة حياة البوت —
    لا تتغير بتغير الشات أو المستخدم أو نوع الـ update.

    لا تُنشئ هذا الكائن مباشرةً — استخدم bot.capabilities.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    # -------------------------
    # Capabilities
    # -------------------------

    @property
    def can_join_groups(self) -> bool:
        """هل يمكن للبوت الانضمام إلى المجموعات؟"""
        return self.raw.get("can_join_groups", False)

    @property
    def can_read_all_group_messages(self) -> bool:
        """هل يقرأ البوت جميع الرسائل في المجموعات (privacy mode مُعطَّل)؟"""
        return self.raw.get("can_read_all_group_messages", False)

    @property
    def supports_inline_queries(self) -> bool:
        """هل يدعم البوت الـ inline queries؟"""
        return self.raw.get("supports_inline_queries", False)

    # -------------------------
    # Export
    # -------------------------

    def to_dict(self) -> dict[str, Any]:
        return self.raw
