# تحقيق — Design Linter

**الحالة:** مفتوحة — في انتظار قرار معماري
**تاريخ:** 2026-07-11
**الميزة:** Design Linter (#6) — من قائمة Planned

---

## 1. المشكلة

**من منظور المطور:**
> "كتبت بوتاً يعمل، لكنني لا أعرف إن كنت أستخدم Titan بالطريقة الصحيحة."

Titan لديه فلسفة معمارية صريحة موثّقة في CONTRACT.md وdesign_notes.md:
- `ctx` هي السطح الأساسي داخل الـ handler — الوصول لـ `bot.telegram` من داخل handler إشارة خطأ
- Middleware مسؤوليتها تدفق التنفيذ فقط — أي منطق تجاري فيها انتهاك
- escape hatches (`ctx.raw`, `model.raw`) للقراءة الاضطرارية — لا للبناء الدائم
- أسماء الأوامر lowercase بالاتفاقية
- `on_offset` دالة sync فقط — async تُنشئ coroutine وتُهمَل بصمت (موثق في roadmap "قيد الدراسة")

**الوضع الحالي:** هذه القواعد موجودة في التوثيق، غير مُنفَّذة في الكود.
المطور ينتهكها دون علم، والنتيجة إما صمت تام أو خطأ بعيد عن مصدره.

---

## 2. الأدوات الموجودة — أين يقع Design Linter بينها؟

الفصل الدقيق ضروري لتجنب التداخل مع ما بُني سابقاً:

| الأداة | السؤال الذي تجيب عليه | الوقت | المدخل |
|---|---|---|---|
| **Runtime Contract Validator** (ADR-009) | هل التوقيع (signature) صحيح؟ | عند التسجيل (import time) | callable |
| **Project Health** (ADR-005) | هل البوت مكتمل هيكلياً؟ | بعد التسجيل | حالة bot المُجمَّعة |
| **Interactive Inspector** (ADR-006) | ماذا يحتوي البوت؟ (وصف، لا حكم) | بعد التسجيل | حالة bot المُجمَّعة |
| **Design Linter (#6)** | هل البوت يتبع اتفاقيات Titan؟ | ؟ | ؟ |

**Design Linter يملأ فراغاً حقيقياً:** لا أداة من الثلاث السابقة تفحص *الاتفاقيات*، فقط البنية أو التوقيع.

---

## 3. القواعد المرشحة — ما الذي يمكن فحصه فعلاً؟

### 3أ. قواعد قابلة للفحص وقت التسجيل (registration time)

| الانتهاك | مثال | الكشف |
|---|---|---|
| اسم أمر يحتوي أحرفاً كبيرة | `@bot.command("Start")` | فحص `name.lower() != name` |
| اسم أمر يحتوي مسافات أو أحرف خاصة | `@bot.command("my bot")` | regex بسيط |
| callback_data فارغة أو whitespace فقط | `@bot.callback("")` | فحص `not data.strip()` |
| `on_offset` async callable | `bot.on_offset = async_fn` | `asyncio.iscoroutinefunction(fn)` |

هذه القواعد لا تحتاج AST — تُفحص مباشرة من المُدخَلات المتاحة لحظة التسجيل.

### 3ب. قواعد قابلة للفحص من الحالة المُجمَّعة (post-registration)

| الانتهاك | مثال | الكشف |
|---|---|---|
| عدد كبير من fan-out handlers لحدث واحد | `>N` handlers على `"message"` | عد `bot.handlers["message"]` |
| router مضمّن بدون أي handler مسجّل فيه | `bot.include(empty_router)` | فحص `len(router.commands) == 0` |

### 3ج. قواعد تتطلب AST (تحليل الكود المصدري)

| الانتهاك | المثال الحرفي | المشكلة |
|---|---|---|
| `bot.telegram.*` داخل handler | `await bot.telegram.send_message(...)` داخل `async def on_msg(ctx)` | يتطلب تحليل AST لمعرفة سياق الاستدعاء |
| `ctx.raw` في منطق دائم | `if ctx.raw["message"]["entities"]` دائماً | يتطلب AST + data flow |
| منطق تجاري داخل middleware | `await db.save(ctx.user_id)` داخل middleware | يتطلب AST + heuristics |

هذه القواعد **غير قابلة للكشف وقت التشغيل** بدون تحليل ثابت للكود.

---

## 4. التوترات المعمارية الحقيقية

### التوتر 1 — Python API مقابل CLI/AST tool

**الخيار أ: `bot.lint()` — Python API**
تتبع نفس نمط `bot.health()` و`bot.inspect()`.
- ✅ متسق مع الفلسفة الحالية (كل شيء API، لا تبعيات خارجية)
- ✅ لا تبعيات جديدة — صفر `pip install`
- ✅ قابل للاستهلاك من Playground، Architect AI، CI
- ❌ محدود بما يُكشَف في runtime — القواعد 3ج (الأكثر قيمة) غير متاحة
- ❌ قد يتداخل مع `bot.health()` في الشعور — فصل المسؤولية يحتاج صياغة واضحة

**الخيار ب: flake8/ruff plugin أو CLI tool مستقل**
يحلل الكود بالـ AST، يكشف كل قواعد 3أ و3ب و3ج.
- ✅ يكتشف أعمق انتهاكات
- ❌ تبعيات خارجية (flake8/ast) تناقض "minimal core"
- ❌ خارج نمط Titan الثابت (كل شيء Python API حتى الآن)
- ❌ يتطلب تكامل CI منفصل عن Python code عادي
- ❌ كاشف كود المطور، لا كاشف تهيئة البوت — حدود مختلفة

**الخيار ج: API للقواعد القابلة للتشغيل + توثيق للقواعد الأخرى**
`bot.lint()` يُعيد نتائج القواعد 3أ+3ب، والقواعد 3ج تُوثَّق كـ "design guidelines" لا كـ runtime checks.
- ✅ واقعي ومتسق
- ✅ لا يعد بما لا يستطيع تقديمه
- يثير سؤالاً: هل "Design Linter" بدون القواعد الأعمق مفيد بما يكفي؟

---

### التوتر 2 — ما الفرق الحقيقي بين `bot.lint()` و`bot.health()`؟

**`bot.health()` يفحص:** هل البنية مكتملة؟ (handlers مفقودة، error handler غائب)
**`bot.lint()` يفحص:** هل الاتفاقيات محترمة؟ (أسماء، patterns، anti-patterns)

الأمثلة تجعل الفرق واضحاً:
- بوت بلا error handler → `health()` يُبلّغ، `lint()` لا يعلم
- أمر اسمه `"Start"` بدلاً من `"start"` → `lint()` يُبلّغ، `health()` لا يعلم
- `on_offset` async → يناسب `lint()` أكثر من `health()` (ليست مشكلة بنيوية، بل استخدام خاطئ)

الحدود واضحة ومتمايزة. الخطر الوحيد هو `LintFinding` مقابل `HealthFinding` — هل نستخدم نفس نوع البيانات؟

---

### التوتر 3 — وقت التنفيذ: هل نُفعِّل فحوص 3أ فوراً أم نجمعها لـ `bot.lint()`؟

الفحوص في 3أ (اسم الأمر، callback_data، on_offset) يمكن تشغيلها وقت التسجيل مثل Contract Validator تماماً. هذا يعني:
- `@bot.command("Start")` → `TitanError` فوري (مثل Contract Validator)

**مقابل:** جمعها في `LintFinding` قابل للاستعلام عبر `bot.lint()`.

السؤال: هل القاعدة "convention" أم "error"؟
- اسم أمر بحرف كبير: سيعمل في Telegram (Telegram case-insensitive للأوامر)، لكنه مخالف للاتفاقية — يناسب `WARNING` في lint، لا `TitanError` في validator.
- `on_offset` async: الكود "يعمل" بدون خطأ، لكن الـ coroutine تُهمَل بصمت — هنا يقوى الحجج للـ `WARNING` الفوري (أقرب لـ Contract Validator).

---

## 5. ما لا يوجد في الكود حالياً

لا أثر لـ Design Linter في `src/titan/` بأي شكل. لا فحوصات اتفاقية، لا `LintFinding`، لا `lint()` method.

الموقع الوحيد الذي يُلمَّح لمشكلة مرتبطة:
- `docs/internal/design_notes.md` السطر 212: "options range from accepting this as a known tradeoff, to introducing structural markers (type annotations, linting rules, naming patterns)" — لكن هذا يتحدث عن تطبيق Titan نفسه، لا بوتات المطورين.
- `ROADMAP.md` قسم "قيد الدراسة": `on_offset` يبتلع `async def` بصمت — مرشّح واضح لقاعدة lint فورية.

---

## 6. أسئلة مفتوحة تحتاج قرارًا قبل ADR

**س1 — الشكل:**
`bot.lint()` API مثل `bot.health()` — أم شيء مختلف؟

**س2 — العمق:**
نقتصر على القواعد القابلة للكشف في runtime (3أ + 3ب) — أم نفتح باب AST/CLI في مرحلة لاحقة؟

**س3 — on_offset async:**
هل يُعالَج كـ `LintFinding` (يظهر عند `bot.lint()`) — أم كـ `TitanError` فوري وقت التعيين مثل Contract Validator؟

**س4 — نوع البيانات:**
`LintFinding` مستقل عن `HealthFinding` — أم نستخدم نفس `HealthFinding` ونوسّع مصدره؟

**س5 — الموقع المعماري:**
قدرة Core (`bot.lint()` مثل `bot.health()`) — أم أداة منفصلة في `titan.linter` (خارج Core مثل `titan.playground`)?
