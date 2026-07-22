# Titan

إطار عمل Python غير متزامن لبناء بوتات Telegram.

بسيط. واضح. لا يتغير تحت قدميك.

[![CI](https://github.com/WaheedFox/Titan/actions/workflows/ci.yml/badge.svg)](https://github.com/WaheedFox/Titan/actions/workflows/ci.yml)

> 🌐 [English version → README.en.md](README.en.md)

---

## التثبيت

```bash
pip install titanx
```

---

## البداية السريعة

```python
from titan import Titan

bot = Titan("YOUR_TOKEN")

@bot.command("start")
async def start(ctx):
    await ctx.reply("أهلاً! أنا جاهز.")

bot.run()
```

---

## المفاهيم الأساسية

Titan توفر خمس طرق للتفاعل مع بوتك. كل طريقة لها دور محدد.

| الطريقة | الدور |
|---|---|
| `bot.on(event)` | استقبال أي حدث Telegram بالاسم |
| `bot.command(name)` | استقبال أمر محدد مثل `/start` |
| `bot.callback(data)` | استقبال ضغطة زر inline محددة |
| `bot.middleware` | تشغيل منطق قبل كل handler |
| `bot.telegram` | استدعاء Telegram API مباشرة |

### `bot.on` — استقبال الأحداث

```python
@bot.on("message")
async def on_message(ctx):
    await ctx.reply("وصلتني رسالتك.")

@bot.on("callback")
async def on_callback(ctx):
    await ctx.answer_callback()

@bot.on("channel")
async def on_channel(ctx):
    pass  # منشورات القناة
```

الأحداث المدعومة: `message`، `callback`، `channel`، `new_member`، `left_member`.

### `bot.command` — استقبال الأوامر

```python
@bot.command("start")
async def start(ctx):
    await ctx.reply("مرحباً!")

@bot.command("help")
async def help(ctx):
    await ctx.reply("أرسل أي رسالة للبدء.")
```

### `bot.callback` — استقبال أزرار Inline

```python
@bot.callback("confirm")
async def on_confirm(ctx):
    await ctx.answer_callback("تم التأكيد.")

@bot.callback("cancel")
async def on_cancel(ctx):
    await ctx.answer_callback("تم الإلغاء.")
```

إذا لم يوجد handler مطابق لـ `callback_data`، يُحوَّل التحديث إلى `bot.on("callback")`.

### `bot.middleware` — منطق ما قبل التنفيذ

يعمل قبل كل handler. استخدمه للـ logging، التحقق من الصلاحيات، ومنع الـ spam.

```python
@bot.middleware
async def guard(ctx, next):
    print(f"تحديث من المستخدم {ctx.user_id}")
    await next()
```

- `await next()` ← يكمل التنفيذ للـ handler
- `return` بدون استدعاء `next()` ← يوقف التحديث هنا

### `bot.telegram` — الوصول المباشر للـ API

للعمليات خارج سياق الرسالة الواحدة.

```python
await bot.telegram.send_message(chat_id=123, text="رسالة مباشرة.")
await bot.telegram.get_chat_member(chat_id=123, user_id=456)
await bot.telegram.pin_message(chat_id=123, message_id=789)
```

`bot.telegram` يتجاوز الـ middleware والـ ctx — للاستدعاء المباشر والصريح فقط.

---

## السياق (`ctx`)

كل handler يستلم كائن `ctx` يحمل بيانات التحديث الحالي وأدوات التفاعل.

### البيانات

```python
ctx.user_id        # int | None — معرّف المستخدم
ctx.chat_id        # int | None — معرّف الشات
ctx.text           # str | None — نص الرسالة
ctx.callback_data  # str | None — بيانات الزر المضغوط
ctx.is_banned      # bool — هل المستخدم في قائمة الحظر

ctx.sender         # بيانات المرسل: .id, .first_name, .username, .is_bot
ctx.chat           # بيانات الشات: .id, .type, .title, .username
ctx.message        # بيانات الرسالة: .id, .text
```

### الأفعال

```python
await ctx.reply("مرحباً")
await ctx.send("مرحباً")
await ctx.edit("نص محدّث")        # داخل callback handlers فقط
await ctx.delete_message()
await ctx.ban_user()
await ctx.leave()
await ctx.answer_callback("تم")
await ctx.fetch_permissions()      # يفحص صلاحية البوت في الشات
```

### الوصول الخام

```python
ctx.raw  # JSON الكامل القادم من Telegram
```

وجود `ctx.raw` مضمون وجزء من العقد. لكن *بنيته* تتبع Telegram API وقد تتغير — استخدمه فقط عند الحاجة لبيانات غير متاحة عبر `ctx` مباشرة.

---

## أزرار Inline

```python
from titan import Titan, InlineKeyboard

bot = Titan("YOUR_TOKEN")

@bot.command("start")
async def start(ctx):
    keyboard = (
        InlineKeyboard()
        .row()
        .button("نعم ✅", callback_data="confirm")
        .button("لا ❌", callback_data="cancel")
    )
    await ctx.reply("هل أنت متأكد؟", reply_markup=keyboard)

@bot.callback("confirm")
async def on_confirm(ctx):
    await ctx.answer_callback("تم التأكيد!")

@bot.callback("cancel")
async def on_cancel(ctx):
    await ctx.answer_callback("تم الإلغاء.")

bot.run()
```

---

## Router

يتيح لك تقسيم الـ handlers عبر ملفات متعددة ودمجها في البوت الرئيسي.

```python
# admin.py
from titan import Router

router = Router()

@router.command("ban")
async def ban(ctx):
    await ctx.ban_user()
    await ctx.reply("تم الحظر.")

@router.callback("confirm_ban")
async def confirm_ban(ctx):
    await ctx.answer_callback()
```

```python
# main.py
from titan import Titan
from admin import router

bot = Titan("YOUR_TOKEN")
bot.include(router)
bot.run()
```

Router يدعم: `on()`، `command()`، `callback()`.

Router لا يدعم: `middleware()` أو `include()` المتداخل.

---

## الأسماء البديلة (Aliases)

تتيح لك تعريف أسماء مخصصة لـ methods الـ ctx عبر `AliasMap` من `titan.extras`.

```python
from titan.extras.alias import AliasMap

aliases = AliasMap()
aliases.register("قل", "reply")
aliases.register("اطرد", "ban_user")

bot.middleware(aliases.as_middleware())

@bot.on("message")
async def handler(ctx):
    await ctx.قل("مرحباً")   # نفس ctx.reply()
    await ctx.اطرد()          # نفس ctx.ban_user()
```

الاسم الأصلي يبقى متاحاً بدون أي تغيير. Aliases طبقة تسمية فقط — لا تغير في السلوك.

`AliasMap` كيان مستقل — يمكن مشاركته بين routers متعددة:

```python
router1.middleware(aliases.as_middleware())
router2.middleware(aliases.as_middleware())
```

---

## نظام الحظر

```python
bot.banned_users  # set[int] — تديرها أنت بالكامل

bot.banned_users.add(user_id)
bot.banned_users.discard(user_id)
```

عندما يكون المستخدم في `bot.banned_users`، تكون `ctx.is_banned` قيمتها `True` قبل تشغيل الـ middleware. Titan لا تتصرف تلقائياً — الـ middleware تقرر ماذا تفعل.

```python
@bot.middleware
async def guard(ctx, next):
    if ctx.is_banned:
        return
    await next()
```

---

## تشغيل البوت

```python
# متزامن — الأنسب في أغلب الحالات
bot.run()

# غير متزامن — عندما تُدير event loop خاص بك
import asyncio
asyncio.run(bot.run_async())
```

كلا الأسلوبين ينفّذان نفس المنطق الداخلي.

---

## حواف حادة معروفة

---

### مشاكل موثَّقة (سلوك غير صحيح)

#### `bot.include()` — حالة جزئية عند التعارض

إذا احتوى الـ `Router` على handlers وأمر يتعارض مع أمر مسجَّل مسبقاً، فإن `bot.include()` تُضيف الـ handlers أولاً ثم تُرمى `TitanError`. الـ mutation لا تُعكس.

```python
@bot.command("start")
async def existing(ctx): ...

router = Router()

@router.on("message")
async def handler(ctx): ...  # يُضاف للبوت

@router.command("start")
async def conflict(ctx): ...  # يُسبب TitanError

bot.include(router)
# TitanError مُرماة — لكن handler("message") أُضيف بالفعل
```

**التعامل معه:** تحقق من التعارضات قبل استدعاء `include()`. إذا وقع الخطأ، أعد تهيئة البوت بدلاً من المتابعة.

---

#### `bot.callback("")` — لا يُنفَّذ أبداً

التسجيل بـ `callback_data` فارغة (`""`) ينجح بدون خطأ، لكن الـ handler لا يُستدعى أبداً عند وصول update يحمل `callback_data=""`. المنطق الداخلي يتعامل مع `""` كغياب البيانات.

```python
@bot.callback("")        # يُسجَّل بنجاح
async def handler(ctx):  # لا يُنفَّذ أبداً
    ...
```

**التعامل معه:** لا تستخدم سلسلة فارغة كـ `callback_data`. استخدم قيمة وصفية دائماً مثل `"noop"` أو `"skip"`.

---

### ضمانات غائبة (سلوك صحيح لكن بلا حماية)

هذه ليست أخطاء — Titan تتصرف بشكل متسق، لكنها لا تحمي من أنماط الاستخدام الخاطئة التالية:

**استدعاء `next()` مرتين في middleware**
يؤدي إلى تنفيذ كل handler مرتين. Titan لا تكتشف هذا. اتبع قاعدة: استدعاء `next()` مرة واحدة فقط.

**تسجيل أمر بشرطة مائلة: `bot.command("/start")`**
يُسجَّل بنجاح لكن لا يُطابق أي update أبداً. الاسم الصحيح هو `"start"` بدون شرطة مائلة.

**تسجيل `error_handler` أكثر من مرة**
الأخير فقط يبقى — الأول يُحذف بصمت. لا يوجد تحذير.

**`InlineButton` بدون `callback_data` ولا `url`**
Titan تقبل الزر. Telegram API سترفضه عند إرسال الرسالة.

**`AliasMap.register()` باسم يطابق خاصية موجودة في `ctx`**
إذا اخترت اسماً يطابق خاصية موجودة مثل `text` أو `chat_id`، ستُكتَب الخاصية الأصلية بصمت.

```python
aliases.register("text", "reply")
# ctx.text الآن تُشير إلى reply — الخاصية الأصلية اختفت
```

استخدم أسماء لا تتعارض مع خصائص `ctx` الموجودة.

**تمرير `async def` إلى `on_offset`**
`on_offset` تتوقع دالة عادية (synchronous). تمرير `async def` ينتج كوروتيناً لا يُنفَّذ أبداً، بدون خطأ أو تحذير.

```python
async def save(offset):   # خطأ — دالة async
    ...

bot.run(on_offset=save)   # الكوروتين يُنشأ ويُتجاهل عند كل تحديث
```

استخدم دالة عادية، وابدأ event loop منفصلاً إذا احتجت async داخلها.

---

## الفلسفة

Titan إطار عمل مبني على الاستقرار.

- الأشياء البسيطة تبقى بسيطة.
- الأشياء المعقدة ممكنة عبر `bot.telegram`.
- الـ API لا يتغير بدون إصدار جديد.
- لا سلوك خفي. لا magic. لا سباق ميزات.

---

## الرخصة

**W.A.S.L v1.0** — رخصة واصل التجارية للبرمجيات
راجع ملف [LICENSE](LICENSE) للاطلاع على الشروط الكاملة.

---

© Copyright by **Waheed**. All rights reserved.
*(Alien's Zone ~ building real robots to help humanity thrive and stay alive! ^^)*
