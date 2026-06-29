"""
Moderation bot.

Demonstrates:
- middleware guard using bot.banned_users
- /ban and /unban commands (Telegram-level via ctx.ban_user)
- explicit permission check before deleting a message
- inline keyboard with confirm/cancel flow
"""

import os
from titan import Titan, InlineKeyboard, TitanError

bot = Titan(token=os.environ["BOT_TOKEN"])


@bot.middleware
async def guard(ctx, next):
    if ctx.is_banned:
        return
    await next()


@bot.command("start")
async def on_start(ctx):
    await ctx.reply("Moderation bot active.")


@bot.command("ban")
async def on_ban(ctx):
    target = ctx.message.raw.get("reply_to_message", {}).get("from", {}).get("id")
    if target is None:
        await ctx.reply("Reply to a message to ban that user.")
        return

    bot.banned_users.add(target)
    await ctx.ban_user(target)
    await ctx.reply(f"User {target} banned.")


@bot.command("unban")
async def on_unban(ctx):
    target = ctx.message.raw.get("reply_to_message", {}).get("from", {}).get("id")
    if target is None:
        await ctx.reply("Reply to a message to unban that user.")
        return

    bot.banned_users.discard(target)
    await ctx.reply(f"User {target} removed from local ban list.")


@bot.command("delete")
async def on_delete(ctx):
    await ctx.refresh_permissions()

    if not ctx.can_delete:
        await ctx.reply("I do not have permission to delete messages here.")
        return

    kb = (
        InlineKeyboard()
        .row()
        .button("Delete", callback_data="confirm_delete")
        .button("Cancel", callback_data="cancel_delete")
    )
    await ctx.reply("Delete this message?", reply_markup=kb)


@bot.callback("confirm_delete")
async def on_confirm_delete(ctx):
    await ctx.answer_callback()
    await ctx.delete_message()


@bot.callback("cancel_delete")
async def on_cancel_delete(ctx):
    await ctx.answer_callback("Cancelled.")
    await ctx.edit("Deletion cancelled.")


bot.run()
