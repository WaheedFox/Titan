# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.recipes.welcome

The recommended pattern for greeting new group members.

Register a handler for the "new_member" event, access members through
ctx.new_members, and announce with ctx.send() — not ctx.reply(), because
a welcome is a group announcement, not a reply to any specific message.

Usage:
    from titan.recipes import Welcome

    welcome = Welcome("Welcome, {name}!")

    @bot.on("new_member")
    async def on_join(ctx):
        await welcome(ctx)

Template variables:
    {name} — the new member's first name, or "there" if unavailable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from titan.ctx import Context

__all__ = ["Welcome"]

_DEFAULT_MESSAGE = "Welcome, {name}!"


class Welcome:
    """
    The recommended pattern for welcoming new human members to a group.

    Handles ctx.new_members correctly: guards against None, skips bots,
    and sends one message per member via ctx.send().

    Args:
        message: A string template. Use {name} for the member's first name.
                 Defaults to "Welcome, {name}!".

    Example:
        welcome = Welcome("Welcome to the group, {name}!")

        @bot.on("new_member")
        async def on_join(ctx):
            await welcome(ctx)
    """

    def __init__(self, message: str = _DEFAULT_MESSAGE) -> None:
        self.message = message

    async def __call__(self, ctx: "Context") -> None:
        for member in ctx.new_members or []:
            if member.is_bot:
                continue
            await ctx.send(self.message.format(name=member.first_name or "there"))
