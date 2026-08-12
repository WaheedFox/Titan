import pytest

from titan.bot import Titan
from titan.lint import LintFinding
from titan.router import Router


def make_bot() -> Titan:
    return Titan("dummy-token")


def codes(findings: list[LintFinding]) -> list[str]:
    return [f.code for f in findings]


class TestLintFinding:
    def test_is_frozen_dataclass(self):
        f = LintFinding(level="WARNING", code="TITAN_LINT_001", message="msg", hint="fix")
        with pytest.raises(Exception):
            f.code = "other"

    def test_str_includes_level_code_message_hint(self):
        f = LintFinding(level="WARNING", code="TITAN_LINT_001", message="bad name", hint="fix it")
        s = str(f)
        assert "WARNING" in s
        assert "TITAN_LINT_001" in s
        assert "bad name" in s
        assert "fix it" in s

    def test_hint_is_never_empty(self):
        f = LintFinding(level="WARNING", code="X", message="m", hint="h")
        assert f.hint


class TestLintReturnsEmptyWhenClean:
    def test_no_findings_for_clean_bot(self):
        bot = make_bot()

        @bot.command("start")
        async def on_start(ctx): ...

        @bot.callback("yes")
        async def on_yes(ctx): ...

        assert bot.lint() == []

    def test_returns_list(self):
        assert isinstance(make_bot().lint(), list)


class TestLINT001CommandCase:
    def test_uppercase_command_triggers_finding(self):
        bot = make_bot()

        @bot.command("Start")
        async def h(ctx): ...

        findings = bot.lint()
        assert "TITAN_LINT_001" in codes(findings)

    def test_mixedcase_command_triggers_finding(self):
        bot = make_bot()

        @bot.command("myCommand")
        async def h(ctx): ...

        assert "TITAN_LINT_001" in codes(bot.lint())

    def test_lowercase_command_no_finding(self):
        bot = make_bot()

        @bot.command("start")
        async def h(ctx): ...

        assert "TITAN_LINT_001" not in codes(bot.lint())

    def test_multiple_uppercase_commands_each_reported(self):
        bot = make_bot()

        @bot.command("Start")
        async def h1(ctx): ...

        @bot.command("Stop")
        async def h2(ctx): ...

        lint_001 = [f for f in bot.lint() if f.code == "TITAN_LINT_001"]
        assert len(lint_001) == 2

    def test_finding_message_contains_command_name(self):
        bot = make_bot()

        @bot.command("MyCmd")
        async def h(ctx): ...

        finding = next(f for f in bot.lint() if f.code == "TITAN_LINT_001")
        assert "MyCmd" in finding.message

    def test_finding_hint_suggests_lowercase(self):
        bot = make_bot()

        @bot.command("START")
        async def h(ctx): ...

        finding = next(f for f in bot.lint() if f.code == "TITAN_LINT_001")
        assert "start" in finding.hint or "lowercase" in finding.hint.lower()


class TestLINT002CallbackData:
    def test_empty_string_callback_data_triggers_finding(self):
        bot = make_bot()
        bot.callback_handlers[""] = lambda ctx: None
        assert "TITAN_LINT_002" in codes(bot.lint())

    def test_whitespace_only_callback_data_triggers_finding(self):
        bot = make_bot()
        bot.callback_handlers["   "] = lambda ctx: None
        assert "TITAN_LINT_002" in codes(bot.lint())

    def test_valid_callback_data_no_finding(self):
        bot = make_bot()

        @bot.callback("confirm")
        async def h(ctx): ...

        assert "TITAN_LINT_002" not in codes(bot.lint())

    def test_finding_hint_nonempty(self):
        bot = make_bot()
        bot.callback_handlers[""] = lambda ctx: None
        finding = next(f for f in bot.lint() if f.code == "TITAN_LINT_002")
        assert finding.hint


class TestLINT003OnOffsetAsync:
    def test_async_on_offset_triggers_finding_after_assignment(self):
        bot = make_bot()

        async def bad_offset(n): ...

        bot._on_offset = bad_offset
        assert "TITAN_LINT_003" in codes(bot.lint())

    def test_sync_on_offset_no_finding(self):
        bot = make_bot()

        def good_offset(n): ...

        bot._on_offset = good_offset
        assert "TITAN_LINT_003" not in codes(bot.lint())

    def test_no_on_offset_no_finding(self):
        bot = make_bot()
        assert "TITAN_LINT_003" not in codes(bot.lint())

    def test_finding_hint_explains_coroutine_issue(self):
        bot = make_bot()

        async def bad(n): ...

        bot._on_offset = bad
        finding = next(f for f in bot.lint() if f.code == "TITAN_LINT_003")
        assert "await" in finding.hint.lower() or "async" in finding.hint.lower()


class TestLINT010EmptyRouter:
    def test_empty_router_triggers_finding(self):
        bot = make_bot()
        router = Router()
        bot.include(router)
        assert "TITAN_LINT_010" in codes(bot.lint())

    def test_router_with_handlers_no_finding(self):
        bot = make_bot()
        router = Router()

        @router.command("ping")
        async def h(ctx): ...

        bot.include(router)
        assert "TITAN_LINT_010" not in codes(bot.lint())

    def test_router_with_callbacks_only_no_finding(self):
        bot = make_bot()
        router = Router()

        @router.callback("ok")
        async def h(ctx): ...

        bot.include(router)
        assert "TITAN_LINT_010" not in codes(bot.lint())

    def test_router_with_on_handler_no_finding(self):
        bot = make_bot()
        router = Router()

        @router.on("message")
        async def h(ctx): ...

        bot.include(router)
        assert "TITAN_LINT_010" not in codes(bot.lint())

    def test_two_empty_routers_both_reported(self):
        bot = make_bot()
        bot.include(Router())
        bot.include(Router())
        lint_010 = [f for f in bot.lint() if f.code == "TITAN_LINT_010"]
        assert len(lint_010) == 2

    def test_finding_hint_nonempty(self):
        bot = make_bot()
        bot.include(Router())
        finding = next(f for f in bot.lint() if f.code == "TITAN_LINT_010")
        assert finding.hint


class TestLINT011ExcessiveFanOut:
    def _register_n_handlers(self, bot: Titan, n: int, event: str = "message") -> None:
        for i in range(n):
            async def h(ctx, _i=i): ...
            bot.handlers.setdefault(event, []).append(h)

    def test_eleven_handlers_triggers_finding(self):
        bot = make_bot()
        self._register_n_handlers(bot, 11)
        assert "TITAN_LINT_011" in codes(bot.lint())

    def test_ten_handlers_no_finding(self):
        bot = make_bot()
        self._register_n_handlers(bot, 10)
        assert "TITAN_LINT_011" not in codes(bot.lint())

    def test_finding_contains_event_name_and_count(self):
        bot = make_bot()
        self._register_n_handlers(bot, 12, event="message")
        finding = next(f for f in bot.lint() if f.code == "TITAN_LINT_011")
        assert "message" in finding.message
        assert "12" in finding.message

    def test_finding_hint_suggests_routers(self):
        bot = make_bot()
        self._register_n_handlers(bot, 11)
        finding = next(f for f in bot.lint() if f.code == "TITAN_LINT_011")
        assert "router" in finding.hint.lower() or "Router" in finding.hint

    def test_different_events_reported_separately(self):
        bot = make_bot()
        self._register_n_handlers(bot, 11, event="message")
        self._register_n_handlers(bot, 11, event="channel")
        lint_011 = [f for f in bot.lint() if f.code == "TITAN_LINT_011"]
        assert len(lint_011) == 2


class TestLintOrdering:
    def test_findings_sorted_by_code(self):
        bot = make_bot()

        @bot.command("Start")
        async def h(ctx): ...

        bot.callback_handlers[""] = lambda ctx: None
        bot.include(Router())

        found_codes = codes(bot.lint())
        assert found_codes == sorted(found_codes)

    def test_all_findings_are_warnings_in_v1(self):
        bot = make_bot()

        @bot.command("Bad")
        async def h(ctx): ...

        bot.callback_handlers[""] = lambda ctx: None
        for finding in bot.lint():
            assert finding.level == "WARNING"


class TestLintDoesNotModifyBot:
    def test_lint_does_not_change_commands(self):
        bot = make_bot()

        @bot.command("Start")
        async def h(ctx): ...

        before = dict(bot.commands)
        bot.lint()
        assert bot.commands == before

    def test_lint_callable_multiple_times(self):
        bot = make_bot()

        @bot.command("Start")
        async def h(ctx): ...

        r1 = bot.lint()
        r2 = bot.lint()
        assert r1 == r2
