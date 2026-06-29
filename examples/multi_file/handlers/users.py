from titan import Router

router = Router()


@router.command("start")
async def on_start(ctx):
    name = ctx.sender.first_name or "there"
    await ctx.reply(f"Hello, {name}. Use /help to see what I can do.")


@router.command("help")
async def on_help(ctx):
    await ctx.reply(
        "/start — greet\n"
        "/help — this message\n"
        "/language — change language"
    )


@router.on("message")
async def on_message(ctx):
    if ctx.text and not ctx.text.startswith("/"):
        await ctx.reply(f"You said: {ctx.text}")
