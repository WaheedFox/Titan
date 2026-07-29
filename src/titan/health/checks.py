# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.health.checks

فحوصات Project Health — كل دالة تُمثّل فحصاً مستقلاً.

كل دالة:
- تستقبل bot instance
- تُعيد HealthFinding إذا اكتُشفت مشكلة
- تُعيد None إذا كانت الحالة سليمة

الفحوصات مقسّمة لمرحلتين:
- Structural (pre-run): تعمل دائماً، لا تحتاج Telegram
- Operational (post-run): تعمل فقط إذا كانت bot.capabilities متاحة
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from titan.health.models import HealthFinding, HealthLevel

if TYPE_CHECKING:
    from titan.bot import Titan


Check = Callable[["Titan"], "HealthFinding | None"]

# -------------------------
# Structural checks (pre-run)
# -------------------------

def check_no_handlers(bot: "Titan") -> HealthFinding | None:
    """
    ERROR — لا handlers ولا commands ولا callbacks مسجلة.

    البوت يستقبل updates ولا يفعل بها شيئاً.
    """
    if not (bot.commands or bot.handlers or bot.callback_handlers):
        return HealthFinding(
            level=HealthLevel.ERROR,
            code="NO_HANDLERS",
            message=(
                "No handlers, commands, or callbacks are registered. "
                "The bot will receive updates but do nothing."
            ),
        )
    return None


def check_no_error_handler(bot: "Titan") -> HealthFinding | None:
    """
    WARNING — لا error handler مسجّل.

    الاستثناءات داخل الـ handlers تُسجَّل فقط ولا تُعالَج.
    """
    if bot._error_handler is None:
        return HealthFinding(
            level=HealthLevel.WARNING,
            code="NO_ERROR_HANDLER",
            message=(
                "No error handler is registered. "
                "Exceptions raised inside handlers will be logged but not handled."
            ),
        )
    return None


# -------------------------
# Operational checks (post-run — require bot.capabilities)
# -------------------------

def check_inline_capability_unused(bot: "Titan") -> HealthFinding | None:
    """
    WARNING — supports_inline_queries=True بدون أي inline handler.

    Inline Mode مُفعَّل في BotFather لكن لا يوجد ما يستقبل الـ inline queries.
    """
    caps = bot.capabilities
    if caps is None:
        return None
    if caps.supports_inline_queries and "inline_query" not in bot.handlers:
        return HealthFinding(
            level=HealthLevel.WARNING,
            code="INLINE_CAPABILITY_UNUSED",
            message=(
                "Inline queries are enabled in BotFather (supports_inline_queries=True) "
                "but no inline_query handler is registered."
            ),
        )
    return None


def check_group_capability_unused(bot: "Titan") -> HealthFinding | None:
    """
    INFO — can_join_groups=True بدون أي handler للمجموعات.

    البوت يمكنه الانضمام للمجموعات لكن لا يملك handlers لأحداث المجموعات.
    """
    caps = bot.capabilities
    if caps is None:
        return None
    if not caps.can_join_groups:
        return None

    _GROUP_EVENTS = {"message", "new_member", "left_member", "channel"}
    has_group_handler = (
        any(event in bot.handlers for event in _GROUP_EVENTS)
        or bool(bot.commands)
    )
    if not has_group_handler:
        return HealthFinding(
            level=HealthLevel.INFO,
            code="GROUP_CAPABILITY_UNUSED",
            message=(
                "Bot can join groups (can_join_groups=True) "
                "but no group-related handlers are registered "
                "(message, new_member, left_member, or commands)."
            ),
        )
    return None


def check_privacy_mode_disabled_unused(bot: "Titan") -> HealthFinding | None:
    """
    INFO — can_read_all_group_messages=True بدون message handler.

    Privacy mode مُعطَّل (البوت يستقبل كل رسائل المجموعات)
    لكن لا يوجد message handler لمعالجتها.
    """
    caps = bot.capabilities
    if caps is None:
        return None
    if not caps.can_read_all_group_messages:
        return None
    if "message" not in bot.handlers:
        return HealthFinding(
            level=HealthLevel.INFO,
            code="PRIVACY_MODE_DISABLED_UNUSED",
            message=(
                "Privacy mode is disabled (can_read_all_group_messages=True), "
                "meaning the bot receives all group messages, "
                "but no message handler is registered."
            ),
        )
    return None


# ترتيب التشغيل: structural أولاً، ثم operational
ALL_CHECKS: list[Check] = [
    check_no_handlers,
    check_no_error_handler,
    check_inline_capability_unused,
    check_group_capability_unused,
    check_privacy_mode_disabled_unused,
]
