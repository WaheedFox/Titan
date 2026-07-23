# Investigation #4 — Update Routing & Filtering

**التاريخ:** 2026-07-23  
**الحالة:** مكتمل — قرار: **Reject**  
**النطاق:** نموذج الـ routing الحالي في Titan ومقارنته بما أنتجه الاستخدام الحقيقي في الأطر الناضجة

---

## 1. المشكلة كما تظهر في الاستخدام الحقيقي

### الأعراض الأكثر تكراراً في PTB وaiogram

**العرَض الأول — "handler يصله كل شيء"**  
مطور يسجّل `on("message")` ويجد أن handler يُستدعى للصور والملفات والإيموجي والنصوص والـ forward والـ reply وكل ما يصل. يبدأ بكتابة سلسلة `if/elif/else` في أول كل handler.

**العرَض الثاني — "أريد نفس handler لكن بشروط مختلفة"**  
بوت يتعامل مع `/help` بطريقة في المجموعات وبطريقة أخرى في الخاص. المطور يسجّل handler واحداً ويكتب `if ctx.chat.type == "private"` في البداية — أو يسجّل اثنين ويكرّر المنطق.

**العرَض الثالث — "لا أريد middleware global بل أريد شرطاً لـ handler واحد فقط"**  
مطور يريد handler يعمل فقط في المجموعات. إذا استخدم middleware global، يؤثر على كل handlers الأخرى. إذا وضع الشرط في الـ handler نفسه، يختلط routing بـ business logic.

**نتيجة هذه الأعراض في الأطر الناضجة:**  
PTB بنى نظام `Filters` — كائنات قابلة للتركيب بـ `&`، `|`، `~` تُسجَّل عند تسجيل الـ handler. aiogram بنى `Magic Filters` (`F.text`, `F.chat.type == "group"`) تُرفق بالـ decorator. كلاهما وصل لهذا الحل من تراكم شكاوى المطورين عبر سنوات.

---

## 2. الجذر المعماري في PTB وaiogram

### نموذج الـ dispatch — الفارق الحقيقي

الشرط داخل الـ handler ليس الجذر. هو عَرَض لمشكلة أعمق تتصل بنموذج الـ dispatch نفسه.

**PTB وaiogram يعتمدان first-match exclusive dispatch:** عند وصول update، يُفحص كل handler مسجَّل بالترتيب، ويُشغَّل **الأول الذي يطابق** ثم يتوقف التسلسل. بدون predicates عند التسجيل، الأداة لا تستطيع أن تُقرِّر "مَن يمتلك هذا الـ update" — أي لا يمكنها تطبيق الـ exclusivity.

Filters في هذا النموذج ليست ميزة إضافية — هي **شرط ضروري** لتشغيل نموذج first-match. بدونها، كل handler يتلقى كل update، وهذا ليس ما أراده الإطاران.

### الجانب الثاني — scoping تنظيمي على نطاق Router

aiogram بنى فوق Filters ما هو أوسع: `@router.message(F.chat.type == "group")` يُحدّد نطاق **router كامل** لا handler منفرد فقط. هذا يتيح وجود router مختص بالمجموعات وآخر بالخاص، كل منهما بـ middleware وسلوك مختلف. الـ Filters هنا أداة لحل مشكلة middleware granularity، لا الـ routing بحد ذاتها.

### ما أنتجه هذا في PTB وaiogram

- **PTB Filters:** predicates ضرورية لتشغيل نموذج first-match. `@app.message(filters.TEXT & filters.Regex(r"\d+"))` تُخبر الأداة "هذا الـ handler مسؤول عن النصوص المطابقة فقط" حتى يمكنها تجاوزه للـ handler التالي إذا لم تتحقق الشروط.
- **aiogram Magic Filters:** `@router.message(F.chat.type.in_({"group", "supergroup"}))` يحدد نطاق router — وهذا حل لمشكلة عزل الـ middleware، تُوظَّف فيه الـ Filters كأداة.
- **التكلفة:** DSL كامل، evaluation chain عند كل update، توثيق موسّع، إمكانية تعارض بين Filters.

---

## 3. تحليل Titan — الكود الفعلي

### 3.1 نموذج الـ routing الحالي

```python
# تسجيل handler لحدث — string key فقط
bot.on("message")       # كل الرسائل
bot.command("start")    # أمر محدد بالاسم
bot.callback("yes")     # callback_data بالقيمة الحرفية

# _dispatch — تشغيل كل handlers المسجّلة لهذا الـ event
async def _dispatch(self, event: str, ctx: Context) -> None:
    for handler in self.handlers.get(event, []):
        try:
            await handler(ctx)
        except Exception as e:
            await self._handle_error(ctx, e)
```

**الخصائص:**
- `on(event: str)` — string key فقط، لا predicate، لا شرط.
- `command(name: str)` — اسم الأمر بالضبط، واحد لكل اسم.
- `callback(data: str)` — قيمة `callback_data` بالضبط، واحد لكل قيمة.
- لا فلترة على chat_type، user_id، content_type، أو أي خاصية أخرى عند التسجيل.

### 3.2 ما يوفّره Titan لمن يحتاج شرطاً

**الخيار الأول — الشرط داخل الـ handler:**
```python
@bot.on("message")
async def h(ctx):
    if ctx.chat.type not in ("group", "supergroup"):
        return
    # ... المنطق الفعلي
```

**الخيار الثاني — middleware global:**
```python
@bot.middleware
async def group_only(ctx, next):
    if ctx.chat.type in ("group", "supergroup"):
        await next()
    # لا next() = handler لا يُستدعى
```

**القيد الحقيقي للخيار الثاني:** الـ middleware في Titan global — يؤثر على كل handlers دون استثناء. لا يوجد per-handler أو per-router middleware. هذا يجعل خيار ٢ غير قابل للاستخدام إلا للشروط التي يجب تطبيقها على جميع الـ handlers.

### 3.3 Router — هل يضيف عزلاً؟

```python
# Router في Titan هو تنظيمي بحت
class Router:
    def on(self, event: str): ...
    def command(self, name: str): ...
    def callback(self, data: str): ...
    # لا middleware، لا فلترة، لا عزل
```

`bot.include(router)` يدمج handlers الـ Router في قواميس الـ bot مباشرةً. بعد الدمج لا يوجد أثر للـ Router — كل handlers تعمل على نفس الـ pipeline.

---

## 4. هل المشكلة موجودة في Titan؟

**نعم، بنفس الشكل الذي ظهر في PTB وaiogram قبل إضافة Filters.**

`on("message")` يستقبل كل رسالة بلا استثناء. أي تمييز — نوع المحتوى، نوع المحادثة، هوية المستخدم، بنية النص — يجب أن يحدث داخل الـ handler أو عبر middleware global.

**لكن هل أنتجت هذه المشكلة نفس الضغط في Titan؟**

هذا هو السؤال الجوهري.

---

## 5. قراءة الضغط الحقيقي

### ما الذي دفع PTB وaiogram لبناء Filters؟

الضغط لم يأتِ من بوتات بسيطة — تلك تعمل بـ `on("message")` + `if/else` بلا مشكلة. الضغط جاء من:

1. **بوتات متعددة الأدوار:** تخدم admin وuser وstranger بسلوك مختلف في نفس الوقت — عشرات الـ handlers بشروط متقاطعة.
2. **فرق متعددة:** كل مطور يكتب handler مستقل ويحتاج أن يُصرّح بشرطه عند التسجيل لا في داخل الكود.
3. **اختبار الـ routing مستقلاً:** Filters قابلة للاختبار كوحدات مستقلة عن الـ handlers.

### ما هو النطاق الحالي لـ Titan؟

- بوتات single-developer أو فرق صغيرة.
- سيناريوهات routing محدودة النطاق في الكود الحالي.
- لا Filters system، لا DSL، لا per-router middleware — هذا قرار نطاق واعٍ.
- التوثيق والنطاق لا يُشيران لاستهداف البوتات ذات الـ routing المعقد.

### هل الـ workarounds الحالية تُنتج "ossification"؟

الـ workaround الرئيسي (شرط في الـ handler) يُنتج:
- خلط routing بـ business logic — مشكلة تنظيمية، لا معمارية في هذا النطاق.
- لا تداخل، لا race condition، لا حالة مخفية — مجرد if في أول السطر.

هذا مختلف جذرياً عن ConversationHandler الذي أنتج race conditions حقيقية، أو عن fallthrough الـ dispatch الذي أرسل updates للـ handler الخطأ.

---

## 6. التمييز الجوهري

| الجانب | PTB/aiogram | Titan |
|---|---|---|
| نموذج الـ routing | نوع الحدث + Filters predicates | نوع الحدث فقط |
| Filters | نظام كامل قابل للتركيب | لا يوجد |
| per-handler condition | عند التسجيل | داخل الـ handler أو middleware global |
| ضغط الاستخدام الذي أنتجه | بوتات كبيرة، فرق متعددة | لم يظهر بعد في Titan's scope |
| التكلفة المعمارية لإضافته | DSL، evaluation chain، تعقيد التوثيق | — |

---

## 7. ما لا يُعدّ فجوة

**غياب Filters system:** لا يوجد ضغط استخدام حقيقي يُثبت أن غياب Filters أنتج مشكلة معمارية في Titan بنطاقه الحالي. الـ workaround (شرط في الـ handler) مرئي لكن غير مؤلم في هذا النطاق.

**غياب content_type routing:** `on("message")` يستقبل كل أنواع المحتوى. هذا قرار تصميم واعٍ — المطور يُميّز في handler body. لم تُنتج هذه القيود أي أنماط broken في الكود الحالي.

**قيد per-handler middleware:** هذا قيد حقيقي، لكنه ينتمي لـ Middleware Granularity (التحقيق التالي)، لا لـ Routing & Filtering.

---

## 8. القرار: **Reject**

**الجذر المعماري موجود:** نموذج routing يعرف نوع الحدث فقط يُجبر كل تمييز آخر على الانتقال لـ handler body. هذا هو بالضبط الجذر الذي دفع PTB وaiogram لبناء Filters.

**لكن الضغط الذي يُحوِّل هذا الجذر إلى مشكلة معمارية لم يظهر في Titan بعد.** الـ workarounds المتاحة (شرط في الـ handler، middleware global) تُغطي نطاق Titan الحالي دون أن تُنتج patterns مكسورة أو تعقيداً متراكماً.

إضافة Filters system اليوم تعني:
- تعقيد API بـ DSL لا يوجد ضغط استخدام يُبرّره حالياً.
- إضافة evaluation overhead عند كل update.
- توسيع نطاق Core لمشكلة قد لا تظهر في الـ bots التي يُستهدف Titan لبنائها.

**Reject ليس إغلاقاً دائماً:** إذا ظهر في المستقبل استخدام حقيقي يُثبت أن المطورين يتجاوزون `on("message")` بطرق تُنتج تعقيداً متراكماً، تستحق المسألة إعادة فتح. لكن ذلك يُبدأ من الاستخدام الحقيقي، لا من "PTB يدعم هذا."

---

*وثيقة تحقيق أولية — تتطلب مراجعة واعتماد القرار قبل أي تنفيذ.*
