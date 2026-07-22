# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.health

تقييم حالة البوت الهيكلية والتشغيلية.

الواجهة العامة:
    bot.health() → list[HealthFinding]

كل finding يحمل level (ERROR/WARNING/INFO)، code، وmessage.
القائمة فارغة إذا لم توجد مشكلات.

لا side effects — الطباعة والمعالجة مسؤولية المستهلك.
"""

from titan.health.models import HealthFinding, HealthLevel

__all__ = ["HealthFinding", "HealthLevel"]
