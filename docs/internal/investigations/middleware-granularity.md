# تحقيق #5 — Middleware Granularity

**التاريخ:** 2026-07-23
**الحالة:** مكتمل — قرار: **Reject**
**النطاق:** تحليل ما إذا كان نموذج الـ middleware الحالي في Titan — global وlinear — يُنتج مشاكل معمارية حقيقية قياساً بما واجهته الأطر الناضجة.

---

## 1. المشكلة كما تظهر في الاستخدام الحقيقي

### الأعراض الأكثر تكراراً في PTB وaiogram

**العرَض الأول — "middleware يؤثر على handlers لا أريده أن يصلها"**
مطور يسجّل middleware للتحقق من صلاحيات المجموعات. يجد أن بوته الخاص (`private`) توقف عن الاستجابة لأن الـ middleware يحجب كل شيء بدلاً من المجموعات فقط. يضيف `if ctx.chat.type == "private": await next(); return` في أول الـ middleware — وتتكرر هذه الإضافات مع كل middleware جديد.

**العرَض الثاني — "أريد logging لكل handlers، لكن rate-limiting لـ group handlers فقط"**
مطور يحتاج middleware مختلفة لأجزاء مختلفة من البوت. النتيجة: middleware واحد ضخم يحتوي سلسلة `if/elif` تُقرِّر لكل حدث أي منطق يُطبَّق.

**العرَض الثالث — "لا أعرف كيف أُنفِّذ كوداً بعد انتهاء الـ handler"**
مطور يريد قياس وقت تنفيذ الـ handler (timing metrics). لا يعرف أين يضع الكود الذي يعمل "بعد" الـ handler. يصل في النهاية إلى workaround مخصص أو يتخلى عن الفكرة.

**العرَض الرابع — "middleware في router لا يؤثر على handler في router آخر"**
هذا الأثر مطلوب في aiogram: فرق تعمل على routers منفصلة ولا تريد middleware أحدها أن يؤثر على الآخر. PTB لم يكن يملك هذه الإمكانية في الإصدارات الأولى، مما أنتج `ConversationHandler` مخصص بمنطق middleware مدمج.

### ما أنتجه هذا في الأطر الناضجة

- **الأطر الناضجة** واجهت الحاجة إلى فصل نطاق التنفيذ بطرق مختلفة، ووصل بعضها إلى مستويات middleware متعددة. **aiogram 3.x** مثلاً بنى نموذجاً ثلاثي المستويات:
  - **Outer middleware:** يُنفَّذ قبل الـ routing وبعده — يرى كل update بغض النظر عن وجود handler.
  - **Inner middleware:** يُنفَّذ فقط إذا وُجد handler مطابق — يعمل كـ "guard" للـ handler.
  - **Per-router middleware:** كل router له سلسلة middleware مستقلة — isolation حقيقي.

الضغط الذي دفع aiogram لهذا التعقيد كان واضحاً: فرق كبيرة، بوتات متعددة الأدوار، وحاجة لعزل middleware في السياق.

---

## 2. الجذر المعماري في PTB وaiogram

### المشكلة الجوهرية: middleware يعمل بدون سياق routing

في نموذج middleware global، الـ middleware تُنفَّذ **قبل** أن يُقرَّر أي handler سيُشغَّل. هذا يعني:

- الـ middleware لا تعرف: هل سيُشغَّل أي handler أصلاً؟ وأيٌّ منها؟
- أي شرط على "نوع الـ handler أو نطاقه" يجب كتابته داخل الـ middleware نفسها.
- يُنتج هذا: خلط routing logic بـ middleware logic — المشكلة نفسها التي أُريد للـ middleware أن تُحلّها.

**الجذر الموحَّد:** middleware التي تعمل في **vacuum routing** — بدون معرفة بالـ handler الذي سيُشغَّل — تُعيد استيراد قرارات routing إلى جسدها. كلما كبر البوت، كبر هذا الخلط.

### ما أنتجه هذا في aiogram

aiogram حلّ المشكلة بتفكيك middleware إلى مستويين بحسب **وقت التنفيذ قياساً بالـ routing:**

- **Outer middleware:** يعمل بغض النظر عن نتيجة الـ routing → مناسب للـ logging والـ metrics.
- **Inner middleware:** يعمل فقط عند وجود handler مطابق → مناسب للـ auth والـ rate-limiting المرتبطة بـ handler محدد.

هذا التفكيك يُعيد فصل الـ routing عن الـ middleware — كل مستوى يعرف متى يعمل وفيما يتعلق بماذا.

---

## 3. تحليل Titan — الكود الفعلي

### 3.1 نموذج MiddlewareChain

```python
class MiddlewareChain:
    def add(self, fn: Middleware) -> None:
        self._chain.append(fn)

    async def run(self, ctx: Context, handler: Callable[[], Awaitable[None]]) -> None:
        async def build(index: int) -> None:
            if index >= len(self._chain):
                await handler()
                return

            async def next_fn() -> None:
                await build(index + 1)

            await self._chain[index](ctx, next_fn)

        await build(0)
```

**الخصائص:**
- سلسلة خطية عالمية — كل middleware تُنفَّذ لكل update.
- نمط **onion كامل**: الكود بعد `await next()` داخل أي middleware يُنفَّذ **بعد** انتهاء الـ handler والـ middlewares اللاحقة.
- لا per-router، لا per-handler، لا outer/inner تفكيك.

### 3.2 نقطة جوهرية: post-handler middleware ممكنة وموجودة

```python
@bot.middleware
async def timer(ctx, next):
    import time
    start = time.monotonic()
    await next()               # handler يعمل هنا — وكل middleware التالية
    elapsed = time.monotonic() - start
    # هذا الكود يعمل بعد انتهاء الـ handler
```

هذا يعمل الآن في Titan بدون أي تغيير. نمط الـ onion الكامل متاح — لكنه غير موثَّق بوضوح.

**الـ AskManager يثبت هذا:** middleware تعترض بعض الرسائل (`return` بدون `next()`) وتمرر غيرها (`await next()`). الآلية نفسها تدعم post-handler code.

### 3.3 Router — لا middleware

```python
class Router:
    """
    أداة تنظيم handlers عبر ملفات متعددة.
    لا يحتوي على أي منطق تنفيذي.
    لا middleware، لا nested routers، لا priorities.
    """
    def __init__(self) -> None:
        self.commands: dict[str, Handler] = {}
        self.handlers: dict[str, list[Handler]] = {}
        self.callback_handlers: dict[str, Handler] = {}
```

بعد `bot.include(router)`، تُدمج handlers الـ Router في قواميس البوت مباشرةً. الـ Router لا وجود له في وقت التنفيذ.

### 3.4 الـ workaround الحالي

عندما يريد مطور middleware تنطبق فقط على حالات معينة:

```python
@bot.middleware
async def group_only_guard(ctx, next):
    if ctx.chat.type not in ("group", "supergroup"):
        await next()  # لا تؤثر على private
        return
    # منطق المجموعة هنا
    await next()
```

هذا يعمل، لكنه يخلط routing condition بـ middleware logic. مع تراكم الـ middlewares، تُصبح كل واحدة منها تحتوي شروطاً routing.

---

## 4. هل المشكلة موجودة في Titan؟

**نعم، الجذر المعماري موجود:** middleware global لا تعرف بالـ handler الذي سيُشغَّل — أي شرط على نطاق التطبيق يُكتب داخل الـ middleware.

**لكن هل أنتجت هذه المشكلة ضغطاً فعلياً في Titan؟**

للإجابة على هذا، يجب فهم متى يتحول الجذر إلى مشكلة معمارية حقيقية.

---

## 5. قراءة الضغط الحقيقي

### ما الذي دفع aiogram لبناء outer/inner/per-router middleware؟

الضغط جاء من سيناريوهات محددة:

1. **بوتات كبيرة متعددة الأدوار:** admin panel + user interface + payment flow — كل نطاق له متطلبات middleware مستقلة.
2. **فرق متعددة:** كل فريق يطور router مستقل ولا يريد middleware فريق آخر تؤثر على عمله.
3. **عزل الاختبار:** middleware per-router يسمح باختبار كل router باستقلالية كاملة.

### ما هو النطاق الحالي لـ Titan؟

- بوتات single-developer أو فرق صغيرة.
- في الاستخدام الحالي: middleware لا تزيد عن 2-3 في البوتات المعقدة (AskManager + AliasMap + guard واحد أو اثنان).
- لا حالة موثَّقة أنتجت فيها قيود الـ middleware شيفرة مشكوكاً في صحتها أو مستحيلة التطور.

### هل الـ workarounds تُنتج "ossification"؟

الـ workaround الرئيسي (شرط في الـ middleware) يُنتج:
- خلطاً بين routing condition وmiddleware logic — مشكلة تنظيمية.
- لا تداخل، لا race condition، لا حالة مخفية.

هذا مشابه لما وجدناه في تحقيق #4 (Routing & Filtering): الجذر موجود، لكن أثره في هذا النطاق تنظيمي لا معماري.

---

## 6. التمييز الجوهري

| الجانب | aiogram | Titan |
|---|---|---|
| نموذج middleware | outer / inner / per-router | global linear (onion) |
| post-handler code | inner middleware (بعد handler) | ممكن بالكامل عبر كود بعد `await next()` |
| per-handler scope | inner middleware predicates | شرط داخل الـ middleware |
| per-router isolation | per-router middleware chain | غير موجود |
| الضغط الذي أنتج التعقيد | بوتات كبيرة، فرق متعددة | لم يظهر بعد في Titan's scope |
| تكلفة الإضافة | تعقيد API + توثيق + تغيير Router architecture | — |

---

## 7. ما لا يُعدّ فجوة

**غياب post-handler middleware:** هذه الإمكانية موجودة فعلاً في Titan عبر نمط الـ onion. `await next()` يُعلِّق الـ middleware حتى ينتهي الـ handler — الكود بعده هو بالتعريف post-handler. المشكلة توثيق، لا معمار.

**غياب inner middleware:** في نموذج first-match-exclusive (aiogram)، inner middleware ضروري لأن الـ routing تُقرِّر من يُنفِّذ. في نموذج Titan — حيث `on("message")` يُشغِّل كل handlers المسجلة لهذا الحدث — مفهوم "handler محدد تُطبَّق عليه فقط" يتطلب تغيير نموذج dispatch، لا middleware فقط.

**غياب per-router middleware:** وهذا ليس نقصاً عرضياً، بل نتيجة مباشرة لكون Router في Titan يمثل وحدة تنظيم وتسجيل فقط وليس وحدة runtime isolation. الإضافة تتطلب أن يظل الـ Router موجوداً وقت التنفيذ بدلاً من الذوبان في البوت عند `include()` — وهذا تغيير في هوية Router نفسه، لا مجرد إضافة واجهة.

---

## 8. مشاهدة تستحق التوثيق

### AskManager كمثال على middleware الأمثل في Titan

```python
async def _middleware(ctx, next):
    if self._pending_futures_exist(ctx):
        answer = ctx.message.text or ""
        future.set_result(answer)
        return                 # تستهلك الرسالة — لا next()
    await next()               # تمرّر للـ pipeline العادي
```

هذا النمط — middleware تقرر استهلاك أو تمرير بناءً على حالة ديناميكية — يُمثِّل نموذج "outer middleware" بأبسط تمثيل ممكن. لا تفكيك مستويات، لا DSL — مجرد شرط + next.

الجذر الذي يحتاجه aiogram لـ outer/inner middleware (التمييز بين "هل يوجد handler مطابق؟") لا يوجد في Titan لأن نموذج dispatch مختلف.

---

## 9. القرار: **Reject**

**الجذر المعماري موجود:** middleware global لا تعلم بالـ handler الذي سيُشغَّل، وأي شرط على نطاق التطبيق يُكتب داخلها. هذا هو بالضبط الجذر الذي دفع aiogram لبناء outer/inner/per-router middleware.

**لكن الضغط الذي يُحوِّل هذا الجذر إلى مشكلة معمارية لم يظهر في Titan بعد.** الـ workarounds (شرط في الـ middleware) تُغطي نطاق Titan الحالي دون أن تُنتج patterns مكسورة أو تعقيداً متراكماً.

إضافة per-router middleware أو تفكيك outer/inner اليوم تعني:
- تغيير جوهري في معمار Router (يجب أن يظل موجوداً وقت التنفيذ بدلاً من الذوبان).
- تعقيد API بمستويات لا يوجد ضغط استخدام يُبرّرها حالياً.
- توسيع نطاق Core لمشكلة لا تُقلق المطور الذي يُستهدف Titan لخدمته.

**Reject ليس إغلاقاً دائماً:** إذا ظهر في المستقبل استخدام حقيقي يُثبت أن المطورين يُنتجون middleware ضخمة ومتشابكة بسبب غياب الـ per-router isolation، تستحق المسألة إعادة فتح. لكن ذلك يُبدأ من الاستخدام الحقيقي، لا من "aiogram يدعم هذا."

**Implementation note (غير تعاقدية):** يستحق توثيق إمكانية post-handler middleware (كود بعد `await next()`) بشكل صريح في الوثائق أو في `CONTRACT.md` — لأن هذه الإمكانية موجودة فعلاً ولكن غير معروفة بوضوح لكثير من المطورين.

---

*وثيقة تحقيق — القرار: Reject. لا تغيير مطلوب في التصميم الحالي.*
