"""
titan.profiler._models

ProfileEntry وProfilingSession — النماذج الأساسية لتسجيل نتائج القياس.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProfileEntry:
    """
    إدخال قياس واحد لـ update واحد.

    الحقول المضمونة:
        event_type  — نوع الحدث ("command/start"، "message"، "callback/yes"، ...)
        duration_ms — wall time الكلي بالمللي ثانية

    الحقول غير المضمونة:
        metadata    — مفتوح للتوسع المستقبلي، فارغ {} في v1.
                      Titan لا تضمن محتوياته — لا تبن كوداً يعتمد على مفاتيحه.
    """

    event_type: str
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


class ProfilingSession:
    """
    مجموعة إدخالات قياس ناتجة عن profile_update().

    مثال:
        session = await profile_update(bot, fake_command("start"), n=100)
        session.summary()
        # {"command/start": {"count": 100, "avg_ms": 1.2, "min_ms": 0.8, "max_ms": 4.3}}
    """

    def __init__(self, entries: list[ProfileEntry]) -> None:
        self.entries = list(entries)

    def summary(self) -> dict[str, dict[str, float]]:
        """
        يُعيد إحصائيات مجمَّعة لكل event_type:
            count   — عدد القياسات
            avg_ms  — المتوسط
            min_ms  — الأدنى
            max_ms  — الأعلى
        """
        if not self.entries:
            return {}

        groups: dict[str, list[float]] = {}
        for entry in self.entries:
            groups.setdefault(entry.event_type, []).append(entry.duration_ms)

        return {
            event_type: {
                "count": len(durations),
                "avg_ms": sum(durations) / len(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
            }
            for event_type, durations in groups.items()
        }
