# Investigation #3 — Error Handling & Propagation

**التاريخ:** 2026-07-23  
**الحالة:** مكتمل — قرار: **Adapt**  
**النطاق:** ضمان وصول الاستثناءات إلى error handler، واكتمال السياق التشخيصي عند وقوع الخطأ

---

## 1. المشكلة كما تظهر في الاستخدام الحقيقي

### الأعراض الأكثر تكراراً في PTB وaiogram (GitHub Issues، Reddit، Stack Overflow)

**العرَض الأول — "البوت يتجمد بدون أي رسالة"**  
مطور يضيف handler يحتوي خطأً. البوت يستقبل الرسالة، لا شيء يحدث، لا ردّ، لا خطأ في stdout. المطور لا يعرف أين المشكلة.

**العرَض الثاني — "خطأ في handler لا يصل لـ error_handler المسجَّل"**  
مطور يسجّل error handler، لكن استثناء معيّن لا يصل إليه — لأنه حدث داخل `asyncio.create_task()` ولم يُربط بأي handler.

**العرَض الثالث — "error handler يعمل لكن لا أعرف السطر الذي تسبب في الخطأ"**  
error handler يستقبل `exc`، لكن كل المعلومات المتاحة هي `str(exc)` — بدون call stack، بدون اسم الملف، بدون رقم السطر.

**العرَض الرابع — "استثناء داخل error handler يختفي"**  
error handler نفسه يحتوي خطأً. الاستثناء الداخلي يُبتلع بصمت.

---

## 2. الجذر المعماري في PTB وaiogram

في Python، `asyncio.create_task()` ينشئ task مستقل. إذا انتهى بـ exception دون أن يُنتظر أو يُربط بـ callback، فإن Python يحتفظ بالاستثناء داخل الـ task object — ويُبلّغ عنه فقط عند جمع القمامة (GC)، وليس فوراً.

هذا يعني أن أي إطار يستخدم `create_task()` لتشغيل handlers يواجه سؤالاً معمارياً جوهرياً: **من يستقبل الاستثناء الذي يخرج من الـ task، ومتى؟**

### PTB — الحل والثغرة

`Application.process_update()` مُلفَّف في try/except يوجّه الاستثناء لـ `_dispatch_error()`. هذا يحل مشكلة الـ task silently failing. لكن إذا لم يُسجَّل error handler، PTB v13 كان يُسكت الاستثناء تماماً. PTB v20 يُسجّله، لكن السياق التشخيصي الكامل يعتمد على إعداد `logging` الخارجي — لا يُضمن افتراضياً.

### aiogram — الحل والثغرة

aiogram 3.x يستخدم `@router.error()`. الاستثناءات التي لا تُعالَج بـ handler تصل لـ `ErrorEvent`. لكن في مسار الـ fallback، السياق التشخيصي قد يكون منقوصاً.

### القاسم المشترك

| المشكلة | الأثر |
|---|---|
| استثناء يهرب من task boundary | لا يصل لأي handler، يظهر عند GC فقط |
| لا error handler مسجَّل | صمت تام أو رسالة منقوصة |
| error handler مسجَّل + خطأ داخله | يُبتلع الخطأ الداخلي |
| السياق التشخيصي مفقود | المطور يعرف **ماذا** حدث، لا **أين** |

---

## 3. تحليل Titan — الكود الفعلي

### 3.1 ضمان وصول الاستثناء لـ `_handle_error`

```
_handle_update(raw_update)
└── try/except شامل  [سطر 702–705]
    └── await self.middleware_chain.run(ctx, dispatch)
        └── dispatch()
            ├── callback handler: try/except → _handle_error()   [سطر 658–661]
            └── command handler:  try/except → _handle_error()   [سطر 694–697]
```

**الضمان موجود وسليم:** كل مسار تنفيذ داخل `_handle_update` يصل في النهاية إلى `_handle_error`. لا مسار ينتهي بـ unhandled exception.

### 3.2 `asyncio.create_task()` — هل هناك ثغرة؟

ثلاثة مواضع في الكود:

- `_ensure_chat_worker` (سطر 748) — ينشئ task لـ `_chat_worker`. `_chat_worker` نفسه لا يحتوي try/except، لكن دوره مجرد قراءة من queue وإطلاق tasks — لا معالجة منطقية تُنتج استثناءات متوقعة. خطر نظري منخفض جداً.
- `_chat_worker` (سطر 773) — ينشئ task لـ `_handle_update`. بما أن `_handle_update` مُلفَّف بالكامل، الاستثناء مضمون الاستقبال داخله. **آمن.**
- `run_async` (سطر 827) — نفس الموضع الثاني. **آمن.**

**خلاصة:** ضمان وصول الاستثناء لـ `_handle_error` مؤكَّد بنيوياً. المشكلة الجذرية في PTB/aiogram غير موجودة في Titan.

### 3.3 `_log()` و `_handle_error` — التنفيذ الفعلي

```python
# module level
_log = logging.getLogger("titan")

# method
def _log(self, msg: str) -> None:
    _log.info(msg)

# _handle_error
async def _handle_error(self, ctx: Context, exc: Exception) -> None:
    if self._error_handler is not None:
        try:
            await self._error_handler(ctx, exc)
        except Exception as inner:
            self._log(f"Exception raised inside error handler: {inner}")
    else:
        self._log(f"Unhandled exception: {exc}")
```

**الملاحظات:**

`_log()` يستقبل `str` فقط ويستدعي `_log.info(msg)` — بدون `exc_info`، بدون `stack_info`. `logging.info()` مع string لا يُضمّن traceback حتى لو كان هناك active exception في الـ context.

النتيجة:

| المسار | ما يُطبع |
|---|---|
| لا error handler مسجَّل | `"Unhandled exception: <str(exc)>"` فقط |
| استثناء داخل error handler | `"Exception raised inside error handler: <str(inner)>"` فقط |

في كلا المسارين: اسم الخطأ ورسالته فقط — لا call stack، لا ملف، لا سطر.

---

## 4. الفجوة المعمارية الحقيقية

### ما تحله Titan بشكل صحيح

- **ضمان وصول الاستثناء:** كل استثناء يصل لـ `_handle_error` بضمان بنيوي.
- **حماية error handler نفسه:** الاستثناء داخله لا يُوقف البوت ولا يمر صامتاً.
- **لا `BaseException` مُبتلَع:** الكود يستخدم `except Exception` بشكل صحيح.

### الفجوة الفعلية

**Titan تضمن وصول الاستثناء إلى `_handle_error`، لكنها لا تضمن وصول السياق التشخيصي الكامل في مسار الـ fallback.**

مسار الـ fallback — أي غياب `_error_handler` المسجَّل — هو المسار الطبيعي أثناء التطوير. وهو المسار الذي يفقد فيه Titan المعلومات الأكثر أهمية لتشخيص الخطأ: الـ traceback الكامل المتضمن في `exc.__traceback__`.

هذه ليست فجوة في **ضمان الوصول** — بل في **اكتمال السياق** بعد الوصول.

---

## 5. ما لا يُعدّ فجوة

**`asyncio.create_task` بدون `add_done_callback`:** بما أن `_handle_update` مُلفَّف بالكامل، لن ترمي الـ tasks استثناءات خارج نطاقها في الكود الحالي. إضافة callbacks تزيد تعقيداً بلا عائد حقيقي.

**`_chat_worker` بدون try/except خاص:** دوره محدود — لا معالجة منطقية تُنتج استثناءات متوقعة.

**عدم وجود timeout مدمج للـ handlers:** قرار نطاق موثَّق سابقاً.

---

## 6. القرار: **Adapt**

**ليس Reject:** الفجوة ليست قراراً تصميمياً واعياً. فقدان السياق التشخيصي في مسار الـ fallback لا يُقدّم أي ميزة هندسية — هو تقصير في المعلومات المتاحة للمطور.

**ليس Adopt:** البنية الأساسية سليمة. لا إعادة تصميم معمارية مطلوبة. الفجوة في مسار محدود وضيّق.

**Adapt:** يجب ألا يقتصر مسار الـ fallback في `_handle_error` على `str(exc)` وحده، بل يجب أن يوفر معلومات تمكّن المطور من تحديد موضع الخطأ في كوده دون الحاجة لإضافة error handler مسجَّل.

---

## 7. Implementation Note

*(هذا القسم وصفي — آلية التنفيذ تُقرَّر عند التنفيذ، لا هنا)*

الفجوة تقع في مسار واحد: `_handle_error` عند غياب `_error_handler`. التعديل لا يغير:
- واجهة `@bot.error_handler` ولا signature الـ error handler المسجَّل.
- بنية `_handle_update` ومسارات الـ try/except.
- سلوك الـ tasks والـ workers.
- أي شيء في العقد العام بين Titan والمطور.

**CONTRACT.md:** التعديل لا يغير semantics ولا العقد العام — وصول الاستثناء لـ `_handle_error` مضمون سابقاً ومضمون لاحقاً. السياق التشخيصي في مسار الـ fallback هو تفصيل تنفيذي لا يحتاج تحديث CONTRACT.

---

*وثيقة تحقيق — تتطلب مراجعة واعتماد القرار قبل أي تنفيذ.*
