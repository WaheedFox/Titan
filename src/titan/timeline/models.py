"""
titan.timeline.models

نماذج titan.timeline.

ArchiveEntry: عنصر واحد في الذاكرة المعمارية لـ Titan — frozen dataclass.

v1 يحتوي إدخالات من نوع ADR فقط. الحقول مصمَّمة لتبقى صالحة عندما تُضاف
أنواع إدخالات أخرى مستقبلاً (Feature Completion, Major Refactor,
Protocol Introduction, Breaking Change) — لا افتراض أن كل إدخال هو ADR.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchiveEntry:
    """
    إدخال واحد في الذاكرة المعمارية لـ Titan.

    الحقول:
        number:  المعرّف الرقمي كنص  ("001", "009")
        title:   عنوان القرار  ("Keyboard Builder")
        status:  حالة القرار  ("Accepted", "Rejected", "Deferred")
        rule:    المبدأ العام المُشتَق من هذا القرار — dict ثنائي اللغة.
                 المفاتيح المدعومة: "en" (إنجليزي) و "ar" (عربي).
                 الإنجليزية هي fallback الأساسية عند غياب اللغة المطلوبة.
                 استهلاك مُوجَّه: titan.light.rules(locale="en")
        summary: ملخص موجز لما تقرر ولماذا
        tags:    كلمات مفتاحية موضوعية — tuple ثابتة، لا list
        date:    تاريخ القرار إن وُثِّق في الملف الأصلي، وإلا None
        path:    مسار مستند ADR الأصلي — يفتحه المستهلك مباشرةً للمصدر الكامل

    مثال:
        entry = entries()[0]
        print(entry.number, entry.title, entry.status)
        print(entry.rule)
    """

    number: str
    title: str
    status: str
    rule: dict[str, str]
    summary: str
    tags: tuple[str, ...]
    date: str | None
    path: str
