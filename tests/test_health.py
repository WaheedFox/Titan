# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
اختبارات Project Health — titan.health
"""

import pytest
from titan.bot import Titan
from titan.health.models import HealthFinding, HealthLevel
from titan.health.checks import (
    check_no_handlers,
    check_no_error_handler,
    check_inline_capability_unused,
    check_group_capability_unused,
    check_privacy_mode_disabled_unused,
)
from titan.health.runner import run_checks


# -------------------------
# Helpers
# -------------------------

def make_bot() -> Titan:
    return Titan("fake-token")


def make_bot_with_capabilities(**kwargs) -> Titan:
    """يُنشئ bot مع capabilities محددة (بعد getMe)."""
    bot = make_bot()
    bot._api._me = {
        "id": 1,
        "is_bot": True,
        "can_join_groups": kwargs.get("can_join_groups", False),
        "can_read_all_group_messages": kwargs.get("can_read_all_group_messages", False),
        "supports_inline_queries": kwargs.get("supports_inline_queries", False),
    }
    return bot


async def _noop(ctx): pass
async def _error_handler(ctx, exc): pass


# -------------------------
# HealthFinding model
# -------------------------

class TestHealthFinding:
    def test_attributes(self):
        f = HealthFinding(HealthLevel.ERROR, "NO_HANDLERS", "msg")
        assert f.level == HealthLevel.ERROR
        assert f.code == "NO_HANDLERS"
        assert f.message == "msg"

    def test_repr(self):
        f = HealthFinding(HealthLevel.WARNING, "NO_ERROR_HANDLER", "msg")
        assert "WARNING" in repr(f)
        assert "NO_ERROR_HANDLER" in repr(f)

    def test_equality(self):
        f1 = HealthFinding(HealthLevel.ERROR, "CODE", "msg")
        f2 = HealthFinding(HealthLevel.ERROR, "CODE", "msg")
        assert f1 == f2

    def test_inequality_different_level(self):
        f1 = HealthFinding(HealthLevel.ERROR, "CODE", "msg")
        f2 = HealthFinding(HealthLevel.WARNING, "CODE", "msg")
        assert f1 != f2

    def test_hashable(self):
        f = HealthFinding(HealthLevel.INFO, "CODE", "msg")
        assert isinstance(hash(f), int)

    def test_not_equal_to_non_finding(self):
        f = HealthFinding(HealthLevel.ERROR, "CODE", "msg")
        assert f.__eq__("not a finding") is NotImplemented


# -------------------------
# HealthLevel enum
# -------------------------

class TestHealthLevel:
    def test_values(self):
        assert HealthLevel.ERROR == "ERROR"
        assert HealthLevel.WARNING == "WARNING"
        assert HealthLevel.INFO == "INFO"

    def test_str_comparison(self):
        assert HealthLevel.ERROR == "ERROR"

    def test_ordering_by_name(self):
        levels = [HealthLevel.ERROR, HealthLevel.WARNING, HealthLevel.INFO]
        assert set(levels) == {HealthLevel.ERROR, HealthLevel.WARNING, HealthLevel.INFO}


# -------------------------
# check_no_handlers
# -------------------------

class TestCheckNoHandlers:
    def test_empty_bot_returns_error(self):
        bot = make_bot()
        result = check_no_handlers(bot)
        assert result is not None
        assert result.level == HealthLevel.ERROR
        assert result.code == "NO_HANDLERS"

    def test_bot_with_command_returns_none(self):
        bot = make_bot()
        bot.command("start")(_noop)
        assert check_no_handlers(bot) is None

    def test_bot_with_on_handler_returns_none(self):
        bot = make_bot()
        bot.on("message")(_noop)
        assert check_no_handlers(bot) is None

    def test_bot_with_callback_returns_none(self):
        bot = make_bot()
        bot.callback("yes")(_noop)
        assert check_no_handlers(bot) is None

    def test_bot_with_all_three_returns_none(self):
        bot = make_bot()
        bot.command("start")(_noop)
        bot.on("message")(_noop)
        bot.callback("ok")(_noop)
        assert check_no_handlers(bot) is None


# -------------------------
# check_no_error_handler
# -------------------------

class TestCheckNoErrorHandler:
    def test_no_error_handler_returns_warning(self):
        bot = make_bot()
        result = check_no_error_handler(bot)
        assert result is not None
        assert result.level == HealthLevel.WARNING
        assert result.code == "NO_ERROR_HANDLER"

    def test_with_error_handler_returns_none(self):
        bot = make_bot()
        bot.error_handler(_error_handler)
        assert check_no_error_handler(bot) is None


# -------------------------
# check_inline_capability_unused
# -------------------------

class TestCheckInlineCapabilityUnused:
    def test_no_capabilities_returns_none(self):
        bot = make_bot()
        assert check_inline_capability_unused(bot) is None

    def test_inline_disabled_returns_none(self):
        bot = make_bot_with_capabilities(supports_inline_queries=False)
        assert check_inline_capability_unused(bot) is None

    def test_inline_enabled_no_handler_returns_warning(self):
        bot = make_bot_with_capabilities(supports_inline_queries=True)
        result = check_inline_capability_unused(bot)
        assert result is not None
        assert result.level == HealthLevel.WARNING
        assert result.code == "INLINE_CAPABILITY_UNUSED"

    def test_inline_enabled_with_handler_returns_none(self):
        bot = make_bot_with_capabilities(supports_inline_queries=True)
        bot.on("inline_query")(_noop)
        assert check_inline_capability_unused(bot) is None


# -------------------------
# check_group_capability_unused
# -------------------------

class TestCheckGroupCapabilityUnused:
    def test_no_capabilities_returns_none(self):
        bot = make_bot()
        assert check_group_capability_unused(bot) is None

    def test_can_join_groups_false_returns_none(self):
        bot = make_bot_with_capabilities(can_join_groups=False)
        assert check_group_capability_unused(bot) is None

    def test_can_join_groups_no_handlers_returns_info(self):
        bot = make_bot_with_capabilities(can_join_groups=True)
        result = check_group_capability_unused(bot)
        assert result is not None
        assert result.level == HealthLevel.INFO
        assert result.code == "GROUP_CAPABILITY_UNUSED"

    def test_can_join_groups_with_message_handler_returns_none(self):
        bot = make_bot_with_capabilities(can_join_groups=True)
        bot.on("message")(_noop)
        assert check_group_capability_unused(bot) is None

    def test_can_join_groups_with_new_member_handler_returns_none(self):
        bot = make_bot_with_capabilities(can_join_groups=True)
        bot.on("new_member")(_noop)
        assert check_group_capability_unused(bot) is None

    def test_can_join_groups_with_left_member_handler_returns_none(self):
        bot = make_bot_with_capabilities(can_join_groups=True)
        bot.on("left_member")(_noop)
        assert check_group_capability_unused(bot) is None

    def test_can_join_groups_with_command_returns_none(self):
        bot = make_bot_with_capabilities(can_join_groups=True)
        bot.command("start")(_noop)
        assert check_group_capability_unused(bot) is None

    def test_can_join_groups_with_channel_handler_returns_none(self):
        bot = make_bot_with_capabilities(can_join_groups=True)
        bot.on("channel")(_noop)
        assert check_group_capability_unused(bot) is None


# -------------------------
# check_privacy_mode_disabled_unused
# -------------------------

class TestCheckPrivacyModeDisabledUnused:
    def test_no_capabilities_returns_none(self):
        bot = make_bot()
        assert check_privacy_mode_disabled_unused(bot) is None

    def test_privacy_mode_enabled_returns_none(self):
        bot = make_bot_with_capabilities(can_read_all_group_messages=False)
        assert check_privacy_mode_disabled_unused(bot) is None

    def test_privacy_mode_disabled_no_handler_returns_info(self):
        bot = make_bot_with_capabilities(can_read_all_group_messages=True)
        result = check_privacy_mode_disabled_unused(bot)
        assert result is not None
        assert result.level == HealthLevel.INFO
        assert result.code == "PRIVACY_MODE_DISABLED_UNUSED"

    def test_privacy_mode_disabled_with_message_handler_returns_none(self):
        bot = make_bot_with_capabilities(can_read_all_group_messages=True)
        bot.on("message")(_noop)
        assert check_privacy_mode_disabled_unused(bot) is None


# -------------------------
# run_checks
# -------------------------

class TestRunChecks:
    def test_empty_bot_returns_structural_findings(self):
        bot = make_bot()
        findings = run_checks(bot)
        codes = [f.code for f in findings]
        assert "NO_HANDLERS" in codes
        assert "NO_ERROR_HANDLER" in codes

    def test_empty_bot_no_capabilities_skips_operational(self):
        bot = make_bot()
        findings = run_checks(bot)
        codes = [f.code for f in findings]
        assert "INLINE_CAPABILITY_UNUSED" not in codes
        assert "GROUP_CAPABILITY_UNUSED" not in codes
        assert "PRIVACY_MODE_DISABLED_UNUSED" not in codes

    def test_configured_bot_returns_empty(self):
        bot = make_bot()
        bot.command("start")(_noop)
        bot.error_handler(_error_handler)
        findings = run_checks(bot)
        assert findings == []

    def test_operational_findings_when_capabilities_present(self):
        bot = make_bot_with_capabilities(
            supports_inline_queries=True,
            can_join_groups=True,
        )
        findings = run_checks(bot)
        codes = [f.code for f in findings]
        assert "INLINE_CAPABILITY_UNUSED" in codes
        assert "GROUP_CAPABILITY_UNUSED" in codes

    def test_structural_findings_come_before_operational(self):
        bot = make_bot_with_capabilities(supports_inline_queries=True)
        findings = run_checks(bot)
        codes = [f.code for f in findings]
        structural_codes = {"NO_HANDLERS", "NO_ERROR_HANDLER"}
        operational_codes = {"INLINE_CAPABILITY_UNUSED", "GROUP_CAPABILITY_UNUSED", "PRIVACY_MODE_DISABLED_UNUSED"}
        structural_indices = [i for i, c in enumerate(codes) if c in structural_codes]
        operational_indices = [i for i, c in enumerate(codes) if c in operational_codes]
        if structural_indices and operational_indices:
            assert max(structural_indices) < min(operational_indices)

    def test_returns_list(self):
        bot = make_bot()
        result = run_checks(bot)
        assert isinstance(result, list)

    def test_findings_are_health_finding_instances(self):
        bot = make_bot()
        findings = run_checks(bot)
        for f in findings:
            assert isinstance(f, HealthFinding)


# -------------------------
# bot.health() integration
# -------------------------

class TestBotHealthMethod:
    def test_returns_list(self):
        bot = make_bot()
        assert isinstance(bot.health(), list)

    def test_empty_bot_returns_findings(self):
        bot = make_bot()
        findings = bot.health()
        assert len(findings) >= 1
        assert any(f.code == "NO_HANDLERS" for f in findings)

    def test_configured_bot_returns_empty(self):
        bot = make_bot()
        bot.command("start")(_noop)
        bot.error_handler(_error_handler)
        assert bot.health() == []

    def test_delegates_to_run_checks(self):
        bot = make_bot()
        assert bot.health() == run_checks(bot)

    def test_no_side_effects(self):
        """استدعاء health() لا يُعدّل حالة البوت."""
        bot = make_bot()
        bot.command("start")(_noop)
        commands_before = dict(bot.commands)
        bot.health()
        assert bot.commands == commands_before


# -------------------------
# Public API contract
# -------------------------

class TestPublicAPIContract:
    def test_health_finding_importable_from_titan(self):
        """HealthFinding يجب أن يكون مُصدَّراً من titan مباشرةً."""
        from titan import HealthFinding as HF
        assert HF is HealthFinding

    def test_health_level_importable_from_titan(self):
        """HealthLevel يجب أن يكون مُصدَّراً من titan مباشرةً."""
        from titan import HealthLevel as HL
        assert HL is HealthLevel

    def test_no_circular_import_at_runtime(self):
        """استيراد titan وتشغيل bot.health() لا ينتج circular import."""
        import titan
        bot = titan.Titan("fake-token")
        result = bot.health()
        assert isinstance(result, list)

    def test_health_finding_importable_from_titan_health(self):
        """HealthFinding و HealthLevel مُصدَّران من titan.health أيضاً."""
        from titan.health import HealthFinding as HF, HealthLevel as HL
        assert HF is HealthFinding
        assert HL is HealthLevel
