from __future__ import annotations

from typing import TYPE_CHECKING

from titan.lint.findings import LintFinding

if TYPE_CHECKING:
    from titan.bot import Titan

_LEVEL = "WARNING"
_FAN_OUT_THRESHOLD = 10


def check_empty_routers(bot: "Titan") -> list[LintFinding]:
    """
    TITAN_LINT_010 — Router مضمّن بدون أي handlers مسجّلة.

    Router فارغ يُضاف عبر bot.include() لا يضيف أي سلوك ويمثّل
    عادةً خطأ في تهيئة المشروع.
    """
    findings: list[LintFinding] = []
    for router in getattr(bot, "_included_router_objects", []):
        is_empty = (
            len(router.commands) == 0
            and len(router.handlers) == 0
            and len(router.callback_handlers) == 0
        )
        if is_empty:
            findings.append(
                LintFinding(
                    level=_LEVEL,
                    code="TITAN_LINT_010",
                    message="A Router was included via bot.include() but contains no handlers.",
                    hint=(
                        "Either register handlers on this Router before including it, "
                        "or remove the bot.include() call if the Router is unused."
                    ),
                )
            )
    return findings


def check_fan_out(bot: "Titan") -> list[LintFinding]:
    """
    TITAN_LINT_011 — عدد handlers مفرط على نفس نوع الحدث.

    أكثر من 10 handlers على حدث واحد (مثل "message") يشير إلى أن
    المسؤوليات غير مقسّمة — يُفضَّل توزيعها على routers منفصلة
    أو معالجتها في middleware للمخاوف المشتركة.

    العتبة: 10 handlers — ثابت في v1.
    """
    findings: list[LintFinding] = []
    for event, handlers in bot.handlers.items():
        count = len(handlers)
        if count > _FAN_OUT_THRESHOLD:
            findings.append(
                LintFinding(
                    level=_LEVEL,
                    code="TITAN_LINT_011",
                    message=(
                        f"Event '{event}' has {count} registered handlers "
                        f"(threshold: {_FAN_OUT_THRESHOLD})."
                    ),
                    hint=(
                        f"Consider splitting '{event}' handlers across dedicated "
                        "Routers, or use middleware for concerns shared across all handlers."
                    ),
                )
            )
    return findings
