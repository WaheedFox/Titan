# تحقيق — API Evolution & Unknown Update Types

**الحالة:** مكتمل  
**المنهجية:** بدء من مشكلة حقيقية في استخدام الأطر الناضجة → تحليل الجذر المعماري → مقارنة مع Titan → قرار.

---

## 1. المشكلة الحقيقية — من الاستخدام الفعلي

### الحدث المحرِّك

أضاف Telegram في أبريل 2024 نوعَي update جديدَين: `message_reaction` و`message_reaction_count`. بعد الإصدار مباشرةً، ظهرت تقارير في مجتمعات python-telegram-bot وaiogram وpyTelegramBotAPI تصف نفس الأعراض:

> *"My message handler is being called with no text and no user — the bot processes hundreds of phantom updates."*

المشكلة لم تكن في الكود — كانت في أن `allowed_updates` الافتراضي يرسل **كل** الأنواع، وكل إطار يُرسّب update لا يعرفه للـ handler الافتراضي.

### النمط المتكرر عبر ثلاثة أطر

| الإطار | السلوك عند update غير معروف |
|---|---|
| **python-telegram-bot ≤ v13** | يصل لـ `MessageHandler(Filters.ALL)` مع `update.message = None` → `AttributeError` صامت |
| **aiogram v2** | يصل لـ handler مرتبط بـ `UpdateType.ANY` أو يُهمَل — غير محدد |
| **pyTelegramBotAPI** | لا يُرسَّب لأي handler — يُهمَل صامتاً |

الحل الجذري في كل إطار كان **حسم سياسة explicit**: إما الإعلان عن `allowed_updates`، أو تحديد سلوك صريح للأنواع غير المعروفة.

---

## 2. الجذر المعماري

المشكلة ليست "الإطار لا يدعم النوع الجديد" — هذا طبيعي. المشكلة هي **غياب سياسة واضحة** للـ update الذي يصل ولا يوجد route له.

الأطر التي واجهت مشاكل كانت تعتمد على **افتراض ضمني**: "إذا لم أُرسّب الـ update لأي handler، فلا شيء يحدث." لكن بنيتها الداخلية (catch-all handler، Filters.ALL، UpdateType.ANY) أنتجت سلوكاً مختلفاً.

الأطر التي لم تواجه مشاكل (aiogram v3 بعد إعادة الكتابة، MTProto clients) كانت تُعلِن صراحةً في startup عن update types المطلوبة، فلا يصل ما لا يُريده المطور أصلاً.

---

## 3. وضع Titan الحالي

### ما يعالجه Titan فعلاً

Titan يبني route صريحاً لثلاثة أنواع فقط من الـ update، رغم أن Telegram Bot API تعرّف أنواعاً إضافية يتغير عددها بمرور الوقت:

| النوع | يُرسَّب كـ |
|---|---|
| `message` | "message" / أمر / semantic event |
| `channel_post` | "channel" |
| `callback_query` | "callback" أو handler محدد |

`_chat_id_from_raw` تقرأ أيضاً: `edited_message`, `edited_channel_post`, `my_chat_member`, `chat_member` — لأغراض per-chat routing فقط — لكن لا routing events مقابلها في `_handle_update`.

### أمثلة على أنواع تصل بلا route (snapshot — لا قائمة شاملة)

```
chosen_inline_result, shipping_query, pre_checkout_query,
poll, poll_answer, my_chat_member, chat_member, chat_join_request,
message_reaction, message_reaction_count,
chat_boost, removed_chat_boost,
business_connection, business_message, edited_business_message,
deleted_business_messages, purchased_paid_media
```

*القائمة أعلاه لحظة زمنية — ستزيد كلما أضاف Telegram أنواعاً جديدة.*

### ماذا يحدث فعلاً مع هذه الأنواع؟

تتبّع تدفق `message_reaction` مثالاً:

```
run_async
  → _chat_id_from_raw(raw)  → None  (message_reaction ليس في القائمة)
  → asyncio.create_task(_handle_update(raw))

_handle_update
  → Update(raw)
      BotApiTranslator:
        message     = raw.get("message")     → None
        channel_post = raw.get("channel_post") → None
        callback_query = raw.get("callback_query") → None

  → dispatch()
      update.channel_post  is None → skip
      update.callback_query is None → skip
      update.get_message()  → None  → no semantic events
      text → None → no command
      ↓
      await self._dispatch("message", ctx)   ← ⚠️ fallthrough
```

**النتيجة:** كل handler مسجَّل على `on("message")` سيُستدعى مع ctx حيث:
- `ctx.text` → None  
- `ctx.user_id` → None  
- `ctx.chat_id` → None  
- `ctx.message` → None  

وهذا بالضبط نفس الأعراض التي أبلغ عنها مستخدمو PTB وaiogram.

### هل الـ fallthrough مقصود؟

لا. `dispatch()` في `_handle_update` تنتهي دائماً بـ `await self._dispatch("message", ctx)` لأنه الـ catch-all لرسائل لا تطابق أي handler أكثر تخصصاً (لا أمر، لا semantic event). هذا الـ catch-all يلتقط أيضاً كل update لا يوجد له route — وهذا استخدام غير مقصود بوضوح.

الدليل: لو كان مقصوداً، لكان موثقاً في CONTRACT أو ADR. لا شيء من هذا موجود.

---

## 4. الجذر في Titan تحديداً

المشكلة ليست في طبقة الترجمة. `BotApiTranslator` أدى وظيفته تماماً: لم يجد `message`، لم يجد `callback_query`، لم يخترع بيانات. أعاد None لأنه لم يجد ما يُترجمه — وهذا سلوك صحيح.

المشكلة بدأت بعد انتهاء الترجمة: **`dispatch()` حملت افتراضاً ضمنياً أن كل update يصلها يجب أن يجد route**. البنية الحالية لـ `dispatch()` تُعبّر عن هذا الافتراض من خلال الـ fallthrough لـ "message" — لكن "message" ليست الجوهر، هي مجرد النتيجة التي وقع عليها الافتراض في التنفيذ الحالي. لو تغيرت بنية `dispatch()` مستقبلاً، الافتراض هو ما يبقى مهماً.

جانب ثانٍ مستقل: Titan لا يُعلِن `allowed_updates` عند بدء الـ polling — يتلقى كل الأنواع افتراضياً.

---

## 5. المقارنة مع القرار المعماري الصحيح

> **ملاحظة منهجية:** الهدف من مقارنة الأطر هنا ليس اختيار سلوك إطار بعينه ولا تقليده. الهدف استخراج المشكلة المعمارية المشتركة التي دفعت كل إطار للتحرك — لأن تكرار المشكلة عبر أطر متعددة يدل على أنها حقيقية وليست خاصة بتنفيذ معين. القرار النهائي يُشتق من عقد Titan وفلسفته، لا من تقليد PTB أو aiogram.

الإطارات التي حلّت هذا استخدمت إحدى مقاربتين:

**أ — Server-side filtering:** تُرسل `allowed_updates` في `getUpdates` لتصفية الأنواع غير المرغوبة في المصدر. aiogram v3 يفعل هذا افتراضياً — يبني قائمة الأنواع من handlers المسجَّلة.

**ب — Client-side explicit policy:** تُعرَّف سياسة صريحة: "update بلا route → X". PTB يعرف TypeHandler للـ catch-all الصريح. pyTelegramBotAPI يُهمل صامتاً.

كلتا المقاربتين تحلّ المشكلة بشرط وحيد: **أن تكون السياسة صريحة ومحددة، لا ضمنية ومستنتجة.**

---

## 6. القرار

### المسألة أ — إصلاح الـ fallthrough إلى "message"

هذا ليس قرار تصميم. الـ fallthrough غير مقصود وله أعراض ضارة موثقة (handler يُستدعى بـ ctx فارغ). يجب إصلاحه بغض النظر عن القرار في المسأتين ب وج.

**قرار: Adopt** — إزالة الـ fallthrough الضمني، بحيث update بلا route لا يصل لأي handler.

> **تمييز ضروري — "بلا route" ≠ "بلا handler"**  
> *بلا route* يعني أن Titan نفسها لا تعرف كيف تُصنّف هذا الـ update ضمن نموذج أحداثها — النوع غير مدعوم أو غير معروف في هذا الإصدار.  
> *بلا handler* يعني أن النوع معروف لـ Titan وتوجد له route، لكن المطور لم يُسجّل handler لهذا الحدث.  
> الحالة الأولى هي موضوع هذا القرار. الحالة الثانية سلوكها موثق منفصلاً ولا علاقة لها بهذا التحقيق.

---

### المسألة ب — سياسة client-side للـ update غير المدعوم أو غير المعروف

الخيارات:

| الخيار | التوافق مع فلسفة Titan |
|---|---|
| تمرير لـ error handler | لا — لا خطأ حدث، هذا تصنيف خاطئ |
| event مخصص `on("unrouted")` | نعم — لكن يضيف تعقيداً لمشكلة تُحَل معمارياً في المصدر |
| drop صريح بسياسة موثقة | نعم — متسق مع "explicit over automatic" |

**قرار: Adapt** — drop صريح: الـ update لا يُمرَّر لأي handler ولا يُعامَل كخطأ ولا يؤثر على الـ polling.

*Implementation note (غير تعاقدية):* يجوز للتنفيذ تسجيلها على DEBUG لتسهيل التشخيص — لكن هذا تفصيل تنفيذي قابل للتغيير مستقبلاً (tracing، telemetry، أو لا شيء) دون المساس بالقرار نفسه.

---

### المسألة ج — server-side filtering عبر `allowed_updates`

الأطر التي تبني `allowed_updates` تلقائياً من قائمة الـ handlers تحتاج معرفة كاملة بكل update type مسجَّل — وهذا يُقيّد Titan لأن `on("message")` يقابل أنواعاً متعددة داخلياً.

الإعلان عن قائمة ثابتة من الأنواع يعني أن أي نوع جديد يضيفه Telegram في المستقبل لن يصل البوت حتى لو أراد المطور معالجته — عكس الهدف.

**قرار: Reject** — Titan لا يُعلن `allowed_updates`. المعالجة الصحيحة client-side (المسألة ب) تكفي. توثيق `allowed_updates` كخيار يدوي للمطوّر كافٍ.

---

## 7. ملخص القرارات

| المسألة | القرار | السبب |
|---|---|---|
| إصلاح fallthrough لـ "message" | **Adopt** | سلوك غير مقصود وله أعراض ضارة موثقة |
| سياسة client-side للـ update غير المدعوم/المعروف | **Adapt** — drop صريح بسياسة موثقة | لا handler، لا خطأ، لا أثر على polling |
| تكوين `allowed_updates` تلقائياً | **Reject** | يُقيّد المرونة ويكسر forward-compatibility |

---

## 8. تمييز مهم — "Unsupported" مقابل "Unknown"

قبل تحديد ما يستلزمه الإصلاح، يجب التمييز بين فئتين مختلفتين:

**Unsupported Update Type**  
نوع *معروف* في Telegram Bot API ومُوثَّق، لكن Titan لم يبنِ route له بقرار واعٍ أو بانتظار. مثال: `poll`, `my_chat_member`, `chat_join_request`. هذا النوع كان موجوداً وقت بناء Titan — الغياب كان اختياراً أو تأجيلاً.

**Unknown Update Type**  
نوع أضافه Telegram *بعد* بناء إصدار Titan — لم يكن موجوداً في المرجع المستخدم. مثال: `purchased_paid_media` (2024), `message_reaction` (2024). لا قرار اتُّخذ بشأنه لأنه لم يكن معروفاً.

**لماذا التمييز مهم هندسياً:**  
السياسة الصحيحة متطابقة لكلا النوعين — drop صريح — لكن الأسباب مختلفة:
- *Unsupported*: قرار "لا ندعم هذا حتى الآن" يجب أن يكون صريحاً، لا ضمنياً عبر fallthrough.
- *Unknown*: لا يمكن لأي إطار التنبؤ بالمستقبل — السياسة العامة هي السياج الوحيد.

---

## 9. ما يستلزمه الإصلاح (بدون كود — للتوثيق فقط)

**مبدأ الفصل بين المسؤوليات:**

`BotApiTranslator` مسؤوليته الوحيدة هي الترجمة. سياسة التعامل مع الـ update غير المدعوم أو غير المعروف تُملَك بالكامل من طبقة التنفيذ — `dispatch()` داخل `_handle_update`. هذه الطبقة تعرف ماذا رُتِّب له route، وهي المكان الصحيح لقرار "ماذا أفعل بما لا route له."

**في `dispatch()` داخل `_handle_update`:**  
تحتاج exit صريح قبل الـ fallthrough لـ "message". هذا القرار يعيش هنا — لا في الـ Translator، ولا في أي طبقة أخرى.

**في CONTRACT.md:**  
ثلاثة بنود فقط تخص العقد — وكيفية التسجيل تفصيل تنفيذي خارج نطاقه:

1. Updates غير المدعومة وغير المعروفة لا تُمرَّر لأي handler.
2. لا تُعتبر خطأ ولا تستدعي الـ error handler.
3. لا تؤثر على سير الـ polling.

كيف يختار التنفيذ تسجيلها — إن اختار — ليس جزءاً من العقد. التسجيل على debug level مسموح به ولكنه غير مضمون.

**ملاحظة:** الإصلاح تصحيح في Execution Model، لا إضافة ميزة. لا تغيير في الـ Public API — المطور لن يلاحظ فرقاً في الـ interface، فقط في السلوك: handler لن يُستدعى بعد الآن بـ ctx فارغ.
