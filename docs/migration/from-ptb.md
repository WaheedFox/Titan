# الانتقال من python-telegram-bot إلى Titan

---

## الفرق الفلسفي الرئيسي

PTB مبني على فكرة **التسجيل الضمني عبر الأنواع والـ filters**: تُنشئ Handler object، تُحدد شروطه (نوع الرسالة، regex، حالة المحادثة)، ثم تضيفه لـ Application. الـ routing logic موزعة على Handler objects.

Titan مبني على فكرة **التسجيل الصريح عبر الـ decorators**: `@bot.command('start')`، `@bot.on('message')`، `@bot.callback('yes')`. الـ routing logic واضحة من اسم الـ decorator مباشرةً.

**النتيجة:** Titan أقل مرونةً في الـ filtering، لكنه أوضح في التتبع. إذا رأيت `@bot.command('start')` تعرف فوراً ما الذي يُشغّل هذا الـ handler.

---

## خريطة المقابلات

| PTB | Titan |
|---|---|
| `Application` | `Titan` |
| `app.add_handler(CommandHandler('start', fn))` | `@bot.command('start')` |
| `app.add_handler(MessageHandler(filters.TEXT, fn))` | `@bot.on('message')` |
| `app.add_handler(CallbackQueryHandler(fn, pattern=r'^yes$'))` | `@bot.callback('yes')` |
| `update: Update, context: ContextTypes.DEFAULT_TYPE` | `ctx: Context` |
| `update.message.reply_text('hi')` | `await ctx.reply('hi')` |
| `context.bot.send_message(chat_id, 'hi')` | `await ctx.send('hi')` |
| `app.add_error_handler(fn)` | `@bot.error_handler` |
| `app.run_polling()` | `bot.run()` |

---

## الأشياء التي ستنكسر

### 1. handler واحد فقط لكل command

```python
# PTB — يعمل: يُشغّل fn1 أولاً، fn2 إذا لم يُعالَج
app.add_handler(CommandHandler('start', fn1), group=0)
app.add_handler(CommandHandler('start', fn2), group=1)

# Titan — يرمي TitanError عند التسجيل الثاني
@bot.command('start')
async def fn1(ctx): ...

@bot.command('start')  # ❌ TitanError: Command 'start' is already registered
async def fn2(ctx): ...
```

**الحل:** دمج المنطق في handler واحد، أو استخدام `bot.middleware()` للمنطق المشترك.

---

### 2. لا filter objects — الفلترة داخل الـ handler

```python
# PTB
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fn))

# Titan — لا filters، تحقق داخل الـ handler
@bot.on('message')
async def fn(ctx):
    if ctx.text is None:
        return
    if ctx.text.startswith('/'):
        return
    # ... منطقك هنا
```

---

### 3. الـ callback_data بالـ exact match فقط

```python
# PTB — يدعم regex
app.add_handler(CallbackQueryHandler(fn, pattern=r'^item_\d+$'))

# Titan — exact string فقط
@bot.callback('item_1')
async def fn1(ctx): ...

@bot.callback('item_2')
async def fn2(ctx): ...

# أو route عام:
@bot.on('callback')
async def handle_items(ctx):
    if ctx.callback_data and ctx.callback_data.startswith('item_'):
        item_id = ctx.callback_data.split('_')[1]
        ...
```

---

### 4. السياق الموحّد

```python
# PTB
async def fn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("hi")
    user_id = update.effective_user.id
    data = context.user_data  # PTB in-memory storage

# Titan
async def fn(ctx: Context):
    await ctx.reply("hi")
    user_id = ctx.user_id
    # لا context.user_data — استخدم تخزينك الخاص
```

---

## الأشياء التي لا يوجد لها مقابل مباشر

### ConversationHandler

PTB's `ConversationHandler` لا يوجد في Titan.

للحوارات البسيطة (سؤال → جواب): استخدم `titan.extras.ask.AskManager`.

```python
from titan.extras import AskManager
ask = AskManager()
bot.middleware(ask.as_middleware())

@bot.command('start')
async def start(ctx):
    name = await ask(ctx, "ما اسمك؟")
    await ctx.reply(f"مرحباً {name}!")
```

للحوارات المعقدة مع state machine: حافظ على الحالة في تخزينك الخاص (Redis, SQLite, dict).

### context.user_data / context.chat_data

PTB يوفر in-memory storage تلقائياً. Titan لا يوفره. استخدم تخزينك الخاص وعرّضه عبر middleware إذا احتجت.

### ConversationHandler.END / states

لا مقابل مباشر. هذه PTB-specific abstraction.
