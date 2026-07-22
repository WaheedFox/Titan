"""
titan.links.archive

Archive Layer — طبقة حفظ محتوى الرسائل الاختيارية.

لا تُفعَّل تلقائياً. المطور يختار تفعيلها عبر bot.links.enable_archive().

العلاقة مع Identity Layer:
    الأرشيف يعتمد على وجود هوية — لا يعكس العكس.
    رسالة بلا أرشيف: هويتها موجودة، محتواها غير محفوظ.
    رسالة ذات أرشيف: هويتها موجودة ومحتواها محفوظ.

في v1: Archive Layer تعمل مع SqliteMessageStore فقط.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TitanMessageArchive:
    """
    بيانات الأرشيف لرسالة مسجّلة في Identity Layer.

    تُخزَّن فقط عند تفعيل Archive Layer.

    الحقول:
        titan_id:  FK → TitanMessageIdentity.titan_id
        text:      نص الرسالة عند الإرسال (None للرسائل غير النصية)
        chat_type: نوع الشات — private | group | supergroup | channel | unknown
        sent_at:   وقت الإرسال بصيغة ISO 8601
    """

    titan_id: int
    text: str | None
    chat_type: str
    sent_at: str
