"""
titan.light._core

تنفيذ الدوال الأربع: search()، explain()، rules()، decisions().

كل شيء يبني فوق titan.timeline — لا استدعاءات خارجية، لا LLM.
النتائج محددة تماماً: نفس المدخلات تُعطي دائماً نفس المخرجات.
"""

from __future__ import annotations

import re

import titan.timeline as _timeline
from titan.timeline._data import ArchiveEntry

from titan.light._models import (
    ArchitectExplanation,
    ArchitectRule,
    DecisionSummary,
    SearchResult,
)

# ---------------------------------------------------------------------------
# أوزان حقول البحث
# ---------------------------------------------------------------------------

_FIELD_WEIGHTS: dict[str, int] = {
    "title": 3,
    "tags": 2,
    "rule": 2,
    "summary": 1,
}


def _resolve_rule(rule: dict[str, str], locale: str) -> str:
    """
    يُعيد نص القاعدة باللغة المطلوبة مع fallback إلى الإنجليزية.

    ترتيب الأولوية:
        1. اللغة المطلوبة (locale)
        2. الإنجليزية ("en") — fallback أساسي
        3. أول قيمة متاحة في الـ dict (احتياطي أخير)

    يُعيد سلسلة فارغة إذا كان الـ dict فارغاً.
    """
    return rule.get(locale) or rule.get("en") or next(iter(rule.values()), "")


def _match_entry(entry: ArchiveEntry, keyword: str) -> SearchResult | None:
    """
    يبحث عن keyword في حقول entry ويُعيد SearchResult أو None.
    البحث case-insensitive، keyword واحد في كل مرة.
    يبحث في جميع اللغات المتاحة لحقل rule.
    """
    kw = keyword.lower()
    matched: list[str] = []
    relevance = 0

    if kw in entry.title.lower():
        matched.append("title")
        relevance += _FIELD_WEIGHTS["title"]

    tags_text = " ".join(entry.tags).lower()
    if kw in tags_text:
        matched.append("tags")
        relevance += _FIELD_WEIGHTS["tags"]

    # يبحث في جميع اللغات المتاحة — البحث شامل بغض النظر عن اللغة
    rule_text = " ".join(entry.rule.values()).lower()
    if kw in rule_text:
        matched.append("rule")
        relevance += _FIELD_WEIGHTS["rule"]

    if kw in (entry.summary or "").lower():
        matched.append("summary")
        relevance += _FIELD_WEIGHTS["summary"]

    if not matched:
        return None

    return SearchResult(
        number=entry.number,
        title=entry.title,
        matched_fields=matched,
        relevance=relevance,
        entry=entry,
    )


def _normalize_number(raw: str) -> str | None:
    """
    يُحوّل "11" و"ADR-011" و"011" كلها إلى "011" (zero-padded إلى 3 أرقام).
    يُعيد None إذا لم يكن الإدخال رقماً قابلاً للتعرف عليه.
    """
    cleaned = re.sub(r"(?i)^adr-?", "", raw.strip())
    if cleaned.isdigit():
        return cleaned.zfill(3)
    return None


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------

def search(
    keyword: str,
    *,
    status: str | None = None,
) -> list[SearchResult]:
    """
    بحث محدد النتائج (deterministic) عن keyword في قرارات Titan المعمارية.

    هذا ليس ذكاءً اصطناعياً — هو keyword matching موزون على حقول محددة.
    نفس الكلمة تُعطي دائماً نفس النتائج بنفس الترتيب.

    البحث في حقل rule يشمل جميع اللغات المتاحة (en وar).

    أوزان الحقول:
        title   → 3   (التطابق في العنوان أقوى دلالةً)
        tags    → 2
        rule    → 2
        summary → 1

    الـ relevance = مجموع أوزان الحقول المتطابقة في الإدخال.
    البحث case-insensitive، بدون fuzzy أو stemming في v1.

    Args:
        keyword: نص البحث. سلسلة فارغة تُعيد كل القرارات.
        status:  فلترة بالحالة ("Accepted"، "Rejected"، ...). None = الكل.

    Returns:
        list[SearchResult] مرتبة تنازلياً بالـ relevance.

    مثال:
        from titan.light import search
        for r in search("playground"):
            print(r.number, r.title, r.relevance)
    """
    all_entries: list[ArchiveEntry] = _timeline.entries()

    if status is not None:
        all_entries = [e for e in all_entries if e.status == status]

    kw = keyword.strip()

    if not kw:
        # كلمة فارغة → كل القرارات كـ SearchResult بـ relevance=0
        return [
            SearchResult(
                number=e.number,
                title=e.title,
                matched_fields=[],
                relevance=0,
                entry=e,
            )
            for e in all_entries
        ]

    results: list[SearchResult] = []
    for entry in all_entries:
        result = _match_entry(entry, kw)
        if result is not None:
            results.append(result)

    results.sort(key=lambda r: r.relevance, reverse=True)
    return results


# ---------------------------------------------------------------------------
# explain()
# ---------------------------------------------------------------------------

def explain(query: str, *, locale: str = "en") -> ArchitectExplanation | None:
    """
    يُقدّم تفسيراً لقرار معماري — أكثر من مجرد استرجاع.

    الفرق عن search(): explain() تُعيد قراراً واحداً مع تركيز على الـ rule
    (المبدأ الذي أرسته) والـ summary (لماذا اتُّخذ هذا القرار تحديداً).
    المطور يقرأ explain() ليفهم الدافع المعماري، لا ليحصل على قائمة.

    منطق التطابق:
        - رقم ("011"، "11"، "ADR-011") → تطابق مباشر بالرقم
        - نص                           → search() والإدخال الأعلى relevance

    Args:
        query:  رقم القرار أو كلمة مفتاحية.
        locale: لغة حقل rule في الناتج ("en" أو "ar"). افتراضي: "en".
                إذا لم تتوفر اللغة المطلوبة يعود إلى الإنجليزية.

    Returns:
        ArchitectExplanation | None (None إذا لم يُوجد تطابق).

    مثال:
        from titan.light import explain

        exp = explain("011")
        print(exp.rule)     # ← المبدأ المعماري بالإنجليزية (افتراضي)
        print(exp.summary)  # ← ما اتُّخذ ولماذا
        print(exp.path)     # ← مسار ADR الكامل للتفاصيل الأعمق

        exp = explain("011", locale="ar")   # المبدأ بالعربية
        exp = explain("playground")         # بالكلمة المفتاحية
    """
    query = query.strip()
    if not query:
        return None

    # محاولة تطابق رقم مباشر
    normalized = _normalize_number(query)
    if normalized is not None:
        found = _timeline.entry(normalized)
        if found is not None:
            return _entry_to_explanation(found, locale)
        return None

    # تطابق keyword → أفضل نتيجة
    results = search(query)
    if not results:
        return None
    return _entry_to_explanation(results[0].entry, locale)


def _entry_to_explanation(entry: ArchiveEntry, locale: str = "en") -> ArchitectExplanation:
    return ArchitectExplanation(
        number=entry.number,
        title=entry.title,
        status=entry.status,
        date=entry.date,
        rule=_resolve_rule(entry.rule, locale),
        summary=entry.summary or "",
        tags=list(entry.tags),
        path=entry.path,
    )


# ---------------------------------------------------------------------------
# rules()
# ---------------------------------------------------------------------------

def rules(*, status: str | None = None, locale: str = "en") -> list[ArchitectRule]:
    """
    يُعيد القواعد المعمارية الجوهرية المستخرجة من قرارات Titan.

    هذه ليست قواعد بناء الجملة Python، ولا قواعد lint، ولا قواعد routing.
    هي المبادئ التي وجّهت قرارات التصميم — الـ "rule" field في كل ADR —
    الجملة التي تلخّص لماذا اتُّخذ هذا القرار وما الحدّ الذي يرسيه.

    إدخالات بدون rule field لا تظهر في النتيجة.

    Args:
        status: فلترة بالحالة ("Accepted"، "Rejected"، ...). None = الكل.
        locale: لغة نص القاعدة ("en" أو "ar"). افتراضي: "en".
                إذا لم تتوفر اللغة المطلوبة يعود إلى الإنجليزية.

    Returns:
        list[ArchitectRule] مرتبة تاريخياً.

    مثال:
        from titan.light import rules

        for r in rules(locale="en"):
            print(f"ADR-{r.number} ({r.title}): {r.rule}")

        for r in rules(locale="ar", status="Accepted"):
            print(f"ADR-{r.number}: {r.rule}")
    """
    all_entries = _timeline.entries()

    if status is not None:
        all_entries = [e for e in all_entries if e.status == status]

    return [
        ArchitectRule(
            number=e.number,
            title=e.title,
            rule=_resolve_rule(e.rule, locale),
            date=e.date,
        )
        for e in all_entries
        if e.rule  # يتجاهل الإدخالات بدون قاعدة (dict فارغ)
    ]


# ---------------------------------------------------------------------------
# decisions()
# ---------------------------------------------------------------------------

def decisions(
    *,
    status: str | None = None,
    tags: list[str] | None = None,
    locale: str = "en",
) -> list[DecisionSummary]:
    """
    يُعيد ملخصات منظمة لجميع القرارات المعمارية، مرتبةً تاريخياً.

    Args:
        status: فلترة بالحالة ("Accepted"، "Rejected"، ...). None = الكل.
        tags:   فلترة: يُعيد فقط القرارات التي تحتوي على أحد هذه التصنيفات.
        locale: لغة حقل rule في الناتج ("en" أو "ar"). افتراضي: "en".
                إذا لم تتوفر اللغة المطلوبة يعود إلى الإنجليزية.

    مثال:
        from titan.light import decisions

        for d in decisions(status="Accepted"):
            print(d.number, d.title)

        for d in decisions(tags=["routing"], locale="ar"):
            print(d.number, d.rule)
    """
    all_entries = _timeline.entries()

    if status is not None:
        all_entries = [e for e in all_entries if e.status == status]

    if tags is not None:
        tag_set = {t.lower() for t in tags}
        all_entries = [
            e for e in all_entries
            if any(t.lower() in tag_set for t in e.tags)
        ]

    return [
        DecisionSummary(
            number=e.number,
            title=e.title,
            status=e.status,
            date=e.date,
            summary=e.summary or "",
            tags=list(e.tags),
            rule=_resolve_rule(e.rule, locale),
        )
        for e in all_entries
    ]
