# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.inspector

يُنتج snapshot وصفية عن الحالة التسجيلية الكاملة للبوت.

المسؤولية:
- تجميع ما تم تسجيله (commands, callbacks, events, middleware, ...)
- إرجاعه كـ BotSnapshot مجمّدة

لا أحكام. لا تقييم. الوصف فقط.
Inspector يصف — Health يُقيّم.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from titan.bot import Titan


@dataclass(frozen=True)
class BotSnapshot:
    """
    Snapshot وصفية عن الحالة التسجيلية الكاملة للبوت.

    تُنتجها `bot.inspect()`. لا تُعدَّل بعد الإنشاء.

    الحقول:
        commands:              أسماء الأوامر المسجلة  (مثال: ("start", "help"))
        callbacks:             قيم callback_data المسجلة  (مثال: ("yes", "no"))
        events:                dict من اسم الحدث إلى عدد الـ handlers  (مثال: {"message": 2})
        middleware_count:      عدد الـ middlewares في السلسلة
        has_error_handler:     True إذا كان error handler مسجلاً
        included_router_count: عدد الـ routers المدمجة عبر bot.include()
        capabilities_available: True إذا كانت bot.capabilities متاحة (بعد bot.run())

    مثال:
        snapshot = bot.inspect()
        print(snapshot.commands)          # ("start", "help")
        print(snapshot.middleware_count)  # 2
        print(snapshot.has_error_handler) # True
    """

    commands: tuple[str, ...]
    callbacks: tuple[str, ...]
    events: Mapping[str, int]
    middleware_count: int
    has_error_handler: bool
    included_router_count: int
    capabilities_available: bool


def build_snapshot(bot: "Titan") -> BotSnapshot:
    """
    يبني BotSnapshot من الحالة الحالية للبوت.

    يقرأ من الـ public API وMiddlewareChain.count فقط.
    لا يلمس private attributes مباشرةً.
    """
    return BotSnapshot(
        commands=tuple(sorted(bot.commands.keys())),
        callbacks=tuple(sorted(bot.callback_handlers.keys())),
        events=MappingProxyType({
            event: len(handlers)
            for event, handlers in bot.handlers.items()
            if handlers
        }),
        middleware_count=bot.middleware_chain.count,
        has_error_handler=bot._error_handler is not None,
        included_router_count=bot.router_count,
        capabilities_available=bot.capabilities is not None,
    )
