"""
titan.links.identity

نموذج بيانات هوية الرسالة.

TitanMessageIdentity يحتفظ بالربط الأساسي بين هوية Titan
ومعرف Telegram الخام. هذا الحد الأدنى الكافي لـ Identity Layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TitanMessageIdentity:
    """
    الهوية الأساسية لرسالة أرسلها البوت.

    تُخزَّن تلقائياً عند كل إرسال ناجح عبر ctx.reply() أو ctx.send().
    لا تحتوي على نص الرسالة أو metadata إضافية — هذه تنتمي لـ Archive Layer.

    قاعدة الحجز التاريخي:
        titan_id لرسالة محذوفة → deleted=True، لكن titan_id لا يُعاد تخصيصه أبداً.
        الهوية تصف لحظة وجود — الرسالة كانت، وهذه الحقيقة لا تُمحى.

    الحقول:
        titan_id:            المعرف الفريد التسلسلي — المفتاح
        bot_username:        اسم البوت بدون @ (مثال: "MyBot")
        telegram_message_id: معرف Telegram للرسالة داخل الشات
        chat_id:             معرف الشات
        deleted:             هل حُذفت الرسالة من Telegram؟
    """

    titan_id: int
    bot_username: str
    telegram_message_id: int
    chat_id: int
    deleted: bool = field(default=False)
