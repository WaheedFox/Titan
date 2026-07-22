"""
titan.migration

Migration Knowledge API — قابلة للقراءة برمجياً من الأدوات المستقبلية.

تُجيب على:
    ما هي الأطر المدعومة؟
    ما المفاهيم المُوثَّقة لإطار معين؟
    ما الفرق بين مفهوم في إطار خارجي ومقابله في Titan؟

لا تُحلل كوداً. لا تقترح إصلاحات. لا تُترجم مشاريع.
Migration Assistant يشرح الفلسفة — لا يُترجم الكود.

مثال:
    from titan.migration import frameworks, concepts, compare

    frameworks()
    # ["aiogram", "ptb", "telebot"]

    concepts("aiogram")
    # ["callback", "command", "context", "error_handler", "handler", "middleware", "routing", "startup"]

    mapping = compare("aiogram", "middleware")
    print(mapping.titan_equivalent)  # "bot.middleware()"
    print(mapping.difference)        # "Titan uses one update-level chain..."

للأدلة النصية الفلسفية:
    → docs/migration/from-ptb.md
    → docs/migration/from-aiogram.md
    → docs/migration/from-telebot.md
"""

from __future__ import annotations

from titan.migration.models import ConceptMapping
from titan.migration._data import FRAMEWORKS


def frameworks() -> list[str]:
    """
    يُرجع قائمة مرتبة بمعرّفات الأطر المدعومة.

    مثال:
        frameworks()
        # ["aiogram", "ptb", "telebot"]
    """
    return sorted(FRAMEWORKS.keys())


def concepts(framework: str) -> list[str]:
    """
    يُرجع قائمة مرتبة بأسماء المفاهيم المُوثَّقة لإطار معين.

    يرمي ValueError إذا كان الإطار غير مدعوم.

    مثال:
        concepts("aiogram")
        # ["callback", "command", "context", "error_handler",
        #  "handler", "middleware", "routing", "startup"]
    """
    if framework not in FRAMEWORKS:
        supported = ", ".join(sorted(FRAMEWORKS.keys()))
        raise ValueError(
            f"Framework '{framework}' is not supported. "
            f"Supported frameworks: {supported}"
        )
    return sorted(FRAMEWORKS[framework].keys())


def compare(framework: str, concept: str) -> ConceptMapping:
    """
    يُرجع ConceptMapping يصف الفرق بين مفهوم في إطار خارجي ومقابله في Titan.

    يرمي ValueError إذا كان الإطار أو المفهوم غير مدعوم.

    مثال:
        mapping = compare("aiogram", "middleware")
        print(mapping.source_name)       # "dp.update.outer_middleware() / ..."
        print(mapping.titan_equivalent)  # "bot.middleware()"
        print(mapping.difference)        # "Titan uses one update-level chain..."
        print(mapping.note)              # "If you need per-handler behavior..."
    """
    if framework not in FRAMEWORKS:
        supported = ", ".join(sorted(FRAMEWORKS.keys()))
        raise ValueError(
            f"Framework '{framework}' is not supported. "
            f"Supported frameworks: {supported}"
        )
    fw_data = FRAMEWORKS[framework]
    if concept not in fw_data:
        available = ", ".join(sorted(fw_data.keys()))
        raise ValueError(
            f"Concept '{concept}' is not documented for '{framework}'. "
            f"Available concepts: {available}"
        )
    return fw_data[concept]


__all__ = ["ConceptMapping", "frameworks", "concepts", "compare"]
