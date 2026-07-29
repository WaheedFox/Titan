"""
titan.links.address

وحدة الهوية الأساسية في Message Links Protocol.

TitanMessageAddress يمثل هوية رسالة كاملة — لا يكفي titan_id وحده
لأن الهوية مرتبطة بالبوت صاحب الرسالة.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TitanMessageAddress:
    """
    العنوان الكامل لرسالة Titan.

    يجمع بين اسم البوت ومعرف الرسالة ليشكّل هوية قابلة للمشاركة
    بين المستخدمين والأدوات.

    الصيغة النصية:
        https://t.me/{bot_username}/{titan_id}

    هذا Titan Message Address — بروتوكول هوية فوق Telegram.
    Telegram لا يحتاج أن يفهمه.
    من يفهمه: Titan نفسه، Architect AI، أدوات المطور.

    الخصائص:
        bot_username:  اسم البوت بدون @  (مثال: "MyBot")
        titan_id:      معرف الرسالة التسلسلي عند هذا البوت  (مثال: 482)
    """

    bot_username: str
    titan_id: int

    def __str__(self) -> str:
        return f"https://t.me/{self.bot_username}/{self.titan_id}"

    def __repr__(self) -> str:
        return (
            f"TitanMessageAddress("
            f"bot_username={self.bot_username!r}, "
            f"titan_id={self.titan_id})"
        )
