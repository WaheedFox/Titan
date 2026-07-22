from __future__ import annotations

from typing import TYPE_CHECKING

from titan.lint.findings import LintFinding

if TYPE_CHECKING:
    from titan.bot import Titan

_LEVEL = "WARNING"


def check_command_names(bot: "Titan") -> list[LintFinding]:
    """
    TITAN_LINT_001 — أسماء الأوامر يجب أن تكون lowercase.

    Telegram نفسها case-insensitive، لكن اتفاقية Titan تفرض lowercase
    لضمان الاتساق والقراءة في قواعد الكود.
    """
    findings: list[LintFinding] = []
    for name in bot.commands:
        if name != name.lower():
            findings.append(
                LintFinding(
                    level=_LEVEL,
                    code="TITAN_LINT_001",
                    message=f"Command '{name}' uses non-lowercase characters.",
                    hint=(
                        "Use lowercase command names. Telegram is case-insensitive "
                        f"but Titan convention requires lowercase. "
                        f"Rename to '{name.lower()}'."
                    ),
                )
            )
    return findings
