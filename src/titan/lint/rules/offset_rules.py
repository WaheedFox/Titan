from __future__ import annotations

from typing import TYPE_CHECKING

from titan.lint.findings import LintFinding
from titan.validation import _is_async

if TYPE_CHECKING:
    from titan.bot import Titan

_LEVEL = "WARNING"


def check_on_offset(bot: "Titan") -> list[LintFinding]:
    """
    TITAN_LINT_003 — on_offset يجب ألا تكون async callable.

    public API يرفض دالة async قبل بدء polling. يبقى هذا الفحص
    للحالات الداخلية التي قد تضع callable غير صالح مباشرةً على bot.

    يدعم الدوال async وcallable objects ذات __call__ async.
    """
    fn = getattr(bot, "_on_offset", None)
    if fn is None:
        return []
    if _is_async(fn):
        return [
            LintFinding(
                level=_LEVEL,
                code="TITAN_LINT_003",
                message="on_offset is an async callable; Titan requires a synchronous callback.",
                hint=(
                    "on_offset must be a synchronous callable. "
                    "Public run() and run_async() reject async callbacks before "
                    "polling starts. Use a sync function and schedule async work separately."
                ),
            )
        ]
    return []
