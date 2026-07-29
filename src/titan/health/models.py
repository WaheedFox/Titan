# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.health.models

نماذج البيانات الخاصة بـ Project Health.
"""

from __future__ import annotations

from enum import Enum


class HealthLevel(str, Enum):
    """
    مستوى خطورة الـ finding.

    ERROR   — البوت معطل فعلياً (مثال: لا handlers مسجلة)
    WARNING — غالباً خطأ، نادراً مقصود (مثال: لا error handler)
    INFO    — ملاحظة، قد تكون مقصودة (مثال: capability غير مستخدمة)
    """

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class HealthFinding:
    """
    نتيجة فحص واحد من فحوصات Project Health.

    الخصائص:
        level   — مستوى الخطورة (ERROR / WARNING / INFO)
        code    — معرّف ثابت قابل للمقارنة البرمجية
        message — وصف بشري يشرح المشكلة

    لا تُنشئ هذا الكائن مباشرةً — يُعيده bot.health().
    """

    __slots__ = ("level", "code", "message")

    def __init__(self, level: HealthLevel, code: str, message: str) -> None:
        self.level = level
        self.code = code
        self.message = message

    def __repr__(self) -> str:
        return f"HealthFinding(level={self.level!r}, code={self.code!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HealthFinding):
            return NotImplemented
        return self.level == other.level and self.code == other.code and self.message == other.message

    def __hash__(self) -> int:
        return hash((self.level, self.code, self.message))
