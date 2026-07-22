"""
titan.profiler

أداة تطوير تقيس wall time لكل update في بيئة محكومة.
تبني فوق titan.playground وbot.feed_update() — لا تعديلات في Core.

غير مُصدَّرة من جذر الحزمة — الاستيراد صريح دائماً:
    from titan.profiler import profile_update

v1: profile_update() + ProfileEntry + ProfilingSession فقط.
راجع docs/decisions/013-performance-profiler.md.
"""

from __future__ import annotations

from titan.profiler._models import ProfileEntry, ProfilingSession
from titan.profiler._run import profile_update

__all__ = [
    "profile_update",
    "ProfileEntry",
    "ProfilingSession",
]
