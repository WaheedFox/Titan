"""
titan.timeline

الذاكرة المعمارية لـ Titan — قابلة للقراءة برمجياً من الأدوات المستقبلية.

titan.timeline ليست قارئ ADR. هي الذاكرة المعمارية للمشروع: فلسفته،
قراراته، وتطوره التاريخي، مُعرَّضة برمجياً.

v1 يحتوي إدخالات من نوع ADR فقط. الشكل مصمَّم بحيث لا يفترض أن كل إدخال
هو ADR إلى الأبد — أنواع إدخالات مستقبلية (Feature Completion, Major
Refactor, Protocol Introduction, Breaking Change) تنضم لاحقاً بنفس البنية.

لا تحليل Markdown في وقت التشغيل. titan.timeline._data هو مصدر الحقيقة
الوحيد — نفس فلسفة titan.migration و titan.health: بيانات ثابتة، صريحة،
غير متغيّرة.

مثال:
    from titan import timeline

    for entry in timeline.entries():
        print(entry.number, entry.title, entry.status)

    entry = timeline.entry("003")
    print(entry.rule)

    accepted = timeline.by_status("Accepted")

    for rule in timeline.rules():
        print(rule)
"""

from __future__ import annotations

from titan.timeline.models import ArchiveEntry
from titan.timeline._data import ENTRIES


def entries() -> list[ArchiveEntry]:
    """
    يُرجع كل إدخالات الذاكرة المعمارية، مرتّبة حسب number.

    مثال:
        entries()[0].title
        # "Keyboard Builder"
    """
    return sorted(ENTRIES, key=lambda e: e.number)


def entry(number: str) -> ArchiveEntry | None:
    """
    يُرجع الإدخال المطابق لـ number، أو None إذا لم يوجد.

    مثال:
        entry("003").title
        # "Capabilities"

        entry("999")
        # None
    """
    for e in ENTRIES:
        if e.number == number:
            return e
    return None


def by_status(status: str) -> list[ArchiveEntry]:
    """
    يُرجع الإدخالات المطابقة لـ status، مرتّبة حسب number.

    المطابقة حساسة لحالة الأحرف — نفس القيم الموثّقة في الملفات الأصلية
    ("Accepted", "Rejected", "Deferred").

    مثال:
        by_status("Rejected")
        # [ArchiveEntry(number="001", title="Keyboard Builder", ...)]
    """
    return sorted((e for e in ENTRIES if e.status == status), key=lambda e: e.number)


def latest(n: int) -> list[ArchiveEntry]:
    """
    يُرجع آخر n إدخال حسب number، من الأحدث إلى الأقدم.

    مثال:
        latest(2)
        # [ArchiveEntry(number="009", ...), ArchiveEntry(number="008", ...)]
    """
    return sorted(ENTRIES, key=lambda e: e.number, reverse=True)[:n]


def rules() -> list[dict[str, str]]:
    """
    يُرجع كل قاعدة معمارية مُشتقة من الذاكرة، مرتّبة حسب number.

    كل قاعدة dict ثنائي اللغة: {"en": "...", "ar": "..."}.
    للحصول على النص في لغة محددة مع fallback تلقائي استخدم titan.light.rules():

        from titan.light import rules
        for r in rules(locale="en"):
            print(r.rule)

    titan.timeline بهذا المعنى نظام ذاكرة فلسفية، لا مجرد فهرس Markdown.
    """
    return [e.rule for e in entries()]


__all__ = [
    "ArchiveEntry",
    "entries",
    "entry",
    "by_status",
    "latest",
    "rules",
]
