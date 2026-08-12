from __future__ import annotations

from typing import TYPE_CHECKING

from titan.lint.findings import LintFinding

if TYPE_CHECKING:
    from titan.bot import Titan

_LEVEL = "WARNING"


def check_callback_data(bot: "Titan") -> list[LintFinding]:
    """
    TITAN_LINT_002 — callback_data يجب ألا تكون فارغة أو whitespace فقط.

    callback_data فارغة لا تُميَّز عن غيرها في Telegram وتجعل routing
    غير متوقع.
    """
    findings: list[LintFinding] = []
    for data in bot.callback_handlers:
        if not data.strip():
            findings.append(
                LintFinding(
                    level=_LEVEL,
                    code="TITAN_LINT_002",
                    message=(
                        f"Callback data {data!r} is empty or whitespace-only."
                    ),
                    hint=(
                        "callback_data must be a non-empty, non-whitespace string. "
                        "Use a descriptive identifier like 'confirm_delete' or 'menu_back'."
                    ),
                )
            )
    return findings
