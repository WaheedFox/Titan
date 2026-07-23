# Investigation #3 — Error Handling & Propagation

**التاريخ:** 2026-07-23  
**الحالة:** مكتمل — قرار: **Adapt**  
**النطاق:** ضمان وصول الاستثناءات إلى error handler، وجودة المعلومات المتاحة عند وقوع الخطأ

---

## 1. المشكلة كما تظهر في الاستخدام الحقيقي

### الأعراض الأكثر تكراراً في PTB وaiogram (GitHub Issues، Reddit، Stack Overflow)

**العرَض الأول — "البوت يتجمد بدون أي رسالة"**  
مطور يضيف handler يحتوي خطأً. البوت يستقبل الرسالة، لا شيء يحدث، لا ردّ، لا خطأ في stdout. المطور لا يعرف أين المشكلة.

**العرَض الثاني — "خطأ في handler لا يصل لـ error_handler المسجَّل"**  
مطور يسجّل error handler، لكن استثناء معيّن لا يصل إليه. يكتشف لاحقاً أن الاستثناء حدث داخل `asyncio.create_task()` ولم يُربط بأي handler.

**العرَض الثالث — "error handler يعمل لكن لا أعرف السطر الذي تسبب في الخطأ"**  
error handler يستقبل `exc` وعند طباعته يحصل على `str(exc)` فقط — بدون stack trace، بدون اسم الملف، بدون رقم السطر.

**العرَض الرابع — "استثناء داخل error handler يختفي"**  
error handler نفسه يحتوي خطأً. الاستثناء الداخلي يُبتلع بصمت، والمطور يقضي وقتاً طويلاً يبحث عن سبب عدم عمل error handler.

---

## 2. الجذر المعماري في PTB وaiogram

### نموذج asyncio والمشكلة الأساسية

في Python، `asyncio.create_task()` ينشئ task مستقل. إذا انتهى هذا الـ task بـ exception دون أن يُستقبل النتيجة أو يُضاف `add_done_callback`، فإن Python:

1. يحتفظ بالاستثناء داخل الـ task object.
2. عند جمع القمامة (GC) لهذا الـ task object — وليس فوراً — يُطبع تحذيراً: `"Task exception was never retrieved"`.
3. لا يُوقف البرنامج، لا يُبلّغ أي handler.

هذا يعني أن أي إطار يستخدم `create_task()` لتشغيل handlers يواجه سؤالاً معمارياً جوهرياً: **من يستقبل الاستثناء الذي يخرج من الـ task؟**

### PTB — الحل والثغرة

PTB يُشغّل كل update في coroutine منفصل. `Application.process_update()` مُلفَّف في try/except يوجّه الاستثناء لـ `_dispatch_error()`. هذا يحل مشكلة الـ task silently failing.

لكن الثغرة: إذا لم يُسجَّل error handler، PTB v13 كان يُسكت الاستثناء تماماً (silent swallow). PTB v20 يُسجّله عبر `logging`، لكن بـ `str(exc)` فقط في بعض المسارات — بدون traceback كامل.

### aiogram — الحل والثغرة

aiogram 3.x يستخدم `@router.error()` decorator. الاستثناءات التي لا تُعالَج بـ handler تصل لـ `ErrorEvent`. إذا لم يُسجَّل error handler، يُطبع aiogram السطر `"Unhandled exception"` بدون traceback كامل في بعض الإعدادات.

### القاسم المشترك

كلا الإطارين يعانيان من نفس المشكلة في المسار الافتراضي:

| المشكلة | الأثر |
|---|---|
| استثناء يهرب من task boundary | لا يصل لأي handler، يظهر عند GC فقط |
| لا error handler مسجَّل | صمت تام أو رسالة منقوصة |
| error handler مسجَّل + خطأ داخله | يُبتلع الخطأ الداخلي |
| traceback مفقود | المطور يعرف **ماذا** حدث، لا **أين** |

---

## 3. تحليل Titan — الكود الفعلي

### 3.1 ضمان وصول الاستثناء لـ `_handle_error`

```
_handle_update(raw_update)
├── try:
│   └── await self.middleware_chain.run(ctx, dispatch)
│       └── dispatch()
│           ├── callback handler: try/except → _handle_error()   [سطر 658–661]
│           └── command handler:  try/except → _handle_error()   [سطر 694–697]
└── except Exception as e:
    └── _handle_error(ctx, e)                                    [سطر 704–705]
```

**الضمان موجود:** كل مسار تنفيذ داخل `_handle_update` — سواء middleware أو command handler أو callback handler أو `dispatch()` نفسه — يصل في النهاية إلى `_handle_error`. لا مسار ينتهي بـ unhandled exception.

### 3.2 `asyncio.create_task()` — هل هناك ثغرة؟

ثلاثة مواضع:

**الموضع الأول — `_ensure_chat_worker` (سطر 748):**  
```python
task = asyncio.create_task(self._chat_worker(chat_id, queue), ...)
```
`_chat_worker` نفسه لا يحتوي try/except. إذا `_chat_worker` نفسه رمى استثناءً (وهذا غير ممكن في الكود الحالي لأن دوره مجرد قراءة من queue وإطلاق tasks) — الاستثناء يظهر عند GC فقط. خطر نظري منخفض جداً في الكود الحالي.

**الموضع الثاني — `_chat_worker` (سطر 773):**  
```python
asyncio.create_task(self._handle_update(raw), ...)
```
`_handle_update` مُلفَّف بالكامل في try/except. الاستثناء مضمون الاستقبال داخل `_handle_update` — لن يهرب من الـ task. **آمن.**

**الموضع الثالث — `run_async` (سطر 827):**  
```python
asyncio.create_task(self._handle_update(raw), ...)
```
نفس الموضع الثاني. **آمن.**

**خلاصة الـ tasks:** الضمان البنيوي سليم. المخاطر النظرية صغيرة ومقبولة.

### 3.3 `_handle_error` — التنفيذ الفعلي

```python
async def _handle_error(self, ctx: Context, exc: Exception) -> None:
    if self._error_handler is not None:
        try:
            await self._error_handler(ctx, exc)
        except Exception as inner:
            self._log(f"Exception raised inside error handler: {inner}")
    else:
        self._log(f"Unhandled exception: {exc}")
```

**ملاحظات:**

| الجانب | الوضع الحالي | الأثر |
|---|---|---|
| لا error handler مسجَّل | `_log(f"Unhandled exception: {exc}")` | `str(exc)` فقط — لا traceback |
| error handler مسجَّل + استثناء داخله | `_log(f"Exception raised inside error handler: {inner}")` | `str(inner)` فقط — لا traceback |
| لا يوجد `traceback` أو `exc_info=True` في أي موضع | لا في `_handle_error`، لا في `_chat_worker`، لا في `run_async` | المطور يعرف نوع الخطأ، لا مكانه |

---

## 4. الفجوة المعمارية الحقيقية في Titan

### ما تحل Titan بشكل صحيح (مقارنةً بـ PTB/aiogram)

- **ضمان الوصول:** كل استثناء يصل لـ `_handle_error` بضمان بنيوي — لا مسار يُسكت الخطأ تماماً.
- **حماية error handler نفسه:** الاستثناء داخل error handler لا يُوقف البوت ولا يمر صامتاً.
- **لا `BaseException` مُبتلَع:** الكود يستخدم `except Exception` بشكل صحيح.

### ما لا تحله Titan — الفجوة الفعلية

**المشكلة الوحيدة الحقيقية: فقدان الـ traceback في المسار الافتراضي.**

عندما لا يُسجَّل error handler (الحالة الافتراضية أثناء التطوير)، يطبع Titan:
```
Unhandled exception: 'NoneType' object has no attribute 'text'
```

بدون:
- اسم الملف
- رقم السطر  
- سلسلة استدعاء الدوال (call stack)

هذه المعلومات موجودة في Python في كل لحظة — `exc.__traceback__` — لكن `str(exc)` يتجاهلها تماماً.

**الأثر الفعلي:** مطور يكتب handler جديداً يرى رسالة غامضة في stdout لا تدله على أي سطر في كوده يحمل المشكلة. هذا هو نفس الشكوى الأكثر تكراراً في PTB وaiogram — إلا أن سببها في تلك الأطر هو عدم وصول الاستثناء للـ handler أصلاً، بينما في Titan يصل لكن المعلومات منقوصة.

### الفجوة الثانوية: traceback داخل error handler نفسه

```python
except Exception as inner:
    self._log(f"Exception raised inside error handler: {inner}")
```

نفس المشكلة — المطور يعرف أن error handler رمى استثناءً، لكنه لا يعرف في أي سطر من error handler حدث ذلك.

---

## 5. ما لا يُعدّ فجوة

### `asyncio.create_task` بدون `add_done_callback`

بما أن `_handle_update` مُلفَّف بالكامل، الـ tasks الناتجة عنه لن ترمي استثناءات خارج نطاقها. إضافة `add_done_callback` لكل task ستضيف تعقيداً بلا عائد حقيقي في الكود الحالي.

### عدم وجود timeout مدمج للـ handlers

قرار نطاق سابق — مذكور في وثيقة ask(). `asyncio.wait_for()` متاح للمطور.

### `_chat_worker` بدون try/except خاص

دوره محدود: قراءة من queue وإطلاق tasks فقط. لا معالجة منطقية تُنتج استثناءات متوقعة.

---

## 6. مقارنة الفجوة مع طبيعة مشاكل PTB/aiogram

| المشكلة | PTB/aiogram | Titan |
|---|---|---|
| استثناء يهرب من task بصمت كامل | ✅ مشكلة حقيقية | ❌ غير موجود — الضمان البنيوي يمنعها |
| لا error handler = صمت تام | ✅ مشكلة في PTB v13 | ❌ غير موجود — يُطبع دائماً |
| traceback مفقود في الـ log | ✅ مشكلة | ✅ **مشكلة موجودة في Titan أيضاً** |
| استثناء داخل error handler يختفي | ✅ مشكلة | ❌ غير موجود — يُطبع — لكن بدون traceback |

الفجوة الوحيدة المشتركة: **فقدان الـ traceback** — وهي الأقل خطورةً من بين مشاكل PTB/aiogram، لكنها تظل ذات أثر حقيقي على تجربة التطوير.

---

## 7. القرار

### **Adapt**

**ليس Reject** لأن الفجوة ليست "اختلاف تصميمي واعٍ" — الـ traceback المفقود لا يُقدّم أي ميزة. لا يوجد مبرر هندسي لتجاهله. `str(exc)` أقل معلومات من `logging.exception()` في كل حالة ممكنة.

**ليس Adopt** لأن البنية الأساسية سليمة. المشكلة لا تتطلب إعادة تصميم معمارية — التعديل محدود ودقيق.

**Adapt:** تعديل `_handle_error` لتضمين الـ traceback في مسار الـ fallback (لا error handler مسجَّل) وفي مسار الاستثناء داخل error handler نفسه.

### نطاق التعديل المقترح (لا كود — وصف فقط)

- في مسار `else` (لا error handler): استخدام `logging.exception()` أو تمرير `exc_info=True` بدلاً من `str(exc)`.
- في مسار الاستثناء داخل error handler: نفس المعالجة.
- التوافق: `_error_handler` المسجَّل يستقبل `ctx` و`exc` كما الآن — لا تغيير في الواجهة الخارجية.

### ما لا يتغير

- بنية `_handle_update` ومسارات الـ try/except.
- واجهة `@bot.error_handler`.
- سلوك الـ tasks والـ workers.
- كل ما يخص أولوية المعالجة أو ترتيب تنفيذ الـ handlers.

---

## 8. ملاحظة للتنفيذ

هذا التحقيق يصف فجوة واحدة محددة في سطر واحد فعلياً (`_handle_error` — سطر 71 في `bot.py`). الحل لا يستدعي ADR مستقلاً — يمكن تغطيته بـ note في وثيقة CONTRACT.md إذا اعتُمد القرار.

---

*وثيقة تحقيق أولية — تتطلب مراجعة واعتماد القرار قبل أي تنفيذ.*
