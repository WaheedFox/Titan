# 011 — Playground

**Status:** Accepted

---

## Proposal

إضافة `titan.playground` — مختبر معماري تفاعلي يسمح للمطور بتجربة سلوك
Titan الحقيقي (routing، middleware، Inspector، أخطاء) دون بناء بوت متصل
فعلياً بـ Telegram. يعتمد على قدرة جديدة في Core: `Titan.feed_update()` —
مدخل رسمي لتغذية Titan بأحداث من أي مصدر غير polling.

---

## Investigation

→ [docs/internal/investigations/playground.md](../internal/investigations/playground.md)

**المشكلة الحقيقية:** المطور يتعلم Titan اليوم بطريقتين مكلفتين فقط —
قراءة الكود المصدري مباشرة، أو تشغيل بوت حقيقي متصل بتوكن فعلي لمجرد فهم
كيف يمر update واحد عبر النظام. لا توجد طريقة لرؤية السلوك الحقيقي بمعزل
عن كلفة الإنتاج.

**لماذا الآن:** `titan.migration` (ADR-007) وثّق الفلسفة، `bot.inspect()`
(ADR-006) عرض الحالة الساكنة. الفجوة المتبقية: لا توجد طريقة لـ *صنع*
الحالة وتجربتها فعلياً. Playground يغلق هذه الفجوة تحديداً.

---

## Decision

### ١. نقطة الدخول: `Titan.feed_update()` — قدرة Core عامة، لا facade

كان الخيار الأول المطروح "facade رقيقة فوق `_handle_update` الخاصة" —
رُفض. أي غلاف فوق method خاص يُبقي الاعتماد الحقيقي على سلوك غير مضمون؛
تغيير توقيع `_handle_update` داخلياً يكسر المستهلك بصمت رغم الغلاف.

**القرار: `feed_update()` قدرة معلنة في `Titan` نفسها:**

```python
async def feed_update(self, update: dict[str, Any]) -> None:
    """
    Feed a Telegram-compatible update into Titan's processing pipeline.
    """
    await self._handle_update(update)
```

هذه ليست ميزة Playground فقط — هي حقيقة معمارية جديدة: **Titan يستطيع
استقبال update من أي مصدر، لا من Telegram polling حصراً.** هذا يخدم
Playground اليوم، ويخدم لاحقاً: اختبارات متقدمة تريد تغذية update دون
تكرار منطق dispatch، Userbot Support المستقبلي (مصدر أحداث مختلف تماماً
عن `getUpdates`)، وأي adapter خارجي آخر.

**التسمية:** المعامل `update`، لا `raw_update`. كلمة "raw" تختزل الدالة
إلى أداة اختبار داخلية؛ التسمية الصحيحة تعكس أنها مدخل أحداث رسمي بنفس
وزن `run_async()` — مسار مختلف لنفس الالتزام.

**العلاقة بـ `_handle_update`:** تبقى كما هي داخلياً، حرة التغيير طالما
`feed_update()` تحافظ على نفس العقد الظاهر (update متوافق مع شكل Telegram
→ معالجة كاملة عبر middleware ثم routing، بدون قيمة إرجاع). لا تكرار
لمنطق dispatch — Playground والاختبارات المتقدمة تمر عبر نفس المسار
الحقيقي الذي يستخدمه `run_async()`.

---

### ٢. الموقع: `src/titan/playground/` — public optional domain، بدون root export

نفس نمط `titan.migration` و`titan.timeline`: حزمة مستقلة داخل `src/titan/`،
قابلة للاستيراد الصريح، لكن **غير مذكورة** في `# 1. Public API` المجمّدة
في `CONTRACT.md`.

**تمييز مهم لا يُخلط:** هذا ليس "داخلياً" (`titan._playground`) — هي
public domain كاملة، فقط اختيارية غير مُصدَّرة من الجذر:

```python
# ✅ الاستخدام الرسمي
from titan.playground import Playground

# ❌ غير متاح، وليس المقصود إتاحته
from titan import Playground
```

**السبب:** Playground أداة يستدعيها المطور بقصد صريح — لا حاجة لإدخالها
في مسار `from titan import Titan` الذي يستخدمه كل مطور بوت عادي. إبقاؤها
خارج السطح المجمّد يمنحها حرية تغيّر أكبر في مراحلها الأولى دون أن تُعتبر
أي تعديل فيها كسراً بالمعنى الذي يُعرّفه `CONTRACT.md`.

---

### ٣. Telegram البديل: `RecordingTelegram` داخل `playground` فقط — بدون لمس `telegram.py`

**رُفض إضافة `Protocol` رسمي في `telegram.py`.** لا يوجد اليوم أي
مستهلك ثانٍ لـ `Telegram` غير `Context` و`TelegramAdapter` و`Titan` نفسها؛
إضافة تجريد الآن يعني بناء طبقة لحماية مستهلك وحيد مستقبلي — نفس المنطق
الذي رفض `by_tag()` في ADR-010: **لا نبني تجريداً لحاجة غير مؤكدة.**
Titan تتجنب عمداً أن تصبح "مصنع abstractions" — كل طبقة تُضاف بثمن حقيقي
على وضوح "hello world".

**القرار: `RecordingTelegram` يعيش حصراً داخل `titan.playground`، ويعتمد
على duck typing:**

```python
class RecordingTelegram:
    """
    بديل لـ Telegram يُستخدم داخل Playground فقط.
    يسجل كل استدعاء API بدل تنفيذه فعلياً عبر الشبكة.
    """
```

**حد صريح على نطاقه:** `RecordingTelegram` **لا يحاول محاكاة Telegram
API بالكامل.** يطبّق فقط الطرق التي يستدعيها `Context`/`TelegramAdapter`
فعلياً اليوم (`send_message`, `edit_message_text`, `delete_message`,
`answer_callback_query`, ...). أي استدعاء غير مُنفَّذ فيه يفشل بوضوح
(`AttributeError`) بدلاً من التصرف بصمت أو محاكاة سلوك غير حقيقي.

---

### ٤. Update Factory: `playground/factory.py`

الاسم `factory.py` لا `_updates.py` — الملف لا يبني "updates" فقط، بل
يبني سيناريوهات محاكاة كاملة (رسالة، أمر، callback، ولاحقاً انضمام أو
inline query). كل دالة تصنع update متوافق مع شكل Telegram الحقيقي من
مدخلات مبسطة:

```python
fake_message(text: str, chat_id: int = 1, user_id: int = 1) -> dict
fake_command(name: str, chat_id: int = 1, user_id: int = 1) -> dict
fake_callback(data: str, chat_id: int = 1, user_id: int = 1) -> dict
```

**حدود واضحة على النطاق:**
- تعيش داخل `titan.playground` كملكية كاملة — ليست utility عامة، لأنها
  جزء من "تجربة Playground" نفسها: منتج معرفي عن شكل update صحيح، لا أداة
  قياس عامة.
- اتجاه الاستيراد باتجاه واحد فقط: `tests/ → titan.playground`، أبداً
  العكس. Playground لا يعرف بوجود `tests/`.
- لا تتحول إلى مُصنِّع update عام قابل للتخصيص الكامل. إن ظهرت حاجة فعلية
  لذلك، هذا مشروع منفصل تماماً (نطاق مستقبلي، ليس امتداداً لـ Playground).

---

### ٥. طبيعة Playground: مختبر معماري، لا sandbox تجريبي فقط

**الفرق الجوهري: Inspector يرى الحالة. Playground يصنع الحالة.**

هذا يحدد سقف الطموح طويل الأمد لـ Playground (تدريجياً، ليس كل شيء في
v1): تشغيل بوت وهمي، مشاهدة routing لحظة بلحظة، مشاهدة middleware chain
أثناء التنفيذ، استهلاك `bot.inspect()` كواجهة عرض، تجربة callbacks
وأخطاء، مقارنة سلوك قبل/بعد migration، وتجربة انتهاكات Contract عمداً
لفهم رسائل الخطأ. v1 يبني فقط الأساس (`feed_update` + `RecordingTelegram`
+ `factory` + استهلاك Inspector) — الباقي يُبنى تباعاً حين يثبت مستهلك
فعلي لكل قدرة، بنفس انضباط ADR-010.

---

### ٦. الاختبار: إثبات عدم انحراف الـ pipeline، لا مطابقة `run_async()`

الاختبار المطلوب **لا يقارن** `feed_update()` بدورة حياة `run_async()`
الكاملة (تلك دورة شبكة polling، لا علاقة لها بالمسار المُختبر). الاختبار
يثبت أن نفس مسار المعالجة الحقيقي يعمل عبر المدخل الجديد تماماً كما يعمل
عبر `_handle_update` الداخلية:

- نفس handler يُستدعى لنفس نوع update.
- نفس middleware chain تُنفَّذ بنفس الترتيب.
- نفس callback handler المحدد بـ `callback_data` يُستدعى.

هذا يضمن أن `feed_update()` ليست نسخة موازية من منطق التوجيه، بل نفس
المسار الحقيقي بمدخل مختلف فقط.

---

## Rule

**Playground لا يضيف قدرات إلى Titan، بل يكشف قدرات Titan الموجودة
بطريقة قابلة للاستكشاف.**

أي وظيفة تُضاف إلى `titan.playground` مستقبلاً يجب أن تستهلك API عامة
موجودة فعلاً في Core (`feed_update`, `inspect`, `health`, ...) — لا تبني
منطقاً موازياً يُعيد تفسير سلوك Titan من الخارج.

**نقطة تغذية الأحداث تعيش في Core، لا في الأداة التي تستهلكها.**

`feed_update()` قدرة في `Titan` نفسها لأنها تصف حقيقة عن المحرك ("يقبل
أحداثاً من مصادر غير polling")، لا حاجة خاصة بـ Playground. أي أداة
مستقبلية (Userbot Support، اختبارات متقدمة) تستدعيها مباشرة دون المرور
عبر Playground.

**لا تجريد في Core لمستهلك واحد.**

`RecordingTelegram` duck-typed داخل `playground` فقط. لا `Protocol` في
`telegram.py` حتى يظهر مستهلك ثانٍ فعلي يحتاج العقد الرسمي.

**كل بديل محاكاة يفشل بوضوح خارج نطاقه المُعلن.**

`RecordingTelegram` ينفّذ فقط ما يُستدعى فعلياً من `Context`/
`TelegramAdapter` اليوم. لا محاولة لتغطية Telegram API بالكامل احتياطاً.

---

## Alternatives Considered

**Facade رقيقة فوق `_handle_update` بدل `feed_update()` عامة**

مرفوض. يُبقي الاعتماد الحقيقي على method خاص غير مضمون خلف غلاف بالاسم
فقط — لا يحل مشكلة الاعتماد الخفي، يخفيها فقط.

**`titan.playground` مُصدَّرة من الجذر (`from titan import Playground`)**

مرفوض. Root API يبقى نظيفاً لكل مطور بوت عادي؛ Playground أداة استكشاف
تُستدعى بقصد صريح، بنفس منطق `titan.migration` و`titan.timeline`.

**`Protocol` رسمي لـ `Telegram` في `telegram.py`**

مرفوض في v1. لا مستهلك ثانٍ فعلي غير `RecordingTelegram` نفسها. إضافته
الآن تجريد احتياطي بلا حاجة مُثبَتة — نفس مبدأ رفض `by_tag()` في ADR-010.

**محاكاة Telegram API الكاملة في `RecordingTelegram`**

مرفوض. يزيد سطح صيانة بلا فائدة — Playground يحتاج فقط ما يُستدعى فعلياً
من Core اليوم. التوسع يحدث تدريجياً مع كل قدرة جديدة تُضاف لـ Playground
نفسه.

**Update factory كـ utility عامة خارج `playground`**

مرفوض الآن. لا مستهلك فعلي غير Playground بعد. الانتقال لموقع utility
عام قرار مستقبلي منفصل إن ظهرت حاجة فعلية من `tests/` أو أدوات أخرى.

**مقارنة `feed_update()` بنتيجة `run_async()` الكاملة في الاختبار**

مرفوض. `run_async()` دورة polling كاملة (شبكة، offset، backoff) لا علاقة
لها بمسار المعالجة المُختبر. المقارنة الصحيحة محصورة في مسار
middleware → routing → handler.

---

## Consequences

**المكتسب:**
- قدرة Core جديدة وحقيقية (`feed_update`) تخدم Playground واختبارات
  متقدمة ومستقبل Userbot Support بنفس الآلية، دون تكرار منطق dispatch.
- Playground يبقى معزولاً بالكامل عن `telegram.py` — صفر تعديل على Core
  الحالي غير `feed_update()` نفسها.
- حدود واضحة منذ البداية تمنع Playground من التمدد إلى IDE أو محرر كود
  أو مُصنِّع بيانات عام.
- مسار نمو مستقبلي واضح (routing visibility، middleware trace، مقارنة
  migration، Contract violations) دون التزام ببنائه كله في v1.

**المقبول كتنازل:**
- `RecordingTelegram` هش أمام تغييرات توقيع مستقبلية في `Telegram`
  الحقيقية — لا فحص نوعي (type-level) بينهما، فقط اكتشاف عند الاستخدام.
  يحتاج اختباراً يتحقق من التغطية الفعلية عند إضافة أي استدعاء API جديد
  في Core.
- `feed_update()` تضيف method عاماً جديداً إلى `Titan` — سطح إضافي دائم،
  ولو صغيراً، لا رجوع عنه بسهولة بعد الاعتماد عليه من Playground
  والاختبارات.
- v1 لا يغطي أياً من: routing visibility الحية، middleware trace،
  Migration Assistant integration، أو استهلاك Architect AI المستقبلي —
  هذه تحتاج ADRs منفصلة لاحقاً عند ظهور مستهلك فعلي لكل واحدة.
