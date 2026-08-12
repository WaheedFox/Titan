# تحقيق — Conversation State & Multi-step Flows

**الحالة:** مكتمل  
**المنهجية:** بدء من مشكلة حقيقية في استخدام الأطر الناضجة → تحليل الجذر المعماري → مقارنة مع Titan → قرار.

---

## 1. المشكلة الحقيقية — من الاستخدام الفعلي

### الأعراض المتكررة في PTB وaiogram

أكثر الشكاوى تكراراً في مجتمعات python-telegram-bot وaiogram عبر GitHub Issues وReddit وStack Overflow:

**في python-telegram-bot:**
- *"My bot freezes after restart — all conversations are lost."*
- *"Two users in the same group trigger each other's conversation state."*
- *"I send /cancel but the bot keeps asking the same question."*
- *"My handler receives `None` for `update.message` inside a ConversationHandler."*
- *"Nested ConversationHandlers don't work — inner handler never resolves."*
- *"The bot stops responding after a user sends messages too quickly."*

**في aiogram:**
- *"Commands get swallowed silently while in FSM state."*
- *"FSM doesn't work in groups — all users share the same state."*
- *"State is never cleared after the conversation ends — memory leak."*
- *"Too much boilerplate — 3 classes and 5 registrations for a 2-step flow."*
- *"Invalid state transition causes messages to disappear with no error."*

الأعراض متباينة، لكنها تصف نفس المشكلة المعمارية.

---

## 2. الجذر المعماري

### نموذج التنفيذ الأصلي: per-message، stateless

PTB وaiogram — ككل إطارات Telegram — بُنيا على نموذج تنفيذ محدد:

> كل رسالة تصل → تُمرَّر لـ handler مسجَّل → ينتهي تنفيذه → لا شيء يبقى في الذاكرة.

هذا النموذج **صحيح** لأوامر بسيطة: `/start`، `/help`، `/status`. كل رسالة مستقلة، كل handler لا يحتاج سياقاً من ما سبقها.

لكن عندما يحتاج البوت **تدفقاً متعدد الخطوات** — "ما اسمك؟" ثم "كم عمرك؟" ثم "من أين أنت؟" — يصطدم هذا النموذج بمشكلة جوهرية:

> **كيف تكتب منطقاً تسلسلياً في نموذج تنفيذ لا يتذكر ما قبله؟**

### الحل التقليدي: state machine خارجية

الإجابة التي اختارها PTB وaiogram: **تخزين "أين نحن" خارجياً** وتحويل المرسلات المستقبلية لـ handler مختلف بناءً على هذه الحالة.

```
ConversationHandler:
  state[user_id] = ASK_NAME
  next message → handler_ask_age
  state[user_id] = ASK_AGE
  next message → handler_ask_city
  ...
```

هذا ليس تسلسلاً — هذا **إيهام بالتسلسل** عبر:
1. تخزين "رقم الخطوة" خارج الكود.
2. تحويل الرسائل المستقبلية بناءً على هذا الرقم.
3. كتابة كل خطوة كـ handler منفصل مسجَّل مسبقاً.

### لماذا هذا يُفشل؟

الـ state machine الخارجية تحمل تكلفة معمارية مركّبة:

| المشكلة | السبب الجذري |
|---|---|
| تجمّد بعد الإعادة تشغيل | الحالة في الذاكرة، ليست في الكود |
| تداخل مستخدمين في المجموعات | المفتاح `user_id` فقط بدون `chat_id` في الإعدادات الافتراضية |
| ابتلاع الأوامر في الحالات | الـ state machine لا تعرف "أي رسائل خارجة عن التدفق" |
| التداخل (race conditions) | رسالتان متتاليتان سريعتان تُقرآن نفس الحالة قبل تحديثها |
| نسيان مسح الحالة | لا lifetime طبيعي للـ state — يجب مسحها يدوياً |
| فشل الـ nested handlers | الـ state machine لا تتداخل — تتعارض |

الجذر الموحّد لكل هذه المشاكل: **محاولة تمثيل coroutine (حساب متسلسل معلَّق) باستخدام state machine (حالة خارجية + جدول توجيه).**

هذا impedance mismatch — ليس قرار تصميم سيئاً بقدر ما هو حل workaround لقيد المنصة.

---

## 3. مقارنة الجذر مع Titan

### ملاحظة منهجية

المقارنة هنا ليست لاختيار سلوك إطار معين، بل لاستخراج الجذر المعماري المشترك والتحقق مما إذا كان موجوداً في Titan. القرار النهائي يبقى منبثقاً من عقد Titan وفلسفته.

### ask() في Titan: ماذا يفعل بالضبط؟

```python
@bot.command("register")
async def register(ctx):
    name = await ask(ctx, "ما اسمك؟")
    age  = await ask(ctx, "كم عمرك؟")
    city = await ask(ctx, "من أين أنت؟")
    await ctx.reply(f"مرحباً {name} ({age}) من {city}")
```

الآلية:
1. `ask()` تُرسل الرسالة، تُنشئ `asyncio.Future`، تُعلّق الـ coroutine (`await future`).
2. `AskManager` middleware تعترض الرسالة التالية من نفس `(chat_id, user_id)`.
3. Middleware تُحلّ الـ Future بنص الرسالة.
4. الـ coroutine تستأنف من حيث توقفت.

**الحالة ليست خارجية — الحالة هي call stack الـ coroutine نفسها.**

لا state machine. لا handler مسجَّل لكل خطوة. لا جدول توجيه. التسلسل حقيقي، لا مُموَّه.

### هل الجذر المعماري موجود في Titan؟

| المشكلة الجذرية في PTB/aiogram | وضعها في Titan |
|---|---|
| تمثيل coroutine بـ state machine | **غير موجود** — ask() هو coroutine حقيقي |
| تخزين حالة الخطوة خارج الكود | **غير موجود** — الحالة هي call stack |
| كل خطوة handler منفصل | **غير موجود** — الكود تسلسلي طبيعي |
| مفتاح التوجيه `state[user_id]` | **غير موجود** — Future مرتبطة بـ `(chat_id, user_id)` |
| race condition في تحديث الحالة | **غير موجود** — per-chat queue + asyncio.Future atomic |
| نسيان مسح الحالة | **غير موجود** — Future لها lifetime طبيعي في coroutine |

---

## 4. ماذا يغطي ask()؟

### الأنماط التي تعمل بشكل طبيعي

**تسلسل خطي:**
```python
name = await ask(ctx, "ما اسمك؟")
age  = await ask(ctx, "كم عمرك؟")
```
الـ Python control flow هو التسلسل. لا إضافة مطلوبة.

**تفريع بناءً على الإجابة:**
```python
answer = await ask(ctx, "هل أنت مشترك؟ نعم/لا")
if answer.lower() == "نعم":
    plan = await ask(ctx, "أي خطة؟")
else:
    await ctx.reply("يمكنك الاشتراك عبر /subscribe")
```
الـ Python `if/else` هو التفريع. لا state enum، لا handler منفصل.

**حلقة تكرار مع تحقق:**
```python
while True:
    answer = await ask(ctx, "أدخل رقماً:")
    if answer.isdigit():
        break
    await ctx.reply("أرجو إدخال رقم صحيح فقط.")
```
الـ Python `while` هي الحلقة. لا registered retry handler.

**محادثات متوازية لمستخدمين مختلفين:**
المفتاح `(chat_id, user_id)` يعزل كل محادثة تلقائياً. مستخدمان في نفس المجموعة لهما Futures مستقلة.

**الإلغاء من خارج التدفق (`erase()`):**
إذا أرسل المطور `await bot.erase_user(user_id)`، تُلغى جميع Futures المعلّقة لهذا المستخدم. الـ coroutine تستقبل `CancelledError` — السلوك المتوقع من asyncio.

### القيود الموثَّقة والمصرَّح بها

**لا persistence:**
`ask()` يوثّق صراحةً: "No persistence — pending asks are lost on bot restart."
هذا قرار نطاق، ليس ثغرة معمارية. المطور الذي يحتاج persistence يُدير الحالة خارج Titan بوعي.

**لا timeout مدمج:**
لا يوجد `timeout=` في توقيع `ask()`. لكن `asyncio.wait_for()` يعمل بشكل طبيعي:
```python
try:
    answer = await asyncio.wait_for(ask(ctx, "..."), timeout=60)
except asyncio.TimeoutError:
    await ctx.reply("انتهت المهلة.")
```
هذا ليس غياب ميزة — هو تفويض للـ standard library الذي يحل المشكلة بشكل أصح.

---

## 5. الحالة التي تستحق النظر: الأوامر أثناء ask()

### الوضع الحالي

عندما يكون `ask()` معلّقاً وأرسل المستخدم `/cancel`:
- الـ middleware تعترض الرسالة (لأنها رسالة نصية، ليست callback).
- تُحلّ الـ Future بالنص الحرفي `"/cancel"`.
- الـ coroutine تستأنف وتحصل على `"/cancel"` كإجابة.
- لا يصل `/cancel` لأي command handler.

المطور يرى `"/cancel"` في المتغير، ويتعامل معه يدوياً:
```python
answer = await ask(ctx, "ما اسمك؟")
if answer.startswith("/"):
    await ctx.reply("تم إلغاء العملية.")
    return
```

### هل هذا ثغرة معمارية؟

المقارنة مع الأطر الأخرى:

| الإطار | سلوك الأمر أثناء محادثة |
|---|---|
| **PTB ConversationHandler** | يُرسَّب للـ fallbacks إذا سُجِّل، وإلا يُهمَل صامتاً |
| **aiogram FSM** | يُبتلع من الـ state — لا يصل لأي command handler إلا بتكوين خاص |
| **Titan ask()** | يصل للـ coroutine كإجابة نصية — المطور يتحقق منه |

سلوك Titan **أكثر شفافية من الاثنين**: لا ابتلاع صامت، لا حاجة لتسجيل fallback handlers. المطور يقرر بوعي ماذا يفعل بالإجابة.

هذا ليس ثغرة — هو موقف تصميمي. الـ coroutine تمتلك التدفق، وهي من تقرر ما "يعني" كل إجابة.

الغياب القصدي لـ "interrupt pattern" مدمج هو نتيجة طبيعية لنقل المسؤولية من الإطار للمطور — وهي فلسفة Titan.

---

## 6. حالة ask() مع الرسائل غير النصية

### الوضع الحالي

إذا أرسل المستخدم صورة أو ملصقاً أو موقعاً أثناء `ask()`:
- الـ middleware تعترض الرسالة.
- تُحلّ الـ Future بـ `ctx.message.text or ""` — أي سلسلة فارغة.
- الـ coroutine تستأنف بـ `""`.

هذا موثَّق ضمنياً في `test_ask_returns_empty_string_for_non_text_message`.

### هل هذا ثغرة؟

**ليس ثغرة معمارية.** ask() صُمِّمت كآلية Q&A نصية صريحة. الرسائل غير النصية تُحلّ بـ `""` لأن ask() لا تعرف ما "تفعله" بصورة أو موقع — وهذا صحيح.

استخدام حالة "اجمع الصور من المستخدم" مختلف جوهرياً: هو ليس Q&A، بل مستقبل محتوى. هذا نمط مختلف كلياً عن "اسألني سؤالاً وانتظر إجابة".

إذا ظهرت الحاجة الحقيقية، فهي تستدعي آلية منفصلة — ليس توسيع ask().

---

## 7. ملخص المقارنة

| السؤال | الجواب |
|---|---|
| هل الجذر المعماري (state machine خارجية) موجود في Titan؟ | **لا** — ask() هو coroutine حقيقي، لا state machine |
| هل ask() يمنع المشاكل التي أنتجتها ConversationHandler وFSM؟ | **نعم** — المشكلة نفسها غير موجودة |
| هل هناك حالات حقيقية لا يغطيها ask()؟ | القيود موجودة (persistence، timeout، رسائل غير نصية) لكنها قرارات نطاق، لا ثغرات معمارية |
| هل يجب Adopt أي شيء من ConversationHandler أو FSM؟ | **لا** |

---

## 8. ما تُظهره مقارنة الأطر

الإضافة المفيدة من هذا التحقيق ليست "نقل ميزة من PTB" — بل فهم **لماذا** ask() هو جواب أصح معمارياً:

ConversationHandler وFSM ظهرا لأن المطورين كانوا يريدون كتابة:
```python
name = input("ما اسمك؟")
age  = input("كم عمرك؟")
```

لكن الإطار لا يدعم ذلك — كل `input()` handler منفصل. فاخترع الإطار state machine تُوهم بالتسلسل.

Titan لا تحتاج هذه الحيلة لأن `asyncio.Future` تتيح `await` حقيقياً — وهذا ما كان المطورون يريدونه منذ البداية.

---

## 9. القرار

### المسائل المطروحة:

| المسألة | القرار |
|---|---|
| هل نتبنّى ConversationHandler أو FSM pattern؟ | **Reject** |
| هل ask() يعالج الجذر المعماري الصحيح؟ | نعم — لا تغيير مطلوب |
| هل القيود الحالية (persistence، timeout، non-text) تستدعي Adopt/Adapt؟ | **Reject** — قرارات نطاق، تُعالَج مستقلاً عند ظهور حاجة حقيقية |

### الجواب الهندسي:

الجذر المعماري الذي أجبر PTB وaiogram على بناء ConversationHandler وFSM — أي محاولة تمثيل تسلسل منطقي في نموذج تنفيذ per-message stateless — **غير موجود في Titan**.

ask() لا يُضيف state machine فوق نموذج stateless. هو يُغيّر النموذج نفسه: الـ coroutine **هي** الحالة، والـ `await` **هو** التعليق.

القيود الموجودة في ask() (لا persistence، لا timeout مدمج، رسائل غير نصية تُحلّ بـ "") هي حدود نطاق واعية — لا ثغرات معمارية. أي توسيع لها يستحق دراسة مستقلة عند ظهور حاجة حقيقية موثَّقة.

**القرار النهائي: Reject** — لا Adopt، لا Adapt، لا تغيير في التصميم الحالي.
