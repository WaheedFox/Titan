"""
Usage Validation Bot — titanx==1.0.0a1

بوت حقيقي يمارس كل الـ API الأساسية:
- bot.command()
- bot.on()
- bot.callback() + InlineKeyboard
- bot.middleware
- Router + bot.include()
- bot.alias()
- error_handler
- bot.telegram (direct call)
"""

import os
import logging
from titan import Titan, InlineKeyboard, InlineButton, Router
from titan.extras.alias import AliasMap  # [UVF-01] bot.alias() غير موجودة — يجب استخدام AliasMap يدوياً

logging.basicConfig(level=logging.INFO)

# ── تهيئة البوت ──────────────────────────────────────────────────────────────
bot = Titan(os.environ["BOT_TOKEN"])

# alias: نسمّي reply → say  لتجربة الـ alias layer
# [UVF-01] الـ README يوثّق bot.alias("say", "reply") لكنها غير موجودة على كلاس Titan
# الـ API الفعلية: AliasMap + as_middleware()
aliases = AliasMap()
aliases.register("say", "reply")

# ── Middleware: logging بسيط ──────────────────────────────────────────────────
@bot.middleware
async def logger(ctx, next):
    uid = ctx.user_id
    logging.getLogger("titan.usage").info("update from user=%s", uid)
    await next()

# تسجيل alias middleware بعد logger
bot.middleware(aliases.as_middleware())

# ── Error handler ─────────────────────────────────────────────────────────────
@bot.error_handler
async def on_error(ctx, exc):
    logging.getLogger("titan.usage").error("unhandled error: %s", exc)
    await ctx.reply("حدث خطأ غير متوقع.")

# ── Commands ──────────────────────────────────────────────────────────────────
@bot.command("start")
async def on_start(ctx):
    name = ctx.sender.first_name if ctx.sender else "مستخدم"
    await ctx.say(f"أهلاً {name}! أنا بوت التحقق من Titan.\n\nاختر أمراً:")

@bot.command("help")
async def on_help(ctx):
    await ctx.reply(
        "/start — البداية\n"
        "/help — المساعدة\n"
        "/menu — قائمة تفاعلية\n"
        "/info — معلومات المحادثة\n"
        "/ping — اختبار الاتصال"
    )

@bot.command("menu")
async def on_menu(ctx):
    kb = (
        InlineKeyboard()
        .row()
        .button("✅ تأكيد", callback_data="confirm")
        .button("❌ إلغاء", callback_data="cancel")
        .row()
        .button("ℹ️ معلومات", callback_data="info")
    )
    await ctx.reply("اختر:", reply_markup=kb)

@bot.command("info")
async def on_info(ctx):
    chat = ctx.chat
    lines = [
        f"user_id: {ctx.user_id}",
        f"chat_id: {ctx.chat_id}",
        f"chat type: {chat.type if chat else 'N/A'}",
        f"username: {ctx.username or '—'}",
    ]
    await ctx.reply("\n".join(lines))

@bot.command("ping")
async def on_ping(ctx):
    await ctx.reply("pong 🏓")

# ── Callbacks ─────────────────────────────────────────────────────────────────
@bot.callback("confirm")
async def on_confirm(ctx):
    await ctx.answer_callback("تم التأكيد ✅")
    await ctx.edit("تم اختيار: تأكيد.")

@bot.callback("cancel")
async def on_cancel(ctx):
    await ctx.answer_callback("تم الإلغاء.")
    await ctx.edit("تم اختيار: إلغاء.")

@bot.callback("info")
async def on_info_cb(ctx):
    await ctx.answer_callback()
    await ctx.edit(f"chat_id: {ctx.chat_id}\nuser_id: {ctx.user_id}")

# ── on("message"): echo ───────────────────────────────────────────────────────
@bot.on("message")
async def on_message(ctx):
    if ctx.text:
        await ctx.reply(f"قلت: {ctx.text}")

# ── Router: وحدة منفصلة لأوامر المجموعات ─────────────────────────────────────
group_router = Router()

@group_router.on("new_member")
async def on_join(ctx):
    name = ctx.new_members[0].first_name if ctx.new_members else "عضو جديد"
    await ctx.reply(f"مرحباً {name}! 👋")

@group_router.on("left_member")
async def on_leave(ctx):
    name = ctx.left_member.first_name if ctx.left_member else "عضو"
    await ctx.reply(f"وداعاً {name}.")

bot.include(group_router)

# ── تشغيل ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run()
