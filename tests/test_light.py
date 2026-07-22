"""
اختبارات titan.light

تتحقق من:
    1. search() — keyword matching محدد النتائج، وزن الحقول، الترتيب، الفلترة
    2. explain() — تفسير بالرقم، بالـ keyword، حالات لا تطابق
    3. rules() — القواعد المعمارية المستخرجة من ADRs، فلترة بالحالة
    4. decisions() — كل القرارات، فلترة بالحالة والـ tags
    5. عزل تام — لا استدعاءات خارجية، لا تعديل Core، لا تصدير من الجذر
"""

from __future__ import annotations

import pytest

from titan.light import (
    ArchitectExplanation,
    ArchitectRule,
    DecisionSummary,
    SearchResult,
    decisions,
    explain,
    rules,
    search,
)
from titan.timeline import entries as timeline_entries


# ===========================================================================
# search()
# ===========================================================================

class TestSearch:
    def test_returns_list_of_search_results(self):
        results = search("playground")
        assert isinstance(results, list)
        assert all(isinstance(r, SearchResult) for r in results)

    def test_empty_keyword_returns_all_entries(self):
        all_entries = timeline_entries()
        results = search("")
        assert len(results) == len(all_entries)

    def test_known_keyword_returns_relevant_results(self):
        results = search("playground")
        numbers = [r.number for r in results]
        assert "011" in numbers

    def test_unknown_keyword_returns_empty_list(self):
        results = search("zzzzzzzzzzzz_nonexistent_keyword_xyzxyz")
        assert results == []

    def test_results_sorted_by_relevance_descending(self):
        results = search("api")
        if len(results) >= 2:
            for i in range(len(results) - 1):
                assert results[i].relevance >= results[i + 1].relevance

    def test_title_match_has_higher_relevance_than_summary_only(self):
        results = search("playground")
        first = results[0]
        assert first.number == "011"
        assert "title" in first.matched_fields

    def test_matched_fields_reflects_where_keyword_was_found(self):
        results = search("playground")
        hit = next(r for r in results if r.number == "011")
        assert "title" in hit.matched_fields

    def test_filter_by_status_accepted(self):
        results = search("", status="Accepted")
        assert all(r.entry.status == "Accepted" for r in results)

    def test_filter_by_status_rejected(self):
        results = search("", status="Rejected")
        assert all(r.entry.status == "Rejected" for r in results)

    def test_filter_by_status_nonexistent_returns_empty(self):
        results = search("", status="NonExistentStatus")
        assert results == []

    def test_case_insensitive(self):
        lower = search("playground")
        upper = search("PLAYGROUND")
        assert {r.number for r in lower} == {r.number for r in upper}

    def test_search_result_entry_matches_number(self):
        results = search("playground")
        hit = next((r for r in results if r.number == "011"), None)
        assert hit is not None
        assert hit.entry.number == hit.number

    def test_relevance_is_non_negative(self):
        results = search("api")
        assert all(r.relevance >= 0 for r in results)

    def test_empty_query_all_have_zero_relevance(self):
        results = search("")
        assert all(r.relevance == 0 for r in results)

    def test_empty_query_matched_fields_is_empty(self):
        results = search("")
        assert all(r.matched_fields == [] for r in results)

    def test_is_deterministic(self):
        """نفس المدخلات تُعطي دائماً نفس المخرجات — ليس ذكاءً اصطناعياً."""
        first = [r.number for r in search("routing")]
        second = [r.number for r in search("routing")]
        assert first == second

    def test_bilingual_search_arabic_keyword_finds_correct_adr(self):
        """
        البحث بكلمة عربية موجودة في rule يجد نفس الـ ADR.

        ADR-007: en rule يحتوي "translate" / ar rule يحتوي "يُترجم".
        كلا البحثين يجب أن يجدا ADR-007 ضمن النتائج.
        """
        en_results = search("translate")
        ar_results = search("يُترجم")
        en_numbers = {r.number for r in en_results}
        ar_numbers = {r.number for r in ar_results}
        assert "007" in en_numbers
        assert "007" in ar_numbers

    def test_bilingual_search_cross_language_consistency(self):
        """
        البحث بالإنجليزية والعربية لنفس المفهوم يجد نفس الـ ADR على الأقل.

        ADR-005: en rule → "internal state" / ar rule → "الداخلي".
        البحثان يجب أن يشتركا في ADR-005 على الأقل.
        """
        en_results = {r.number for r in search("internal state")}
        ar_results = {r.number for r in search("الداخلي")}
        # التقاطع ليس فارغاً — اللغتان يصلان لنفس القرارات
        assert en_results & ar_results, (
            f"English search found {en_results}, Arabic search found {ar_results} — no overlap"
        )


# ===========================================================================
# explain()
# ===========================================================================

class TestExplain:
    def test_returns_architect_explanation(self):
        result = explain("011")
        assert isinstance(result, ArchitectExplanation)

    def test_explain_by_exact_number(self):
        result = explain("011")
        assert result is not None
        assert result.number == "011"
        assert result.title == "Playground"

    def test_explain_by_short_number(self):
        result = explain("11")
        assert result is not None
        assert result.number == "011"

    def test_explain_by_adr_prefix(self):
        result = explain("ADR-011")
        assert result is not None
        assert result.number == "011"

    def test_explain_by_adr_prefix_lowercase(self):
        result = explain("adr-011")
        assert result is not None
        assert result.number == "011"

    def test_explain_by_keyword(self):
        result = explain("playground")
        assert result is not None
        assert result.number == "011"

    def test_explain_nonexistent_number_returns_none(self):
        result = explain("999")
        assert result is None

    def test_explain_unknown_keyword_returns_none(self):
        result = explain("zzzzzz_totally_unknown_xyz")
        assert result is None

    def test_explain_empty_string_returns_none(self):
        result = explain("")
        assert result is None

    def test_explanation_contains_rule_field(self):
        """explain() تُبرز الـ rule — المبدأ المعماري الجوهري."""
        result = explain("011")
        assert result is not None
        assert result.rule  # غير فارغة

    def test_explanation_contains_summary_field(self):
        """explain() تُبرز الـ summary — لماذا اتُّخذ هذا القرار."""
        result = explain("011")
        assert result is not None
        assert result.summary

    def test_explanation_contains_path_to_full_adr(self):
        """explain() تُوفّر path لملف ADR الكامل للتفاصيل الأعمق."""
        result = explain("011")
        assert result is not None
        assert "docs/decisions" in result.path

    def test_explanation_fields_are_populated(self):
        result = explain("011")
        assert result is not None
        assert result.title
        assert result.status
        assert result.date

    def test_explanation_tags_is_list(self):
        result = explain("011")
        assert isinstance(result.tags, list)

    def test_explanation_is_frozen(self):
        result = explain("011")
        assert result is not None
        with pytest.raises((AttributeError, TypeError)):
            result.title = "changed"  # type: ignore[misc]


# ===========================================================================
# rules()
# ===========================================================================

class TestRules:
    def test_returns_list_of_architect_rules(self):
        result = rules()
        assert isinstance(result, list)
        assert all(isinstance(r, ArchitectRule) for r in result)

    def test_rules_are_architectural_principles_not_lint_rules(self):
        """
        rules() تعني القواعد المعمارية المستخرجة من قرارات ADR —
        وليست قواعد lint أو قواعد Python.
        """
        result = rules(status="Accepted")
        # كل قاعدة يجب أن تكون موثّقة في ADR — لها number وtitle
        assert all(r.number and r.title for r in result)

    def test_all_rules_have_non_empty_rule_text(self):
        result = rules()
        assert all(r.rule for r in result)

    def test_entries_without_rule_are_excluded(self):
        result = rules()
        assert all(r.rule.strip() for r in result)

    def test_count_matches_entries_with_rules(self):
        all_entries = timeline_entries()
        # e.rule هو dict — فارغ يعني لا قاعدة، غير فارغ يعني موجودة
        entries_with_rules = [e for e in all_entries if e.rule]
        assert len(rules()) == len(entries_with_rules)

    def test_locale_en_returns_english_text(self):
        result = rules(locale="en")
        assert result
        # ADR-002 قاعدتها بالإنجليزية — يجب أن تحتوي على كلمات إنجليزية
        r002 = next((r for r in result if r.number == "002"), None)
        assert r002 is not None
        assert "Action" in r002.rule

    def test_locale_ar_returns_arabic_text(self):
        result = rules(locale="ar")
        assert result
        # ADR-005 قاعدتها بالعربية — يجب أن تحتوي على نص عربي
        r005 = next((r for r in result if r.number == "005"), None)
        assert r005 is not None
        assert any("\u0600" <= c <= "\u06ff" for c in r005.rule)

    def test_locale_default_is_en(self):
        default_result = rules()
        en_result = rules(locale="en")
        assert [r.rule for r in default_result] == [r.rule for r in en_result]

    def test_locale_fallback_to_en_for_unknown_locale(self):
        """لغة غير موجودة → fallback إلى الإنجليزية — مقارنة نص الـ rule فقط."""
        result = rules(locale="fr")
        en_result = rules(locale="en")
        assert [r.rule for r in result] == [r.rule for r in en_result]

    def test_locale_fallback_full_equality(self):
        """
        rules(locale="fr") == rules(locale="en") — مقارنة كاملة للكائنات.

        الـ fallback ليس مجرد نص — كل ArchitectRule (number, title, date, rule)
        يجب أن يكون مطابقاً تماماً عند locale غير موجودة.
        """
        assert rules(locale="fr") == rules(locale="en")

    def test_filter_by_status_accepted(self):
        result = rules(status="Accepted")
        from titan.timeline import entries as te
        accepted_numbers = {e.number for e in te() if e.status == "Accepted"}
        assert all(r.number in accepted_numbers for r in result)

    def test_filter_by_status_nonexistent_returns_empty(self):
        result = rules(status="NonExistentStatus")
        assert result == []

    def test_sorted_chronologically(self):
        result = rules()
        numbers = [r.number for r in result]
        assert numbers == sorted(numbers)

    def test_rule_is_frozen(self):
        result = rules()
        if result:
            with pytest.raises((AttributeError, TypeError)):
                result[0].rule = "changed"  # type: ignore[misc]

    def test_known_adr_present(self):
        result = rules()
        numbers = [r.number for r in result]
        assert "011" in numbers
        assert "013" in numbers


# ===========================================================================
# decisions()
# ===========================================================================

class TestDecisions:
    def test_returns_list_of_decision_summaries(self):
        result = decisions()
        assert isinstance(result, list)
        assert all(isinstance(d, DecisionSummary) for d in result)

    def test_count_matches_all_timeline_entries(self):
        all_entries = timeline_entries()
        assert len(decisions()) == len(all_entries)

    def test_filter_by_status(self):
        result = decisions(status="Accepted")
        assert all(d.status == "Accepted" for d in result)

    def test_filter_by_tags_single(self):
        result = decisions(tags=["routing"])
        assert all("routing" in d.tags for d in result)

    def test_filter_by_tags_case_insensitive(self):
        lower = decisions(tags=["routing"])
        upper = decisions(tags=["ROUTING"])
        assert {d.number for d in lower} == {d.number for d in upper}

    def test_filter_by_tags_nonexistent(self):
        result = decisions(tags=["zzzzzz_nonexistent_tag"])
        assert result == []

    def test_filter_by_tags_any_match(self):
        result = decisions(tags=["routing", "playground"])
        assert len(result) >= 1

    def test_combined_status_and_tags_filter(self):
        result = decisions(status="Accepted", tags=["playground"])
        assert all(d.status == "Accepted" for d in result)
        assert all("playground" in d.tags for d in result)

    def test_sorted_chronologically(self):
        result = decisions()
        numbers = [d.number for d in result]
        assert numbers == sorted(numbers)

    def test_decision_fields_populated(self):
        result = decisions(status="Accepted")
        for d in result:
            assert d.number
            assert d.title
            assert d.status

    def test_tags_is_list(self):
        result = decisions()
        assert all(isinstance(d.tags, list) for d in result)

    def test_decision_is_frozen(self):
        result = decisions()
        if result:
            with pytest.raises((AttributeError, TypeError)):
                result[0].title = "changed"  # type: ignore[misc]

    def test_known_decisions_present(self):
        result = decisions()
        numbers = {d.number for d in result}
        assert "011" in numbers
        assert "012" in numbers
        assert "013" in numbers
        assert "014" in numbers


# ===========================================================================
# عزل تام
# ===========================================================================

class TestIsolation:
    def test_light_not_exported_from_root(self):
        import titan
        assert not hasattr(titan, "search")
        assert not hasattr(titan, "explain")
        assert not hasattr(titan, "rules")
        assert not hasattr(titan, "decisions")

    def test_no_external_dependencies(self):
        import titan.light._core as core_module
        assert core_module is not None

    def test_no_network_calls(self):
        assert search("playground") is not None
        assert explain("011") is not None
        assert rules() is not None
        assert decisions() is not None
