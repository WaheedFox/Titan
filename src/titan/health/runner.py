# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.health.runner

تشغيل فحوصات Project Health على bot instance.

الواجهة الوحيدة: run_checks(bot) → list[HealthFinding]

يُستدعى من bot.health() فقط — لا يُستخدم مباشرةً.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from titan.health.checks import ALL_CHECKS
from titan.health.models import HealthFinding

if TYPE_CHECKING:
    from titan.bot import Titan


def run_checks(bot: "Titan") -> list[HealthFinding]:
    """
    شغّل جميع الفحوصات على الـ bot وأعد النتائج.

    تُعيد قائمة من الـ findings بالترتيب.
    إذا كانت القائمة فارغة — البوت سليم.

    الفحوصات التشغيلية (capabilities) تُتجاهل بصمت
    إذا كانت bot.capabilities غير متاحة بعد.
    """
    findings: list[HealthFinding] = []
    for check in ALL_CHECKS:
        result = check(bot)
        if result is not None:
            findings.append(result)
    return findings
