"""
titan.light

طبقة المعرفة المعمارية لـ Titan.

Titan Light تفهم قرارات المشروع، تعرض فلسفته، وتجعل المطورين والأدوات
يفهمون لماذا أصبح Titan كما هو.

ليست chatbot، وليست wrapper لـ LLM.
v1 محددة النتائج تماماً — تبني فوق titan.timeline بدون أي تبعية خارجية.

غير مُصدَّرة من جذر الحزمة — الاستيراد صريح دائماً:
    from titan.light import search, explain, rules, decisions

راجع docs/decisions/014-architect-ai.md.
"""

from __future__ import annotations

from titan.light._core import decisions, explain, rules, search
from titan.light._models import (
    ArchitectExplanation,
    ArchitectRule,
    DecisionSummary,
    SearchResult,
)

__all__ = [
    # الدوال الأربع
    "search",
    "explain",
    "rules",
    "decisions",
    # النماذج
    "SearchResult",
    "ArchitectExplanation",
    "ArchitectRule",
    "DecisionSummary",
]
