"""
titan.profiler._run

profile_update() — دالة القياس الرئيسية.

تعمل من خارج Core بالكامل: تُحيط bot.feed_update() بـ time.perf_counter()
وتُجمع النتائج في ProfilingSession. تستخدم RecordingTelegram لضمان
عدم إرسال أي طلب حقيقي إلى Telegram خلال القياس.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from titan.playground import RecordingTelegram
from titan.profiler._models import ProfileEntry, ProfilingSession

if TYPE_CHECKING:
    from titan import Titan


def _infer_event_type(update: dict[str, Any]) -> str:
    """
    يستنتج event_type من بنية الـ update dict.

    الأولوية:
        1. callback_query          → "callback/{data}"
        2. message.text يبدأ بـ / → "command/{name}"
        3. channel_post            → "channel"
        4. new_chat_members        → "new_member"
        5. left_chat_member        → "left_member"
        6. غير ذلك                → "message"
    """
    if "callback_query" in update:
        data = update["callback_query"].get("data", "")
        return f"callback/{data}" if data else "callback"

    if "channel_post" in update:
        return "channel"

    message = update.get("message", {})

    if message.get("new_chat_members"):
        return "new_member"

    if message.get("left_chat_member"):
        return "left_member"

    text: str = message.get("text", "")
    if text.startswith("/"):
        name = text[1:].split()[0].split("@")[0]
        return f"command/{name}"

    return "message"


async def profile_update(
    bot: "Titan",
    update: dict[str, Any],
    n: int = 1,
) -> ProfilingSession:
    """
    يُشغّل update عبر bot.feed_update() n مرة ويقيس wall time لكل تشغيل.

    يُحقن RecordingTelegram تلقائياً لمنع أي اتصال حقيقي بـ Telegram.
    يُستعاد الـ API الأصلي بعد انتهاء القياس في جميع الأحوال.

    مثال:
        from titan.profiler import profile_update
        from titan.playground import fake_command

        session = await profile_update(bot, fake_command("start"), n=100)
        print(session.summary())

    Args:
        bot:    بوت Titan مُعدّ مسبقاً (handlers/middleware مُسجَّلة).
        update: update dict — استخدم fake_command/fake_message/fake_callback.
                نفس الـ object يُمرَّر لـ feed_update() في كل دورة دون نسخ.
                في v1 هذا مقبول لأن الـ Core لا يعدّل الـ update dict.
                إذا احتجت كل دورة update مستقلاً (مثلاً لقياس state mutation)،
                مرر n=1 وكرر الاستدعاء يدوياً مع dict مختلف في كل مرة.
        n:      عدد مرات التشغيل. القيمة الافتراضية 1.

    Returns:
        ProfilingSession تحتوي على n إدخالاً من نوع ProfileEntry.
    """
    if n < 1:
        raise ValueError(f"n يجب أن يكون >= 1، استُقبلت القيمة: {n}")

    event_type = _infer_event_type(update)
    original_api = bot._api
    bot._api = RecordingTelegram()

    entries: list[ProfileEntry] = []
    try:
        for _ in range(n):
            start = time.perf_counter()
            await bot.feed_update(update)
            end = time.perf_counter()
            entries.append(
                ProfileEntry(
                    event_type=event_type,
                    duration_ms=(end - start) * 1000,
                    metadata={},
                )
            )
    finally:
        bot._api = original_api

    return ProfilingSession(entries=entries)
