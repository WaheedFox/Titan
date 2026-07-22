# الانتقال من pyTelegramBotAPI (telebot) إلى Titan

---

## الفرق الفلسفي الرئيسي

telebot مبني على **الـ global bot object**: تُنشئ `bot = TeleBot(token)` ثم تُسجّل عليه كل شيء عبر decorators. الملفات الأخرى تستورد `bot` من الملف الرئيسي لتسجيل handlers عليه.

Titan مبني على نفس فكرة الـ decorators لكن مع **Router كأداة تنظيم**: كل ملف يُنشئ `router = Router()` الخاص به ويُسجّل عليه handlers، ثم `bot.include(router)` في الملف الرئيسي. لا حاجة لاستيراد `bot` في كل ملف.

**الفرق الآخر:** telebot يُمرّر الـ Telegram object مباشرةً للـ handler. Titan يُمرّر `ctx: Context` موحَّد يحتوي على البيانات والأدوات معاً — لا حاجة لـ `bot.send_message(chat_id, ...)` من خارج الـ handler.

---

## خريطة المقابلات

| telebot | Titan |
|---|---|
| `TeleBot(token)` | `Titan(token)` |
| `@bot.message_handler(commands=['start'])` | `@bot.command('start')` |
| `@bot.message_handler(content_types=['text'])` | `@bot.on('message')` |
| `@bot.callback_query_handler(func=lambda c: c.data == 'yes')` | `@bot.callback('yes')` |
| `message: types.Message` في الـ handler | `ctx: Context` |
| `bot.reply_to(message, 'hi')` | `await ctx.reply('hi')` |
| `bot.send_message(chat_id, 'hi')` | `await ctx.send('hi')` |
| `bot.delete_message(chat_id, msg_id)` | `await ctx.delete_message()` |
| `bot.polling()` | `bot.run()` |
| try/except في كل handler | `@bot.error_handler` |

---

## الأشياء التي ستنكسر

### 1. تسجيل أمر واحد بعدة أسماء

```python
# telebot — قائمة من الأوامر في handler واحد
@bot.message_handler(commands=['start', 'begin', 'go'])
def start(message): ...

# Titan — كل أمر بـ decorator منفصل
@bot.command('start')
async def start(ctx): ...

@bot.command('begin')
async def begin(ctx): ...
```

إذا كانت جميعها تؤدي نفس الوظيفة، استدعِ دالة مشتركة:

```python
async def _handle_start(ctx):
    await ctx.reply("مرحباً!")

@bot.command('start')
async def start(ctx): await _handle_start(ctx)

@bot.command('begin')
async def begin(ctx): await _handle_start(ctx)
```

---

### 2. لا global bot object في الملفات الأخرى

```python
# telebot — استيراد bot في كل ملف
# handlers/admin.py
from main import bot

@bot.message_handler(commands=['ban'])
def ban(message): ...

# Titan — Router في كل ملف
# handlers/admin.py
from titan import Router

router = Router()

@router.command('ban')
async def ban(ctx): ...

# main.py
from handlers.admin import router
bot.include(router)
```

---

### 3. الـ callback_data بالـ exact match فقط

```python
# telebot — دالة lambda للفلترة
@bot.callback_query_handler(func=lambda c: c.data.startswith('item_'))
def handle_item(call): ...

# Titan — exact string لـ @bot.callback()
# للـ dynamic patterns استخدم on('callback'):
@bot.on('callback')
async def handle_item(ctx):
    if ctx.callback_data and ctx.callback_data.startswith('item_'):
        item_id = ctx.callback_data.split('_')[1]
        ...
```

---

### 4. handlers غير async — Titan يتطلب async

```python
# telebot — sync
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "hi")

# Titan — يجب أن تكون async دائماً
@bot.command('start')
async def start(ctx):
    await ctx.reply("hi")
```

---

### 5. الأخطاء بـ try/except محلي → error handler مركزي

```python
# telebot — error handling محلي في كل handler
@bot.message_handler(commands=['start'])
def start(message):
    try:
        # ... منطقك
    except Exception as e:
        bot.reply_to(message, f"خطأ: {e}")

# Titan — handler مركزي واحد
@bot.error_handler
async def on_error(ctx, exc):
    await ctx.reply(f"حدث خطأ غير متوقع.")
    # log(exc)
```

---

## الأشياء التي لا يوجد لها مقابل مباشر

### telebot.types.*

telebot يُمرّر Telegram objects مباشرةً (`types.Message`, `types.CallbackQuery`). في Titan:
- `ctx.text` بدلاً من `message.text`
- `ctx.user_id` بدلاً من `message.from_user.id`
- `ctx.callback_data` بدلاً من `call.data`
- `ctx.message.raw` إذا احتجت الـ raw dict للبيانات غير المُغطّاة

### non-stop polling

```python
# telebot
bot.polling(non_stop=True)

# Titan — Titan يُعيد المحاولة تلقائياً مع exponential backoff
bot.run()
```

لا حاجة لـ non_stop — Titan يتعامل مع أخطاء الشبكة تلقائياً.

### middleware

telebot لا يملك middleware system. Titan يوفر `@bot.middleware` — وهذا مكسب، لا تكلفة.
