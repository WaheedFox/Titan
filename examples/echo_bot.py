import os
from titan import Titan

bot = Titan(token=os.environ["BOT_TOKEN"])


@bot.command("start")
async def on_start(ctx):
    await ctx.reply(f"Hello, {ctx.sender.first_name}.")


@bot.command("help")
async def on_help(ctx):
    await ctx.reply("/start — greet\n/help — this message")


@bot.on("message")
async def on_message(ctx):
    if ctx.text:
        await ctx.reply(ctx.text)


bot.run()
