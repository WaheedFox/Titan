from __future__ import annotations

from typing import TYPE_CHECKING

from titan.lint.findings import LintFinding
from titan.lint.rules.callback_rules import check_callback_data
from titan.lint.rules.command_rules import check_command_names
from titan.lint.rules.offset_rules import check_on_offset
from titan.lint.rules.router_rules import check_empty_routers, check_fan_out

if TYPE_CHECKING:
    from titan.bot import Titan


def run_lint(bot: "Titan") -> list[LintFinding]:
    """
    نقطة الدخول الوحيدة للمحرك — تجمع نتائج جميع القواعد وتُرتّبها.

    الترتيب: حسب الـ code رقمياً (LINT_001 → LINT_002 → ...).
    يُستدعى فقط من bot.lint() — لا استخدام مباشر.
    """
    findings: list[LintFinding] = []
    findings.extend(check_command_names(bot))
    findings.extend(check_callback_data(bot))
    findings.extend(check_on_offset(bot))
    findings.extend(check_empty_routers(bot))
    findings.extend(check_fan_out(bot))
    return sorted(findings, key=lambda f: f.code)
