"""
titan.migration.models

نماذج Migration Knowledge API.

ConceptMapping: نتيجة compare() — frozen dataclass تصف الفرق بين مفهوم
في إطار خارجي ومقابله في Titan.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptMapping:
    """
    نتيجة compare() — تصف الفرق بين مفهوم في إطار خارجي ومقابله في Titan.

    الحقول:
        framework:        معرّف الإطار المصدر  ("ptb", "aiogram", "telebot")
        concept:          اسم المفهوم المُستعلَم  ("middleware", "command", ...)
        source_name:      الاسم أو النمط في الإطار المصدر
        titan_equivalent: المقابل في Titan
        difference:       الفرق الجوهري بين السلوكَين
        note:             ملاحظة اختيارية — تُضاف للحالات التي تحتاج إعادة تصميم
                          لا مجرد ترجمة syntax

    مثال:
        mapping = compare("aiogram", "middleware")
        print(mapping.titan_equivalent)  # "bot.middleware()"
        print(mapping.difference)        # "Titan uses one update-level chain..."
        print(mapping.note)              # "If you need per-handler behavior..."
    """

    framework: str
    concept: str
    source_name: str
    titan_equivalent: str
    difference: str
    note: str | None = None
