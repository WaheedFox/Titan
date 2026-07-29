"""
Multi-file bot using Router.

Structure:
    main.py          — bot setup, middleware, run
    handlers/
        users.py     — /start, /help, general messages
        settings.py  — /language, inline keyboard flow
"""

import os
from titan import Titan

from handlers.users import router as users_router
from handlers.settings import router as settings_router

bot = Titan(token=os.environ["BOT_TOKEN"])


@bot.middleware
async def log_updates(ctx, next):
    chat = ctx.chat_id
    text = ctx.text or f"[{ctx.callback_data or 'non-text'}]"
    print(f"[{chat}] {text}")
    await next()


bot.include(users_router)
bot.include(settings_router)

bot.run()
