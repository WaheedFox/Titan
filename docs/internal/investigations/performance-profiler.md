# تحقيق — Performance Profiler

**الحالة:** مُغلقة — القرار المعماري اتُّخذ — راجع ADR-013
**تاريخ:** 2026-07-11
**الميزة:** Performance Profiler (#7) — من قائمة Planned

---

## 1. المشكلة التي يحلها Performance Profiler داخل Titan

**من منظور المطور:**
> "البوت يعمل، لكنه يبدو بطيئاً أحياناً — ولا أعرف أين المشكلة بالضبط."

الأدوات الثلاث الموجودة (`inspect`, `health`, `lint`) تُجيب على أسئلة عن **الهيكل الثابت**:
ماذا سُجِّل، هل البنية مكتملة، هل الاتفاقيات محترمة.

لا أحد منها يسأل: **ماذا حدث فعلاً أثناء التشغيل؟**

المشكلة التي لا يُرى حلها حالياً:

- Handler واحد يستغرق 2 ثانية — هل هو handler الأمر؟ الـ middleware؟ بناء الـ Context؟
- `@bot.on("message")` يحتوي 8 handlers — أيّها المشكلة؟
- هل الـ middleware يُضيف latency حقيقياً أم هو رخيص؟
- كم update/ثانية يستطيع البوت معالجته فعلاً؟

هذه أسئلة **runtime** لا أجوبة عنها في الـ state المخزّن على `bot`.

---

## 2. ما الذي لا تستطيع inspect/health/lint اكتشافه؟

| الأداة | ما تراه | ما لا تراه |
|---|---|---|
| `inspect()` | ماذا سُجِّل (أسماء، أعداد) | لم يُنفَّذ شيء بعد — لا بيانات runtime |
| `health()` | هل البنية مكتملة | لا تعرف شيئاً عن الأداء |
| `lint()` | هل الاتفاقيات محترمة | لا تعرف كم استغرق أي handler |

الثلاثة تقرأ **حالة تسجيل ثابتة**. الـ Profiler يحتاج أن يُلاحظ **تنفيذاً ديناميكياً**.

هذا ليس فارقاً في التفاصيل — هو فارق في الطبيعة. inspect/health/lint لا تحتاج أي تغيير في pipeline التنفيذ. الـ Profiler يحتاج أن يكون **داخل** الـ pipeline أو **يُحيط به** ليرى ما يحدث.

---

## 3. ما البيانات القابلة للقياس الآن — بدون تعديل Core

### 3أ. عبر Middleware

مطوّر يمكنه اليوم كتابة:

```python
import time

@bot.middleware
async def timer(ctx, next):
    start = time.perf_counter()
    await next()
    elapsed = time.perf_counter() - start
    print(f"total: {elapsed:.3f}s")
```

ما يقيسه: الوقت الكلي من دخول هذا الـ middleware إلى انتهاء كل ما بعده
(بقية middleware + routing + handler).

ما لا يقيسه:
- وقت بناء `Update` و`Context` (يحدث قبل middleware)
- أيّ handler تحديداً نُفِّذ
- انهيار الوقت: middleware vs handler vs routing

### 3ب. عبر `on_offset` hook

يُعطي count للـ updates المعالجة — لكن لا timing.

### 3ج. عبر Playground + feed_update()

```python
import time
start = time.perf_counter()
await bot.feed_update(fake_command("start"))
elapsed = time.perf_counter() - start
```

يقيس: الوقت الكلي لمعالجة update واحد في بيئة محكومة.
لا يُشغّل شبكة — يعزل timing الـ handler الحقيقي.

### 3د. اكتشاف رئيسي من قراءة `bot.py`

`feed_update()` هو entry point رسمي ونظيف — موثَّق في CONTRACT، مُعرَّض للخارج، يدعو
`_handle_update` مباشرة بدون أي منطق مكرر:

```python
async def feed_update(self, update: dict[str, Any]) -> None:
    await self._handle_update(update)
```

هذا يعني: قياس wall time الكلي ممكن من **خارج Core بالكامل** بـ `time.perf_counter()`
قبل وبعد `await bot.feed_update(update)`. لا hooks مطلوبة.

ملاحظة إضافية: `dispatch` داخل `_handle_update` هو closure لا method منفصلة.
تفكيك الوقت بين middleware / routing / handler يتطلب إعادة هيكلة `bot.py` أو
إضافة conditionals داخل الـ closure — تكلفة حقيقية على ملف كان بسيطاً.

### 3هـ. الخلاصة

**ما هو متاح بدون Core hooks:**
- ✅ الوقت الكلي لمعالجة update (من middleware أو Playground)
- ✅ عدد updates معالجة (on_offset)
- ❌ توزيع الوقت بين middleware / routing / handler
- ❌ معرفة أيّ handler تحديداً نُفِّذ واستغرق كم (من الداخل)
- ✅ معرفة نوع الـ update (يُستنتج من بنية الـ dict: وجود callback_query، text يبدأ بـ /)

---

## 4. القياسات التي تحتاج Core hooks

### نقطة 1 — داخل `_handle_update` (قبل middleware)

```python
# الموقع الحالي:
update = Update(raw_update)
ctx = Context(update, self._api, links=self.links)
```

Profiler يحتاج hook هنا لقياس: وقت بناء Context.

### نقطة 2 — داخل `_dispatch` (حول handler call)

```python
# الموقع الحالي:
for handler in self.handlers.get(event, []):
    await handler(ctx)
```

Profiler يحتاج wrapping هنا لقياس: وقت كل handler على حدة.
يتيح أيضاً معرفة: أيّ event type، أيّ handler بالاسم.

### نقطة 3 — حول command/callback handlers

```python
# الموقع الحالي:
await handler(ctx)  # inside dispatch()
```

نفس الحاجة: وقت تنفيذ handler المحدد + اسمه (اسم الأمر، قيمة callback_data).

### نقطة 4 — حول middleware chain كاملة

```python
# الموقع الحالي:
await self.middleware_chain.run(ctx, dispatch)
```

Profiler يحتاج: وقت الـ middleware chain الكلي مقابل وقت الـ handler.

### ملاحظة مهمة — مشكلة async

كل هذه النقاط في سياق `async` — الـ CPU time للـ handler ليس عزلاً حقيقياً
(event loop يعمل). `time.perf_counter()` يقيس wall time، لا CPU time.
هذا مقبول كـ proxy مفيد للـ v1 — بشرط التوثيق الصريح.

---

## 5. هل هو `bot.profiler()` أم domain منفصل؟

### التشابه مع health/lint/inspect (يدفع نحو Core)

- يفحص `bot` نفسها
- المستهلك نفسه (المطور أثناء التطوير)
- النتيجة `list[ProfilingResult]` أو dict مشابه

### الاختلاف الجوهري (يدفع نحو الحذر)

| | health / lint / inspect | Profiler |
|---|---|---|
| **الطبيعة** | يقرأ state ثابت | يُلاحظ تنفيذاً ديناميكياً |
| **الوقت** | تُستدعى في أي وقت — لا overhead | تحتاج أن تكون "شغّالة" أثناء التنفيذ |
| **الأثر** | صفر overhead على التشغيل | overhead حقيقي — مهما كان صغيراً |
| **الحالة** | لا تراكم — النتيجة تُحسَب لحظياً | تراكم بيانات عبر الزمن — تحتاج مخزن |

**هذا الاختلاف الأخير هو الأهم:**

`bot.lint()` يمكن استدعاؤه 1000 مرة — لا side effects، لا تراكم.
`bot.profiler()` يحتاج أن يُجمع بيانات قبل أن يُستدعى — وهذا يعني:

- من يُشغّل التجميع؟
- متى يبدأ؟
- أين تُخزَّن النتائج؟
- هل هو دائماً مفعّل؟

ثلاثة خيارات معمارية رئيسية:

**الخيار أ — قدرة Core دائماً مفعّلة (مثل health)**
Titan تُسجّل timing لكل update تلقائياً.
`bot.profiler()` يُعيد ملخص ما جُمع.
- المشكلة: overhead دائم في production. غير مقبول لمكتبة stability-driven.

**الخيار ب — قدرة Core opt-in**
المطور يُفعّل التجميع صريحاً:
```python
bot.enable_profiling()
# ... run some updates ...
report = bot.profiling_report()
bot.disable_profiling()
```
- متسق مع فلسفة Titan (explicit over implicit)
- overhead فقط حين المطور يطلبه
- يحتاج state جديدة على `bot` (enabled: bool، accumulated data)

**الخيار ج — domain منفصل: `titan.profiler`**
مثل `titan.playground` — يستهلك `feed_update()` لا polling الحقيقي:
```python
from titan.profiler import profile_update
result = await profile_update(bot, fake_command("start"))
```
- لا overhead في production — يعمل فقط حين يُستدعى
- محدود: يقيس في بيئة Playground لا production فعلي
- يستفيد من `feed_update()` الموجود بدون hooks جديدة في pipeline

---

## 6. أقل v1 حقيقي بدون بناء نظام metrics ضخم

**الحدود المقبولة لـ v1:**

قياس واحد فقط لكل update: **wall time كلي** من دخول `_handle_update` إلى خروجه.
لا تفكيك (middleware vs handler) في v1.

هذا يعطي المطور إجابة حقيقية على: "كم استغرق معالجة هذا النوع من الأوامر؟"

**أقل تنفيذ حقيقي:**

```
ProfileEntry:
    event_type: str           # "command/start"، "callback/yes"، "message"
    duration_ms: float        # wall time الكلي
    timestamp: float          # وقت بدء المعالجة

ProfilingSession:
    entries: list[ProfileEntry]
    summary() → dict          # avg/min/max per event_type
```

هذا يكفي للإجابة على:
- ما أبطأ نوع update في البوت؟
- ما متوسط وقت معالجة `/start`؟
- هل أداء البوت يتراجع بعد N updates؟

---

## 7. ما الذي نرفضه في v1 عمداً

| المرفوض | السبب |
|---|---|
| Percentiles (p50/p95/p99) | تحتاج مكتبة إحصائيات أو تنفيذ مخصص — ليس v1 |
| تفكيك الوقت (middleware vs routing vs handler) | يتطلب hooks في نقاط متعددة من Core — scope كبير |
| Network timing (Telegram API latency) | concern مختلف — أقرب لـ monitoring من profiling |
| Flame graphs أو traces مترابطة | نظام monitoring كامل — خارج نطاق Titan |
| Async CPU profiling حقيقي | يحتاج cProfile أو yappi — تبعيات ثقيلة |
| دعم production always-on | overhead دائم يتعارض مع stability-driven philosophy |
| تخزين دائم (DB/file) للقياسات | Titan لا تمتلك persistence layer لهذا الغرض |
| streaming/real-time metrics | نظام observability كامل — خارج النطاق |
| Per-user profiling | PII concerns + scope ضخم |

---

## 8. التوترات المفتوحة — مُحسومة بالقرار المعماري

**التوتر 1 — أين يعيش؟**
✅ محسوم: **Playground-based** — لا Core opt-in.

**التوتر 2 — ماذا يقيس بالضبط؟**
✅ محسوم: **Wall time كلي per event type** — لا تفكيك مراحل.

**التوتر 3 — كيف يُشغَّل في الـ pipeline؟**
✅ محسوم: **يُقاس من الخارج** عبر `feed_update()` — لا hooks.

**التوتر 4 — هل هو development tool فقط؟**
✅ محسوم: **أداة تطوير فقط في v1.**
Production monitoring قرار مستقل لا يُتخذ إلا إذا ظهر use case حقيقي.

---

## 9. القرار النهائي

**`titan.profiler` — domain منفصل، Playground-based، بدون تعديل Core.**

راجع: [docs/decisions/013-performance-profiler.md](../decisions/013-performance-profiler.md)
