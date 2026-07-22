# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.extras.alias

Opt-in method shortcuts on ctx, applied via middleware.

Usage:
    from titan.extras.alias import AliasMap

    aliases = AliasMap()
    aliases.register("say", "reply")
    bot.middleware(aliases.as_middleware())
"""

from __future__ import annotations

from typing import Any

from titan.errors import TitanError
from titan.ctx import Context


class AliasMap:
    """
    طبقة التسمية الاختيارية في Titan.

    تسمح للمطور بتعريف أسماء بديلة لـ methods موجودة في Context.
    لا تغير أي سلوك — mapping فقط من اسم إلى اسم.

    القواعد:
    - الأسماء الأصلية في ctx تبقى ثابتة بدون أي تغيير
    - الاسم الهدف يجب أن يكون موجوداً في Context وإلا TitanError
    - لا magic، لا wrapping، لا interception
    """

    def __init__(self) -> None:
        self._map: dict[str, str] = {}

    def register(self, alias: str, target: str) -> None:
        if hasattr(Context, alias):
            raise TitanError(
                f"Cannot create alias '{alias}' → '{target}': "
                f"'{alias}' is already an attribute of Context. "
                "Choose a name that does not conflict with existing ctx attributes "
                "(e.g. avoid 'text', 'reply', 'send', 'chat_id', 'user_id', and all other "
                "Context properties and methods)."
            )
        if not hasattr(Context, target):
            raise TitanError(
                f"Cannot create alias '{alias}' → '{target}': "
                f"'{target}' does not exist in Context. "
                "Use the exact method name as it appears in ctx "
                "(e.g. 'reply', 'send', 'edit', 'ban_user', 'delete_message')."
            )
        self._map[alias] = target

    def apply(self, ctx: Context) -> None:
        for alias, target in self._map.items():
            setattr(ctx, alias, getattr(ctx, target))

    def as_middleware(self):
        """
        Return a middleware function that applies aliases to every ctx.

            bot.middleware(aliases.as_middleware())
        """
        alias_map = self

        async def _middleware(ctx: Any, next: Any) -> None:
            alias_map.apply(ctx)
            await next()

        return _middleware


__all__ = ["AliasMap"]
