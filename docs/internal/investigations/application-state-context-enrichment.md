# تحقيق #8 — Application-level State & Context Enrichment

**التاريخ:** 2026-07-24
**الحالة:** مكتمل — قرار: **Reject** — **معتمد**
**النطاق:** تحليل ما إذا كان غياب آليات مدمجة لتخزين الحالة وإثراء السياق يمثل فجوة معمارية حقيقية في Titan، أو قرار تصميم واعٍ.

---

## 1. المشكلة كما تظهر في الاستخدام الحقيقي

### الأعراض الأكثر تكراراً في PTB وaiogram

**العرَض الأول — "كيف أمرر جلسة قاعدة البيانات لكل handler؟"**
مطور يريد استدعاء `db.get_user(ctx.user_id)` في كل handler دون تكرار منطق الاتصال. يبحث عن مكان "يُعدّ" السياق قبل وصول الـ handler.

**العرَض الثاني — "كيف أحفظ بيانات المستخدم بين الرسائل؟"**
مطور يريد تذكّر آخر اختيار للمستخدم أو إعداداته المفضّلة عبر updates متعددة. يبحث عن تخزين مدمج مرتبط بـ `user_id` أو `chat_id`.

**العرَض الثالث — "كيف أتجنب إعادة جلب بيانات المستخدم في كل handler؟"**
مطور يستدعي `db.get_user()` في خمسة handlers مختلفة. يريد جلبها مرة واحدة ووضعها "في مكان مشترك" وصوله سهل من جميع الـ handlers.

### ما أنتجته هذه الأعراض في الأطر الناضجة

- **PTB:** أضاف `context.user_data` (dict مرتبط بـ user_id)، `context.chat_data`، `context.bot_data`، مع طبقة persistence اختيارية (`BasePersistence`) لدعم التخزين الدائم عبر Redis أو SQLAlchemy. الكلاس `ContextTypes` يسمح للمطور بتوسيع `Context` بكلاسات مخصصة.
- **aiogram:** `Dispatcher` يُمرّر `data: dict` لكل handler — middleware يُحقن فيه أي بيانات (جلسة DB، كائن مستخدم، إعدادات). الـ handler يُعلن ما يحتاجه بالاسم كـ keyword argument. `FSMContext` للحالة المرتبطة بالمحادثة.
- **النمط المشترك:** كلا الإطارين يحلّان مشكلتين اعتُبرتا واحدة: **التخزين عبر Updates** (state persistence) و**الحقن في السياق لكل Request** (per-request enrichment). تمييز هذين الجذرين هو جوهر هذا التحقيق.

---

## 2. الجذر المعماري

### مسألتان مختلفتان يجمعهما الاسم

**المسألة أ — State Persistence (الحالة عبر Updates)**
بيانات تحتاج أن تعيش بين رسائل متعددة: إعدادات المستخدم، آخر اختياراته، عداد تفاعلاته. الجذر: **أين تعيش هذه البيانات وكيف تُسترجع؟**

**المسألة ب — Per-request Context Enrichment (إثراء السياق لكل طلب)**
بيانات تُجلب لكل update وتُتاح لكل handler: كائن المستخدم من قاعدة البيانات، جلسة HTTP، feature flags. الجذر: **كيف تصل هذه البيانات للـ handler دون تكرار جلبها في كل مكان؟**

**الفارق الجوهري:**
المسألة أ مشكلة استمرارية (persistence) — تحتاج storage.
المسألة ب مشكلة تدفق (flow) — تحتاج نقطة حقن قبل الـ handler.

---

## 3. تحليل Titan — الكود والعقد الفعلي

### 3.1 المسألة أ — State Persistence في Titan

لا يوجد في Titan:
- `user_data` / `chat_data` / `bot_data` — لا في `ctx`، لا في `Titan`.
- طبقة persistence مدمجة.
- Storage interface أو protocol للمطور لتوصيل قاعدة بياناته.

ما يوجد:
- **`UserDataRegistry`** في `bot.py` — ليس تخزين حالة عام. هو آلية GDPR: يعرف أي modules تحتفظ ببيانات المستخدمين وكيف تُمحى (`/forgetme`، `erase_user()`). CONTRACT يُعرّفه صراحةً كـ privacy compliance، لا state management.
- **`ask()` coroutine** — يخزّن حالة المحادثة في الـ call stack (coroutine suspension)، لا في storage خارجي. CONTRACT §6: `"No persistence — pending asks are lost on bot restart"` — حد نطاق مُصرَّح به.
- **`bot.offset`** — CONTRACT §3: `"bot.offset available for persistence"` — exposed للمطور كمرجع، لا كآلية تخزين مدمجة.

**الخلاصة للمسألة أ:** Titan يُعلن صراحةً أن التخزين مسؤولية المطور. هذا قرار نطاق موثَّق في CONTRACT، ليس غفلة.

### 3.2 المسألة ب — Per-request Context Enrichment في Titan

السؤال الفعلي: **هل يمكن للمطور جلب بيانات مرة واحدة في middleware ووضعها في ctx ليقرأها الـ handler؟**

**ما يقوله CONTRACT §5 حرفياً:**

تحت **Forbidden usage:**
```
- Plugin systems
- Behavior injection into ctx
- Overriding handler routing logic
- Dynamic execution modification beyond next()
```

تحت **Allowed usage:**
```
- Request preprocessing (e.g. normalization)
```

**هل "Behavior injection" يشمل Data injection؟**

"Behavior injection into ctx" لا يُعرَّف في CONTRACT بمثال أو توصيف. النظر في السياق المحيط يُعطي مؤشراً: بقية العناصر في قائمة Forbidden (`Plugin systems`، `Overriding handler routing logic`، `Dynamic execution modification`) تتعلق جميعها بتغيير *كيفية عمل النظام* — إضافة قدرات، تغيير مسار التنفيذ، تعديل سلوك البنية. السياق المحيط يتعلق بالقدرات والسلوك، لكنه لا يُعرِّف مصطلح "Behavior injection" تعريفاً صريحاً، ولا يكفي لحسم ما إذا كانت العبارة تشمل بيانات التطبيق أيضاً.

مقابل ذلك، `"Request preprocessing (e.g. normalization)"` مسموح به — والتطبيع (normalization) يمكن أن يشمل استخراج بيانات وتعيينها على ctx كجزء من إعداد الطلب.

النص صريح في حالة واحدة فقط: `"middleware reads ctx.is_banned — it does not write to it"` — هذا قيد خاص بـ `is_banned`، لا قاعدة عامة على كل attributes.

**الخلاصة:** CONTRACT لا يُثبت ولا ينفي صراحةً أن `ctx.user = await db.get_user(ctx.user_id)` ممنوع. هذا غموض حقيقي: النمط قد يقع تحت "preprocessing" المسموح أو تحت "behavior injection" الممنوع — العقد لا يُحسم الأمر.

### 3.3 هل ctx يمنع الإثراء تقنياً؟

`Context` لا تستخدم `__slots__`. أي middleware يستطيع كتابة `ctx.user_profile = await db.get_user(ctx.user_id)` والكود لن يكسر. الحاجز ليس تقنياً — هو غموض في تفسير العقد.

---

## 4. تحليل المسألتين

### المسألة أ — State Persistence

**هل الجذر المعماري موجود في Titan؟** لا — الغياب مقصود ومُعلَن.

**هل هذا فجوة تستدعي تدخلاً؟**

CONTRACT يُصرَّح بغياب persistence في `ask()` كحد نطاق. `UserDataRegistry` موجود لـ privacy، لا لـ state. لا ادعاء بدعم state storage مدمج في أي وثيقة.

مقارنة مع PTB: PTB أضاف `user_data` لأن جمهوره يبني بوتات إنتاجية تحتاج persistence. Titan في مرحلة مختلفة من النطاق — والمطور يملك storage خاصه (Redis، SQLite، dict في الذاكرة). إضافة storage مدمج تعني اختيار backend، API، وسياسة حياة البيانات — قرارات لا تُحسم قبل وجود ضغط استخدام حقيقي.

**الخلاصة:** Reject — قرار نطاق واعٍ مُصرَّح به.

### المسألة ب — Per-request Context Enrichment

**ما أثبته التحقيق في Titan:** لا توجد آلية رسمية موثَّقة لإثراء ctx ببيانات التطبيق، لكن الكود يسمح بذلك تقنياً، والعقد لا يُحسم موقفه — لا بالإجازة ولا بالمنع.

**هل هذا فجوة تستدعي تدخلاً؟**

CONTRACT §5 يُحدد "Behavior injection into ctx" كـ Forbidden، و"Request preprocessing" كـ Allowed. لكن كما وضّح قسم 3.2، "Behavior injection" لا يُعرَّف بمثال، وسياقه المحيط يُشير إلى إضافة قدرات وسلوك نظام — لا إلى تعيين بيانات على ctx. ولا يوجد في CONTRACT نص صريح يمنع `ctx.user = await db.get_user(ctx.user_id)` أو يُجيزه.

المطور الذي يريد كتابة هذا النمط يقف أمام غموض حقيقي لا يُحسمه العقد: هل يقع تحت "preprocessing" المسموح أم "behavior injection" الممنوع؟

**هل هذا الغموض فجوة معمارية؟**

لا — هو غموض في توثيق حد بين نمطَين. الآلية التقنية موجودة (ctx مفتوح للإثراء)، والعقد لا يُحسم الأمر في أي اتجاه. هذا يجعله ملاحظة توثيق، لا فجوة معمارية تستدعي Adapt.

---

## 5. ما لا يُعدّ فجوة

**غياب `user_data` / `chat_data`:** قرار نطاق واعٍ. الـ developer يملك storage.

**غياب `ContextTypes` pattern (PTB):** يُعقّد API بدون ضغط استخدام يُبرره في نطاق Titan الحالي.

**غياب aiogram-style data injection:** aiogram يُحقن البيانات بـ keyword arguments في الـ handler signature (`async def handler(message, user: User, session: AsyncSession)`). هذا يتطلب dependency injection system مختلفاً جذرياً عن نموذج Titan (`async def handler(ctx)`).

---

## 6. القرار: **Reject**

**المسألة أ (State Persistence):** Reject — غياب storage مدمج قرار نطاق مُصرَّح به في CONTRACT. لا ادعاء بدعمه، ولا ضغط استخدام يُبرر تعقيد إضافته.

**المسألة ب (Context Enrichment):** Reject — التحقيق لم يثبت وجود فجوة معمارية. ما أثبته هو غموض في تفسير CONTRACT §5، وهو موضوع توثيق لا تصميم. الفارق مهم: "لم نجد مشكلة في التصميم" يختلف عن "وجدنا مشكلة في التوثيق" — والنتيجة الطبيعية لكليهما هنا Reject.

**لماذا Reject وليس Adapt في المسألة ب؟**

Adapt يستدعي فجوة معمارية مُثبَتة تحتاج تغييراً. هنا لا يمكن إثبات وجود فجوة في التصميم — ما وُجد غموض في حد بين نمطَين في العقد. الآلية التقنية موجودة، ولا نقص في البنية. إذا ظهر ضغط من مطورين يطلبون موقفاً صريحاً، يصبح الأمر مناسباً لإعادة تقييم.

**ملاحظة مفتوحة (توثيق، لا معمار):**
CONTRACT §5 يستفيد من مثال واحد يُوضح ما يعنيه "Behavior injection" — قدرات وسلوك نظام أم بيانات تطبيق أم كلاهما. جملة واحدة تُغلق الغموض دون تغيير أي قرار معماري.

---

*وثيقة تحقيق أولية — تتطلب مراجعة واعتماد القرار قبل أي تنفيذ.*
