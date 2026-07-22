"""
titan.light._models

نماذج البيانات المُعادة من titan.light.
كل النماذج frozen dataclasses — مقروءة بشرياً ومُهيكلة برمجياً.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from titan.timeline._data import ArchiveEntry


@dataclass(frozen=True)
class SearchResult:
    """
    نتيجة بحث واحدة من search().

    relevance — مجموع أوزان الحقول المتطابقة:
        title: 3  |  tags: 2  |  rule: 2  |  summary: 1
    """

    number: str
    title: str
    matched_fields: list[str]
    relevance: int
    entry: "ArchiveEntry"


@dataclass(frozen=True)
class ArchitectExplanation:
    """
    تفسير قرار معماري واحد — ناتج explain().

    يجمع الحقول الجوهرية من ArchiveEntry في شكل يُيسّر الفهم:
    rule (المبدأ) + summary (ما اتُّخذ ولماذا) + path (للتفاصيل الكاملة).

    path — مسار ملف ADR الكامل لمن يريد تفاصيل أعمق (Alternatives، Consequences).
    """

    number: str
    title: str
    status: str
    date: str
    rule: str
    summary: str
    tags: list[str]
    path: str


@dataclass(frozen=True)
class ArchitectRule:
    """
    قاعدة معمارية جوهرية مستخرجة من ADR — عنصر واحد من rules().

    هذه ليست قواعد بناء جملة Python ولا قواعد lint.
    هي المبادئ التي وجّهت قرارات التصميم في Titan.
    """

    number: str
    title: str
    rule: str
    date: str


@dataclass(frozen=True)
class DecisionSummary:
    """
    ملخص منظم لقرار واحد — عنصر واحد من decisions().
    """

    number: str
    title: str
    status: str
    date: str
    summary: str
    tags: list[str]
    rule: str
