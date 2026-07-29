"""
titan.atlas

طبقة المعرفة المعمارية لـ Titan.

Titan Atlas تفهم قرارات المشروع، تعرض فلسفته، وتجعل المطورين والأدوات
يفهمون لماذا أصبح Titan كما هو.

ليست chatbot، وليست wrapper لـ LLM.
v1 محددة النتائج تماماً — تبني فوق titan.timeline بدون أي تبعية خارجية.

غير مُصدَّرة من جذر الحزمة — الاستيراد صريح دائماً:
    from titan.atlas import search, explain, rules, decisions

راجع docs/decisions/014-architect-ai.md.
"""

from __future__ import annotations

from titan.atlas._core import decisions, explain, rules, search
from titan.atlas._models import (
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
