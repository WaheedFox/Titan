"""
titan.playground

مختبر Titan المعماري — بيئة تجريب لسلوك Titan الحقيقي (routing،
middleware، Inspector) دون بوت متصل فعلياً بـ Telegram.

Playground لا يضيف قدرات إلى Titan، بل يكشف قدرات Titan الموجودة
بطريقة قابلة للاستكشاف. راجع docs/decisions/011-playground.md.

غير مُصدَّرة من جذر الحزمة — الاستيراد صريح دائماً:
    from titan.playground import RecordingTelegram, fake_message

v1: RecordingTelegram + factory (fake_message/fake_command/fake_callback)
فقط. أي توسع مستقبلي (routing trace حي، مقارنة migration، ...) يُبنى
تباعاً بحسب مستهلك فعلي — لا مسبقاً.
"""

from __future__ import annotations

from titan.playground.recording import RecordingTelegram
from titan.playground.factory import fake_callback, fake_command, fake_message

__all__ = [
    "RecordingTelegram",
    "fake_message",
    "fake_command",
    "fake_callback",
]
