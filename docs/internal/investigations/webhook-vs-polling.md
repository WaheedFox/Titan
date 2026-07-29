# تحقيق #7 — Webhook vs Polling (Production Deployment)

**التاريخ:** 2026-07-23
**الحالة:** مكتمل — قرار: **Reject** — **معتمد**
**النطاق:** تحليل ما إذا كان غياب دعم Webhook في Titan يمثل فجوة معمارية حقيقية، أو قيد نطاق واعٍ، أو قرار تصميم مقصود.

---

## 1. المشكلة كما تظهر في الاستخدام الحقيقي

### الأعراض الأكثر تكراراً في PTB وaiogram

**العرَض الأول — "بوتي لا يستقبل تحديثات على السيرفر"**
مطور ينقل بوته من جهازه المحلي إلى VPS أو منصة سحابية. يعمل محلياً، ثم يتوقف على الإنتاج. الغالب: Telegram يرفض `getUpdates` لأن `setWebhook` كان مُفعَّلاً سابقاً — والـ conflict بين الاثنين يصمت.

**العرَض الثاني — "Polling يستهلك كثيراً من المصادر"**
مطور يدير عشرات البوتات ويلاحظ أن كل بوت يحتفظ بـ HTTP connection مفتوح مع Telegram باستمرار. يريد webhook لأن Telegram هو من يُرسل عند وجود update — لا اتصال دائم.

**العرَض الثالث — "كيف أنشر بوتي على Heroku / Railway / Render؟"**
المنصات السحابية بالـ free-tier تُوقف العملية عند غياب الطلبات (sleep). Polling يحتاج process دائمة — Webhook يُيقظ العملية عند كل update. هذا يجعل Webhook ضرورة deployment لا رفاهية معمارية.

**العرَض الرابع — "بوتي يتأخر في الرد"**
Polling الافتراضي كل 30 ثانية (long-polling بـ timeout=30). في الواقع latency أقل بكثير — لكن المطور يظنه بطيئاً لعدم فهمه الفرق بين timeout الانتظار وتأخير التسليم.

### ما أنتجته هذه الأعراض في الأطر الناضجة

- **PTB:** يدعم كلاً من `updater.start_polling()` و`updater.start_webhook()`. في v20 أُعيد التصميم حيث `Application` هي المحور، والـ transport (polling أو webhook) معلَّق كـ updater منفصل. الفصل واضح: المعالجة لا تعرف مصدر الـ update.
- **aiogram:** `Dispatcher` كائن معالجة بحت لا يعرف شيئاً عن النقل. `polling()` و`webhook()` هما entry points مستقلة تُغذّي نفس الـ dispatcher. هذا يُجسّد المبدأ بشكل صريح: transport-agnostic dispatcher.
- **النمط المشترك:** كلا الإطارين فصلا مسألتين بوضوح — **كيف يصل الـ update** (transport) عن **ماذا يحدث بعد وصوله** (processing). هذا الفصل هو الجذر المعماري، لا وجود Webhook بحد ذاته.

---

## 2. الجذر المعماري

### الجذر المعماري الحقيقي: Transport Choice

**Transport Choice** هو الجذر: هل طريقة وصول الـ update (polling أو webhook) مُدمجة مع طريقة معالجته، أم مفصولة عنها؟

هذا هو السؤال المعماري الذي أجبر PTB وaiogram على قرارات تصميمية — لا وجود أو غياب Webhook بحد ذاته. Webhook هو ضغط استخدام (بيئات serverless ومنصات sleep) جعل هذا الفصل ضرورياً عملياً في نطاقهما — ليس الجذر المعماري نفسه.

### مسألتان تنبثقان من هذا الجذر

**المسألة أ — Transport Coupling (هل معالجة الـ update مرتبطة بطريقة وصوله؟)**
السؤال الفني: هل يستطيع Titan استقبال update من مصدر غير polling دون إعادة كتابة طبقة المعالجة؟ الجواب يأتي من تحليل الكود.

**المسألة ب — Declared Transport (ما هو النقل الذي يُعلن عنه عقد Titan؟)**
الجواب يأتي من CONTRACT، لا من افتراضات حول جمهور Titan أو بيئاته المستهدفة.

**الفارق الجوهري:**
Deployment (Webhook vs Polling) هو ضغط استخدام أبرز أهمية Transport Choice — ليس فجوة معمارية مستقلة.

---

## 3. تحليل Titan — الكود الفعلي

### 3.1 مسار وصول الـ update

```
bot.run()
  → run_async()
      → loop: api.get_updates(offset, timeout=30)
          → يعيد قائمة updates
      → لكل update: asyncio.create_task(_run_async(update_data))
          → Update.from_dict(update_data)
          → Context(update, api)
          → middleware_chain.run(ctx, dispatch)
              → dispatch(ctx)
                  → _handle_update(ctx)
```

**الملاحظة الجوهرية:** نقطة الانفصال الطبيعية هي `_run_async(update_data)` — هذه الدالة تستقبل `dict` خام وتُكمل المعالجة بالكامل. لا تعرف ولا تهتم بمصدر هذا الـ dict.

### 3.2 أين يقع الـ coupling الفعلي؟

```python
# هذا هو المكان الوحيد الذي يعرف أن المصدر هو polling:
updates = await self._api.get_updates(offset=offset, timeout=timeout)
for update_data in updates:
    asyncio.create_task(self._run_async(update_data))
```

الـ coupling موجود — لكنه محصور تماماً في `run_async()`. لا يمتد إلى:
- `_handle_update()` — لا تعرف مصدر الـ update
- `MiddlewareChain` — transport-agnostic بالكامل
- `Router` / `dispatch()` — يعالج `Context` فقط
- `Context` / `Update` — لا يحملان معلومة عن المصدر

### 3.3 هل يُصعّب التصميم الحالي إضافة Webhook لاحقاً؟

لا — لأسباب بنيوية واضحة:
- `_run_async(update_data: dict)` موجودة وتعمل كـ entry point نظيفة.
- إضافة Webhook تعني: HTTP server يستقبل POST → يستخرج `update_data` → يستدعي `_run_async()`. الاتصال بطبقة المعالجة نقطة واحدة.
- لا يحتاج تغيير في Router، Middleware، Context، أو Adapter.
- comment في `bot.py` سطر 627 يُقرّ صراحةً بهذا: "مستقبلية غير polling (مثل Userbot Support)" — نقطة التمديد معروفة ومُشار إليها.

### 3.4 هل يوجد setWebhook أو deleteWebhook؟

لا — `telegram.py` لا تحتوي `setWebhook` أو `deleteWebhook`. هذا يعني:
- إذا كان webhook مُفعَّلاً مسبقاً على البوت، `get_updates` ستفشل بصمت أو تُرجع 0 updates.
- لا تشخيص، لا تحذير، لا تنظيف تلقائي.
- هذا عَرَض من أعراض العرَض الأول الموثَّق أعلاه.

---

## 4. تحليل المسألتين

### المسألة أ — Transport Coupling

**هل الجذر المعماري موجود في Titan؟** جزئياً — الـ coupling موجود لكنه محصور في نقطة واحدة (`run_async()`). بقية طبقات المعالجة transport-agnostic بالفعل (موثَّق في §3).

**هل هذا فجوة تستدعي تدخلاً؟**

CONTRACT §0 يُعرِّف `run()` و`run_async()` كـ entry points الرسمية الوحيدة، ولا يذكر webhook في أي موضع من العقد أو الوثائق. هذا يعني أن Titan لا تدّعي transport abstraction — ادعاء لم يُصرَّح به لا يمكن اعتبار غيابه فجوة.

الـ coupling في `run_async()` ليس خطأ معمارياً — هو حدود ما صرَّح به العقد. التصميم لا يمنع التوسع: `_run_async(update_data: dict)` جاهزة كـ entry point نظيفة لأي مصدر مستقبلي.

المقارنة مع aiogram مُضلِّلة هنا: aiogram بنى transport abstraction لأنه صرَّح باستهداف بيئات deployment متنوعة — ادعاء موجود في وثائقه. Titan لم يُصدر ادعاءً مماثلاً.

### المسألة ب — Declared Transport

**ما الذي يُعلنه عقد Titan عن النقل؟**

CONTRACT §0 يُعدِّد entry points النظام: `run()` و`run_async()` — كلاهما يقودان polling loop. لا يوجد في CONTRACT أو في أي وثيقة أخرى ذكر لـ webhook كـ entry point مدعومة أو مخططة. هذا دليل إيجابي، لا افتراض: Titan يُعلن polling صراحةً، ولا يُعلن webhook.

**هل غياب Webhook فجوة معمارية؟**

لا — لأن Titan لا يُعلن في عقده أو وثائقه أنه يستهدف البيئات التي تتطلب Webhook، لذلك لا يمكن اعتبار غيابه فجوة معمارية. الضغط الذي يُظهر هذا الغياب (serverless، منصات sleep) ضغط استخدام لم يظهر في نطاق Titan المُعلَن.

**نقطة مفتوحة — Webhook Conflict Detection:**
غياب `deleteWebhook` أو أي تحقق عند بدء polling قد يُربك المطور الذي سبق وفعّل webhook يدوياً. هذا ليس فجوة معمارية — هو تجربة مطور (DX) سيئة يمكن معالجتها بتحذير في بداية `run_async()` إذا ظهر ضغط من المستخدمين.

---

## 5. ما لا يُعدّ فجوة

**غياب HTTP server للـ webhook:** يستدعي اختيار إطار HTTP (aiohttp، FastAPI، starlette) — قرار نطاق يتجاوز ما يجب أن يحمله Core.

**غياب SSL handling:** الـ TLS ينتمي للـ infrastructure (Nginx، Cloudflare، reverse proxy) — ليس للـ bot framework.

**غياب setWebhook تلقائي:** نفس السبب — إدارة الـ webhook lifecycle ليست مسؤولية Core.

**Latency الـ polling:** Long-polling بـ timeout=30 يُسلّم الـ update في أقل من ثانية من إرسال المستخدم له. لا مشكلة latency حقيقية في هذا النطاق.

---

## 6. القرار: **Reject**

**السبب:**

1. **الجذر المعماري (Transport Choice):** الفصل المعماري متحقق عملياً بعد نقطة الدخول — `_run_async(dict)` وكل ما يليها transport-agnostic بالكامل. أما نقطة الدخول نفسها (`run_async()`) فما زالت مرتبطة بالـ polling، لكن هذا الـ coupling لا يخترق باقي الطبقات وهو ما يجعل التوسع مستقبلاً ممكناً دون إعادة كتابة طبقة المعالجة.

2. **الادعاء (Declared Transport):** CONTRACT §0 يُعلن `run()` و`run_async()` كـ entry points الوحيدة، ولا يذكر webhook في أي موضع. Titan لا تُعلن في عقدها أنها تستهدف البيئات التي تتطلب Webhook، لذلك لا يمكن اعتبار غيابه فجوة معمارية.

3. **لماذا Reject وليس Defer؟** Defer تعني "الجذر المعماري يستدعي معالجة لكن ليس الآن." هنا الجذر غير موجود — لا يوجد ادعاء transport abstraction لم يُوفَّ به، والضغط الذي يُبرر التعقيد (serverless، منصات sleep) لم يظهر في النطاق المُعلَن.

**ملاحظة مفتوحة (DX، لا معمار):**
غياب تحذير عند conflict بين Webhook نشط وـ polling بادئ قد يستحق معالجة مستقبلية كـ DX improvement، إذا ظهرت شكاوى من مستخدمين. هذا خارج نطاق هذا التحقيق ولا يُغير القرار.

---

*وثيقة تحقيق أولية — تتطلب مراجعة واعتماد القرار قبل أي تنفيذ.*
