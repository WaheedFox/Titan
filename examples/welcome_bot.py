"""
Welcome bot.

Demonstrates:
- Welcome recipe for greeting new group members
- Combining a recipe with a regular command handler
"""

import os
from titan import Titan
from titan.recipes import Welcome

bot = Titan(token=os.environ["BOT_TOKEN"])

welcome = Welcome("Welcome to the group, {name}! Glad you're here.")


@bot.command("start")
async def on_start(ctx):
    await ctx.reply("Hello! Add me to a group and I'll greet new members.")


@bot.on("new_member")
async def on_join(ctx):
    await welcome(ctx)


bot.run()
