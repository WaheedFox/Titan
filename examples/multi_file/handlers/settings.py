from titan import Router, InlineKeyboard

router = Router()

LANGUAGES = {"en": "English", "ar": "العربية", "fr": "Français"}


@router.command("language")
async def on_language(ctx):
    kb = (
        InlineKeyboard()
        .row()
        .button("English", callback_data="lang_en")
        .button("العربية", callback_data="lang_ar")
        .row()
        .button("Français", callback_data="lang_fr")
    )
    await ctx.reply("Choose a language:", reply_markup=kb)


@router.callback("lang_en")
async def set_english(ctx):
    await ctx.answer_callback()
    await ctx.edit(f"Language set to: {LANGUAGES['en']}")


@router.callback("lang_ar")
async def set_arabic(ctx):
    await ctx.answer_callback()
    await ctx.edit(f"Language set to: {LANGUAGES['ar']}")


@router.callback("lang_fr")
async def set_french(ctx):
    await ctx.answer_callback()
    await ctx.edit(f"Language set to: {LANGUAGES['fr']}")
