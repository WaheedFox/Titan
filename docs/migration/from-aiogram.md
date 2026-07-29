# الانتقال من aiogram إلى Titan

---

## الفرق الفلسفي الرئيسي

aiogram مبني على **الأنواع كمحور للـ routing**: النوع في signature الـ handler يحدد ما يُشغّله (`message: Message` = يُشغَّل بالرسائل، `query: CallbackQuery` = يُشغَّل بالـ callbacks). المرونة تأتي من Magic Filters (`F.text`, `F.data == 'x'`) على مستوى التسجيل.

Titan مبني على **event strings صريحة**: `@bot.on('message')`, `@bot.command('start')`, `@bot.callback('yes')`. لا Dependency Injection، لا Filter objects. الـ handler دائماً يستقبل `ctx: Context` بغض النظر عن نوع الـ update.

**الفرق الأعمق:** aiogram يُفكر في الـ handler على أنه "دالة تستقبل نوعاً محدداً وتتصرف عليه". Titan يُفكر فيه على أنه "دالة تعالج حدثاً محدداً من خلال سياق موحّد".

---

## خريطة المقابلات

| aiogram | Titan |
|---|---|
| `Dispatcher` | `Titan` |
| `Bot(token)` | داخل `Titan(token)` — لا تحتاجه منفصلاً |
| `@dp.message(Command('start'))` | `@bot.command('start')` |
| `@dp.message(F.text)` | `@bot.on('message')` |
| `@dp.callback_query(F.data == 'yes')` | `@bot.callback('yes')` |
| `@dp.errors()` | `@bot.error_handler` |
| `message: Message` في الـ handler | `ctx: Context` |
| `message.answer('hi')` | `await ctx.reply('hi')` |
| `message.bot.send_message(chat_id, 'hi')` | `await ctx.send('hi')` |
| `Router()` مع nesting | `Router()` — flat فقط، بلا nesting |
| `await dp.start_polling(bot)` | `bot.run()` |

---

## الأشياء التي ستنكسر

### 1. لا Dependency Injection — لا أنواع في الـ signature

```python
# aiogram — النوع يحدد ما يُستقبل
async def start(message: Message, bot: Bot, state: FSMContext):
    await message.answer("hi")

# Titan — ctx فقط، دائماً
async def start(ctx: Context):
    await ctx.reply("hi")
```

أي dependency تريد توفيره في الـ handler (db session, config, ...) — مرّره عبر `bot.middleware()` أو أنشئه مباشرةً في الـ handler.

---

### 2. لا Magic Filters — الفلترة داخل الـ handler

```python
# aiogram
@dp.message(F.text.startswith('!'))
async def handle_bang(message: Message): ...

# Titan
@bot.on('message')
async def handle_bang(ctx):
    if ctx.text and ctx.text.startswith('!'):
        ...  # منطقك هنا
```

---

### 3. Middleware واحدة على مستوى update — لا outer/inner

```python
# aiogram — outer middleware لكل update types، inner لنوع محدد
@dp.update.outer_middleware()
async def auth_middleware(handler, event, data):
    ...

@dp.message.middleware()
async def message_only_middleware(handler, event, data):
    ...

# Titan — سلسلة واحدة على كل update
@bot.middleware
async def my_middleware(ctx, next):
    # يُشغَّل على كل update
    await next()
```

إذا احتجت سلوكاً مختلفاً لأنواع updates مختلفة، افحص داخل الـ middleware:

```python
@bot.middleware
async def selective_middleware(ctx, next):
    if ctx.callback_data is not None:
        # هذا callback query
        pass
    else:
        # هذا رسالة عادية
        pass
    await next()
```

---

### 4. الـ callback_data بالـ exact match فقط

```python
# aiogram — يدعم prefix matching وregex
@dp.callback_query(F.data.startswith('item_'))
async def handle_item(query: CallbackQuery):
    item_id = query.data.split('_')[1]

# Titan — exact string فقط في @bot.callback()
# للـ dynamic patterns استخدم on('callback'):
@bot.on('callback')
async def handle_item(ctx):
    if ctx.callback_data and ctx.callback_data.startswith('item_'):
        item_id = ctx.callback_data.split('_')[1]
        ...
```

---

### 5. الـ Router لا يدعم الـ nesting

```python
# aiogram — routers متداخلة
main_router = Router()
admin_router = Router()
main_router.include_router(admin_router)

# Titan — flat فقط
admin_router = Router()
bot.include(admin_router)  # مباشرةً للبوت
```

إذا كنت تستخدم nesting لتطبيق group-level filters، حرّك تلك الـ checks لـ middleware أو داخل الـ handlers.

---

## الأشياء التي لا يوجد لها مقابل مباشر

### FSMContext / State Machine

aiogram's FSM لا يوجد في Titan.

للحوارات البسيطة: استخدم `titan.extras.ask.AskManager`.

```python
from titan.extras import AskManager
ask = AskManager()
bot.middleware(ask.as_middleware())

@bot.command('register')
async def register(ctx):
    name = await ask(ctx, "ما اسمك؟")
    age = await ask(ctx, "كم عمرك؟")
    await ctx.reply(f"مرحباً {name}، عمرك {age}.")
```

للحوارات المعقدة مع states متعددة: صمّم state machine بنفسك وخزّن الحالة في Redis أو SQLite.

### Magic Filter (F)

لا مقابل مباشر في Titan. الفلترة تحدث داخل الـ handler body.

### Dependency Injection

aiogram يُحقن الـ dependencies تلقائياً عبر signature. في Titan:
- استخدم `bot.middleware()` لحقن الـ dependencies في `ctx` عبر `setattr`
- أو أنشئ الـ dependency مباشرةً في الـ handler
