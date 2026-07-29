# ﷽
"""
اختبارات Migration Knowledge API — titan.migration

تغطي:
- ConceptMapping: النموذج، الخصائص، الثبات
- frameworks(): الأطر المدعومة
- concepts(): المفاهيم لكل إطار
- compare(): المقارنة والأخطاء
- اتساق البيانات الداخلية
"""

import pytest
from dataclasses import fields, FrozenInstanceError

from titan.migration import frameworks, concepts, compare, ConceptMapping
from titan.migration.models import ConceptMapping as ConceptMappingDirect


# ===========================================================================
# ConceptMapping — النموذج
# ===========================================================================

class TestConceptMappingModel:
    def test_is_frozen_dataclass(self):
        assert hasattr(ConceptMapping, "__dataclass_fields__")
        m = ConceptMapping(
            framework="ptb",
            concept="command",
            source_name="CommandHandler('start', fn)",
            titan_equivalent="@bot.command('start')",
            difference="Different.",
        )
        with pytest.raises(FrozenInstanceError):
            m.framework = "aiogram"  # type: ignore[misc]

    def test_required_fields(self):
        field_names = {f.name for f in fields(ConceptMapping)}
        assert field_names == {
            "framework",
            "concept",
            "source_name",
            "titan_equivalent",
            "difference",
            "note",
        }

    def test_note_defaults_to_none(self):
        m = ConceptMapping(
            framework="telebot",
            concept="startup",
            source_name="bot.polling()",
            titan_equivalent="bot.run()",
            difference="Async vs sync.",
        )
        assert m.note is None

    def test_note_can_be_set(self):
        m = ConceptMapping(
            framework="ptb",
            concept="routing",
            source_name="ConversationHandler",
            titan_equivalent="AskManager",
            difference="No state machine.",
            note="This is a redesign, not a translation.",
        )
        assert m.note == "This is a redesign, not a translation."

    def test_all_fields_are_strings_or_none(self):
        m = ConceptMapping(
            framework="aiogram",
            concept="middleware",
            source_name="outer/inner",
            titan_equivalent="bot.middleware()",
            difference="One chain.",
            note="Redesign if per-handler.",
        )
        assert isinstance(m.framework, str)
        assert isinstance(m.concept, str)
        assert isinstance(m.source_name, str)
        assert isinstance(m.titan_equivalent, str)
        assert isinstance(m.difference, str)
        assert isinstance(m.note, str)


# ===========================================================================
# frameworks()
# ===========================================================================

class TestFrameworks:
    def test_returns_list(self):
        assert isinstance(frameworks(), list)

    def test_contains_known_frameworks(self):
        result = frameworks()
        assert "ptb" in result
        assert "aiogram" in result
        assert "telebot" in result

    def test_is_sorted(self):
        result = frameworks()
        assert result == sorted(result)

    def test_no_empty_strings(self):
        for fw in frameworks():
            assert fw.strip() != ""

    def test_minimum_count(self):
        """v1 يجب أن يدعم على الأقل 3 أطر."""
        assert len(frameworks()) >= 3


# ===========================================================================
# concepts()
# ===========================================================================

class TestConcepts:
    def test_returns_list_for_known_framework(self):
        for fw in frameworks():
            result = concepts(fw)
            assert isinstance(result, list)

    def test_is_sorted(self):
        for fw in frameworks():
            result = concepts(fw)
            assert result == sorted(result)

    def test_contains_core_concepts(self):
        """كل إطار يجب أن يوثّق المفاهيم الأساسية."""
        core = {"command", "handler", "context", "callback", "error_handler", "startup"}
        for fw in frameworks():
            fw_concepts = set(concepts(fw))
            missing = core - fw_concepts
            assert not missing, f"{fw} is missing core concepts: {missing}"

    def test_unknown_framework_raises_value_error(self):
        with pytest.raises(ValueError, match="not supported"):
            concepts("unknown_framework")

    def test_error_message_lists_supported_frameworks(self):
        with pytest.raises(ValueError) as exc_info:
            concepts("non_existent")
        for fw in frameworks():
            assert fw in str(exc_info.value)

    def test_no_empty_concept_names(self):
        for fw in frameworks():
            for concept in concepts(fw):
                assert concept.strip() != ""


# ===========================================================================
# compare()
# ===========================================================================

class TestCompare:
    def test_returns_concept_mapping(self):
        result = compare("ptb", "command")
        assert isinstance(result, ConceptMapping)

    def test_framework_field_matches_input(self):
        result = compare("aiogram", "middleware")
        assert result.framework == "aiogram"

    def test_concept_field_matches_input(self):
        result = compare("telebot", "callback")
        assert result.concept == "callback"

    def test_non_empty_fields(self):
        """كل حقل مطلوب يجب أن يكون غير فارغ."""
        for fw in frameworks():
            for concept in concepts(fw):
                m = compare(fw, concept)
                assert m.source_name.strip() != "", f"{fw}/{concept}: source_name is empty"
                assert m.titan_equivalent.strip() != "", f"{fw}/{concept}: titan_equivalent is empty"
                assert m.difference.strip() != "", f"{fw}/{concept}: difference is empty"

    def test_unknown_framework_raises_value_error(self):
        with pytest.raises(ValueError, match="not supported"):
            compare("unknown", "command")

    def test_unknown_concept_raises_value_error(self):
        with pytest.raises(ValueError, match="not documented"):
            compare("ptb", "nonexistent_concept")

    def test_unknown_concept_error_lists_available(self):
        with pytest.raises(ValueError) as exc_info:
            compare("aiogram", "nonexistent_concept")
        for concept in concepts("aiogram"):
            assert concept in str(exc_info.value)

    def test_result_is_frozen(self):
        m = compare("ptb", "command")
        with pytest.raises(FrozenInstanceError):
            m.titan_equivalent = "changed"  # type: ignore[misc]

    def test_all_frameworks_all_concepts(self):
        """كل مفهوم في كل إطار يجب أن يُرجع ConceptMapping صالحة."""
        for fw in frameworks():
            for concept in concepts(fw):
                result = compare(fw, concept)
                assert isinstance(result, ConceptMapping)
                assert result.framework == fw
                assert result.concept == concept

    # -----------------------------------------------------------------------
    # PTB specific
    # -----------------------------------------------------------------------

    def test_ptb_command_mentions_decorator(self):
        m = compare("ptb", "command")
        assert "@bot.command" in m.titan_equivalent

    def test_ptb_context_mentions_unified_ctx(self):
        m = compare("ptb", "context")
        assert "ctx" in m.titan_equivalent.lower() or "Context" in m.titan_equivalent

    def test_ptb_routing_has_note(self):
        """ConversationHandler لا يوجد مقابله — يجب أن يكون note موجوداً."""
        m = compare("ptb", "routing")
        assert m.note is not None and m.note.strip() != ""

    # -----------------------------------------------------------------------
    # aiogram specific
    # -----------------------------------------------------------------------

    def test_aiogram_middleware_has_note(self):
        """outer/inner middleware لا يوجد في Titan — يجب أن يكون note موجوداً."""
        m = compare("aiogram", "middleware")
        assert m.note is not None and m.note.strip() != ""

    def test_aiogram_callback_mentions_exact_match(self):
        m = compare("aiogram", "callback")
        assert "exact" in m.difference.lower() or "pattern" in m.difference.lower()

    def test_aiogram_routing_mentions_flat(self):
        m = compare("aiogram", "routing")
        assert "flat" in m.difference.lower() or "nesting" in m.difference.lower()

    # -----------------------------------------------------------------------
    # telebot specific
    # -----------------------------------------------------------------------

    def test_telebot_error_handler_mentions_no_global(self):
        m = compare("telebot", "error_handler")
        assert "no" in m.source_name.lower() or "try" in m.source_name.lower()

    def test_telebot_startup_mentions_backoff(self):
        m = compare("telebot", "startup")
        assert "backoff" in m.difference.lower() or "retry" in m.difference.lower()


# ===========================================================================
# Data consistency
# ===========================================================================

class TestDataConsistency:
    def test_framework_in_mapping_matches_key(self):
        """كل ConceptMapping.framework يجب أن يطابق مفتاح إطارها."""
        for fw in frameworks():
            for concept in concepts(fw):
                m = compare(fw, concept)
                assert m.framework == fw, (
                    f"Mismatch: FRAMEWORKS['{fw}']['{concept}'].framework == '{m.framework}'"
                )

    def test_concept_in_mapping_matches_key(self):
        """كل ConceptMapping.concept يجب أن يطابق مفتاح مفهومه."""
        for fw in frameworks():
            for concept in concepts(fw):
                m = compare(fw, concept)
                assert m.concept == concept, (
                    f"Mismatch: FRAMEWORKS['{fw}']['{concept}'].concept == '{m.concept}'"
                )

    def test_difference_field_is_informative(self):
        """difference يجب أن يكون أطول من 20 حرفاً — ليس placeholder."""
        for fw in frameworks():
            for concept in concepts(fw):
                m = compare(fw, concept)
                assert len(m.difference) > 20, (
                    f"{fw}/{concept}: difference seems too short: {m.difference!r}"
                )


# ===========================================================================
# Public API contract
# ===========================================================================

class TestPublicAPIContract:
    def test_compare_importable_from_titan_migration(self):
        from titan.migration import compare as c
        assert callable(c)

    def test_frameworks_importable_from_titan_migration(self):
        from titan.migration import frameworks as f
        assert callable(f)

    def test_concepts_importable_from_titan_migration(self):
        from titan.migration import concepts as c
        assert callable(c)

    def test_concept_mapping_importable_from_titan_migration(self):
        from titan.migration import ConceptMapping as CM
        # نتحقق من الهوية عبر الاسم والموديول — لا عبر is
        # لأن test_no_circular_import في test suites أخرى يمسح الـ cache
        assert CM.__name__ == "ConceptMapping"
        assert CM.__module__ == "titan.migration.models"

    def test_concept_mapping_not_in_titan_root(self):
        """ConceptMapping لا يُصدَّر من الجذر — Root Export Policy."""
        import titan
        assert not hasattr(titan, "ConceptMapping")

    def test_titan_migration_not_in_titan_root_all(self):
        """لا شيء من titan.migration يُصدَّر من titan.__all__ مباشرةً."""
        import titan
        migration_names = {"ConceptMapping", "frameworks", "concepts", "compare"}
        exported = set(titan.__all__)
        assert not (migration_names & exported)

    def test_no_circular_import(self):
        """استيراد titan.migration لا يسبب circular import."""
        import sys
        for key in list(sys.modules.keys()):
            if "titan" in key:
                del sys.modules[key]
        import titan.migration  # noqa: F401

    def test_exact_framework_concept_matrix(self):
        """
        يثبّت المصفوفة الكاملة للأطر والمفاهيم.
        أي إضافة أو حذف يجب أن يكون قراراً واعياً — لا يحدث صمتاً.
        """
        expected: dict[str, set[str]] = {
            "ptb": {
                "command", "handler", "middleware", "context",
                "callback", "routing", "error_handler", "startup",
            },
            "aiogram": {
                "command", "handler", "middleware", "context",
                "callback", "routing", "error_handler", "startup",
            },
            "telebot": {
                "command", "handler", "context",
                "callback", "routing", "error_handler", "startup",
            },
        }
        assert set(frameworks()) == set(expected.keys()), "Frameworks list changed"
        for fw, expected_concepts in expected.items():
            actual = set(concepts(fw))
            assert actual == expected_concepts, (
                f"Concept matrix changed for '{fw}'. "
                f"Added: {actual - expected_concepts}, "
                f"Removed: {expected_concepts - actual}"
            )

    def test_docs_and_api_concept_names_consistent(self):
        """
        المفاهيم في الـ API يجب أن تكون consistent مع نفسها داخلياً.
        كل مفهوم يُرجع من concepts() يجب أن يكون قابلاً للاستعلام عبر compare().
        """
        for fw in frameworks():
            for concept in concepts(fw):
                mapping = compare(fw, concept)
                assert mapping.framework == fw
                assert mapping.concept == concept
