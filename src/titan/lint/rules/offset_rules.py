from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from titan.lint.findings import LintFinding

if TYPE_CHECKING:
    from titan.bot import Titan

_LEVEL = "WARNING"


def check_on_offset(bot: "Titan") -> list[LintFinding]:
    """
    TITAN_LINT_003 — on_offset يجب ألا تكون async callable.

    دالة async تُمرَّر كـ on_offset تُنشئ coroutine لا تُنفَّذ أبداً
    (لا تُستدعى بـ await). النتيجة: offset لا يُحفَظ أبداً بصمت تام.

    تُكتشَف فقط بعد run() حيث يُخزَّن _on_offset على bot.
    """
    fn = getattr(bot, "_on_offset", None)
    if fn is None:
        return []
    if asyncio.iscoroutinefunction(fn):
        return [
            LintFinding(
                level=_LEVEL,
                code="TITAN_LINT_003",
                message="on_offset is an async function whose coroutine is never awaited.",
                hint=(
                    "on_offset must be a synchronous callable. "
                    "Async functions passed here create a coroutine object "
                    "that Titan calls without await, so it silently does nothing. "
                    "Use a sync function and schedule async work separately."
                ),
            )
        ]
    return []
