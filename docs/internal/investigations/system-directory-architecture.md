# تحقيق — Titan System Directory Architecture

**الحالة:** مغلقة — التنفيذ اكتمل — راجع ADR-019
**تاريخ:** 2026-07-25
**الهدف:** تحديد مسؤولية وبنية طبقة Lifecycle Management قبل إنشائها — ما الذي ينتمي إليها وما الذي يجب أن يبقى خارجها.

---

## 1. السؤال

هل يوجد ضغط معماري حقيقي يُبرّر طبقة Lifecycle Management مستقلة في Titan؟ وما مسؤوليتها بالضبط؟

- هل تُعبّر عن مسؤولية موجودة وغير منظّمة في `bot.py`؟
- أم أنها مسؤولية جديدة تحتاج بناءً من الصفر؟
- أم أن الضغط لا يكفي لتبرير مجلد مستقل؟

قبل إنشاء أي مجلد، يجب أن يكون الجواب واضحاً.

---

## 2. التشريح الحالي — ماذا يوجد في `src/titan/`؟

### 2.1 الملفات المسطّحة (Flat Files)

هذه الملفات تُشكّل **محرّك تشغيل Titan** — لا تُقدّم ميزة للمطور مباشرةً، بل تُشغّل كل ميزة.

| الملف | الدور |
|---|---|
| `bot.py` | الكلاس الرئيسي `Titan` — نقطة التجميع والـ Public API |
| `ctx.py` | سياق التنفيذ — يمتد لكل الـ handlers |
| `router.py` | توجيه الأحداث — يُفرز الـ updates لـ handlers |
| `middleware.py` | سلسلة التنفيذ — يُمرّر الـ update عبر طبقات مُسجَّلة |
| `adapter.py` | ترجمة Telegram API — يُحوّل raw update إلى نماذج Titan |
| `update.py` | تحليل الـ update — يُحدّد النوع ويستخرج البيانات |
| `telegram.py` | عميل HTTP — يرسل الطلبات لـ Telegram API |
| `errors.py` | هرمية الأخطاء — `TitanError` و `TelegramError` |
| `validation.py` | التحقق من المدخلات — handlers و middlewares |
| `models/` | نماذج البيانات — `Message`, `Sender`, `Chat`, `BotCapabilities` |

### 2.2 الأنظمة الفرعية (Feature Subsystems)

هذه الحزم تُقدّم **ميزة محددة** — كل منها اسم مستقل بمسؤولية واحدة.

| الحزمة | الميزة |
|---|---|
| `atlas/` | الذاكرة المعمارية — ADR-014 |
| `health/` | فحص صحة البوت — ADR-005 |
| `lint/` | فحص الالتزام بالعقد — ADR-012 |
| `inspector.py` | لقطة حالة البوت — ADR-006 |
| `timeline/` | سجل التطور المعماري — ADR-010 |
| `profiler/` | قياس الأداء — ADR-013 |
| `migration/` | مساعد الترحيل — ADR-007 |
| `playground/` | بيئة الاختبار — ADR-011 |
| `links/` | بروتوكول روابط الرسائل — ADR-008 |
| `privacy/` | دورة حياة البيانات — ADR-015→018 |
| `extras/` | `ask` و `alias` — أدوات مساعدة للبوت |
| `recipes/` | أنماط الاستخدام المُعتمدة |

### 2.3 الملاحظة الجوهرية

**الملفات المسطّحة لا تنتمي لأي تصنيف حالياً.** كلها في جذر `src/titan/` بجوار بعضها بلا تمييز. هذا لم يكن مشكلة لأن عددها كان يسيراً — لكنه يعني أن مسؤولية **محرّك التشغيل** غير مُسمَّاة هيكلياً.

---

## 3. ثلاثة تعريفات مرشحة لـ `system/`

### المرشح أ — إعادة التجميع (Engine Regrouping)

**التعريف:** `system/` يستوعب الملفات المسطّحة التي تُشكّل محرّك التشغيل: `adapter.py`, `middleware.py`, `update.py`, `validation.py`, بجانب `models/`.

```
src/titan/
├── bot.py              ← يبقى (Public API Root)
├── ctx.py              ← يبقى (Public Contract)
├── errors.py           ← يبقى (Public Contract)
├── telegram.py         ← يبقى (استُخدم في hot paths)
├── router.py           ← يبقى (مُصدَّر في __init__)
└── system/
    ├── adapter.py      ← ينتقل
    ├── middleware.py   ← ينتقل
    ├── update.py       ← ينتقل
    └── validation.py   ← ينتقل
```

**ما يُحلّه:** يُنظّم implementation details خلف حدّ مرئي.
**ما يكسره:** `bot.py` يستورد من `titan.adapter`، `titan.update`، `titan.middleware` — كل هذه المسارات تتغيّر. إعادة التجميع بلا ضرورة = تعقيد مجاني.
**الحكم:** مرفوض — التجميع الشكلي لا يُضيف سلوكاً، ويكسر مسارات استيراد داخلية ثابتة بدون مكسب.

---

### المرشح ب — إدارة دورة حياة البوت (Lifecycle Management)

**التعريف:** `lifecycle/` مسؤوليته المُوحَّدة: **إطلاق البوت وإيقافه بأمان.** يستخرج منطق `run()` و `run_async()` من `bot.py` ويُوسّعه بإدارة صريحة للإشارات (SIGTERM, SIGINT)، وprotocol للإيقاف المتدرّج (graceful shutdown).

**ما الذي يعيش في `bot.py` حالياً وينتمي لـ `lifecycle/`:**

```python
# في bot.py حالياً — منطق lifecycle منثور داخل run_async():
async def run_async(self, ...):
    # startup: get_me(), سجّل أوامر الـ privacy، سجّل أوامر الـ links
    # polling loop: getUpdates() → _handle_update()
    # backoff: تصاعدي عند الفشل
    # shutdown: KeyboardInterrupt / finally
```

**ما يُضيفه `lifecycle/` الذي لا يوجد الآن:**
- Signal handler صريح لـ SIGTERM (Docker / process managers تُرسل SIGTERM، لا Ctrl+C)
- Graceful drain: انتظر اكتمال الـ updates الجارية قبل الإيقاف

**الحجّة المعمارية لهذا المرشح:**
- `bot.py` حالياً يخلط بين **إعلان البوت** (تسجيل handlers، middleware، routers) وبين **تشغيله** (polling، backoff، إيقاف). المسؤوليتان متشابكتان لكنهما مختلفتان.
- SIGTERM غياب حاله حالياً: عملية تُوقَف بـ SIGTERM تموت دون انتظار اكتمال الـ update الجاري. هذا ليس مشكلة في التطوير — لكنه مشكلة حقيقية في production environments.
- ROADMAP يُدرج "معالجة متوازية للتحديثات" كفكرة قيد الدراسة — أي تصميم لها يحتاج lifecycle management صريح لا يمكن أن يكون داخل `bot.py`.

**الحكم:** هذا المرشح يُعبّر عن ضغط حقيقي — لكنه يحتاج تقييم النطاق (المرحلة 4).

---

### المرشح ج — تنسيق الأنظمة الفرعية (Subsystem Coordination)

**التعريف:** `system/` يُدار من خلاله التنسيق بين الأنظمة الفرعية — event bus داخلي، أو registry مركزي، أو pipeline للبيانات يخدم `health/`, `lint/`, `atlas/`, `profiler/` معاً.

**ما الذي يعيش فيه:**
- `registry.py` — مسجّل الأنظمة الفرعية التي يتتبّعها البوت
- `events.py` — أحداث دورة الحياة الداخلية (bot started, update received, handler failed)
- `bus.py` — يُوزّع هذه الأحداث للأنظمة المشتركة

**لماذا هذا مُبكّر:**
لا توجد الآن حالة يحتاج فيها أحد الأنظمة الفرعية أن يعلم بحدث يقع في نظام آخر. `health/` يُقيّم عند الطلب. `lint/` يُفحص عند الطلب. `profiler/` يسجّل بشكل مستقل. لا ضغط تنسيق حقيقي.
**الحكم:** مرفوض — تصميم event bus لأنظمة لا تحتاجه يعني بناء تجريد بلا مستهلك حقيقي.

---

## 4. تقييم المرشح ب — هل الضغط كافٍ الآن؟

### 4.1 ما يوجد بالفعل

```python
# bot.py → run_async()
async def run_async(self, on_offset=None):
    ...
    try:
        await get_me()          # startup check
        while True:
            updates = await getUpdates(...)
            for u in updates:
                await _handle_update(u)
            backoff = 1.0       # reset
    except KeyboardInterrupt:
        pass                    # الإيقاف عبر Ctrl+C فقط
    finally:
        await session.close()
```

### 4.2 الغياب الحالي

| الحاجة | الوضع الحالي | الخطر |
|---|---|---|
| SIGTERM handling | غائب — العملية تُقتل فوراً | updates جارية تُفقد بصمت في production |
| Graceful drain | غائب | update يُعالَج نصفه ثم يُقطع |
| `on_startup` hook | غائب | لا طريقة رسمية لتشغيل كود عند بدء البوت |
| `on_shutdown` hook | غائب | لا طريقة رسمية لإغلاق موارد (DB connections، external sessions) |
| Startup validation | جزئي (`get_me()` يُشغَّل لكن نتيجته تُهمَل أحياناً) | البوت يبدأ برمز توكن خاطئ بدون رسالة واضحة |

### 4.3 هل هذا ضغط حقيقي؟

**نعم — بمقياس محدود.**

- SIGTERM: أي bot يعمل في Docker أو systemd أو أي container orchestrator يتلقى SIGTERM عند الإيقاف. غيابه يعني فقدان updates بصمت — وهذا سلوك صامت بامتياز (نوع المشاكل التي وثّقتها `silent-failures.md`).
- Hooks (`on_startup` / `on_shutdown`): طلب حقيقي في أي bot production. ربط database أو تهيئة cache عند البدء، وغلق الاتصالات عند الإيقاف. حالياً المطور يحتاج hack لتحقيق هذا.

**لكن — الحجم محدود جداً.**

- SIGTERM يحتاج ~20 سطراً في `bot.py` أو ملف مساعد.
- Hooks تحتاج قائمتَين (on_startup_hooks / on_shutdown_hooks) ونداء في المكان الصحيح.
- هذا لا يبرّر مجلداً كاملاً بمسؤولية مستقلة — إلا إذا كان التصميم المستقبلي يتوسّع فوقه.

---

## 5. الحدود الفاصلة — ما الذي لا ينتمي لـ `system/` مطلقاً؟

بغض النظر عن التعريف المختار، هذه الحدود ثابتة:

| ما لا ينتمي | السبب |
|---|---|
| `bot.py` كـ module | هو Public API Root — يبقى في جذر `titan/` |
| `ctx.py` | Public Contract — جزء من الضمان الرسمي في CONTRACT.md |
| `errors.py` | Public Contract — `TitanError` و `TelegramError` مُصدَّران رسمياً |
| `router.py` | يُستخدم بشكل مستقل (`from titan import Router`) — لا يُخفى خلف `lifecycle/` |
| الأنظمة الفرعية الموجودة | `health/`, `lint/`, `atlas/` إلخ — لكل منها مسؤوليته المسمّاة، لا تحتاج وسيطاً |
| Recipes | خارج نطاق الـ Core بالتعريف |
| أي منطق تجاري | `lifecycle/` لا يُعالج messages أو يُوجّه events — هذا دور `router.py` و `bot.py` |

---

## 6. القرار — Adapt (نطاق محدود)

### التعريف المعتمد

> `lifecycle/` = **طبقة دورة حياة البوت** — المسؤولية الوحيدة هي إدارة حلقة polling وتشغيل البوت وإيقافه بأمان.

### ما يُبنى داخله

```
src/titan/lifecycle/
├── __init__.py       ← داخلي — لا يُصدَّر شيء للمطور
├── runner.py         ← PollingRunner — حلقة polling والـ backoff وإغلاق الـ workers
└── signals.py        ← install / uninstall — معالجة SIGTERM / SIGINT
```

**`runner.py`** يستخرج منطق التشغيل من `bot.py`:
- polling loop مع exponential backoff
- توزيع التحديثات على chat workers أو direct tasks
- graceful drain عند الإيقاف

**`signals.py`** يُضيف ما هو غائب:
- تسجيل SIGTERM / SIGINT handler
- الإلغاء يُشغّل كتلة `finally` في `run_async()` — نفس مسار الإغلاق النظيف

### ما لا يُبنى — حدود صارمة

- لا event bus
- لا subsystem registry
- لا configuration management
- لا hooks (`on_startup` / `on_shutdown`) — خارج نطاق هذا القرار
- لا إعادة تجميع للملفات المسطّحة الموجودة

### العلاقة مع `bot.py`

`bot.py` يبقى كما هو بوصفه **نقطة الإعلان** (declaration point):
- تسجيل handlers
- تسجيل middleware
- تسجيل routers
- تسجيل error handler

`lifecycle/runner.py` يأخذ هذا البوت المُعلَن ويُشغّل حلقة polling.

```python
# المطور لا يرى الفرق — نفس الـ API
bot.run()           → يستدعي lifecycle.runner داخلياً
bot.run_async()     → يستدعي lifecycle.runner داخلياً
```

### ما يعنيه "لا يرى المطور `lifecycle/`"

`titan.lifecycle` مسار داخلي — لا يُذكر في CONTRACT.md كـ public import، ولا يُصدَّر في `__init__.py`. أي مطور يستورد منه مباشرةً يتعامل مع implementation detail.

---

## 7. الاختبارات

`lifecycle/` يُضيف ملف اختبار: `tests/test_lifecycle.py`

نطاق الاختبارات:
- توزيع التحديثات على chat workers أو direct tasks
- `offset_updated` يُستدعى لكل تحديث مع update_id الصحيح
- exponential backoff عند الأخطاء المؤقتة، والإعادة إلى الصفر بعد النجاح
- `shutdown()` يُرسل sentinel ويُفرّغ القاموسَين
- `signals.install` / `uninstall` آمنتان في كل بيئة

لا اختبارات لمسار استيراد `titan.lifecycle` كـ public — لأنه ليس public.

---

## 8. ترتيب التنفيذ

```
التحقيق (هذا الملف)
    ↓
ADR-019: Lifecycle Management Layer
    ↓
تنفيذ: lifecycle/signals.py + lifecycle/runner.py
    ↓
تحديث: bot.py — run_async يفوّض إلى PollingRunner
    ↓
اختبارات: tests/test_lifecycle.py
```

---

## 9. ما يظل خارج النطاق الآن

| الموضوع | الملاحظة |
|---|---|
| `logging` بدلاً من `print()` | ROADMAP — قيد الدراسة — تغيير داخلي في `telegram.py` / `bot.py` |
| Traceback كامل في أخطاء handlers | ROADMAP — قيد الدراسة — يُعالَج في `bot._handle_error()` مباشرةً |
| Network timeout على aiohttp | ROADMAP — قيد الدراسة — تغيير داخلي في `telegram.py` |
| معالجة متوازية للتحديثات | ROADMAP — قيد الدراسة — يبني فوق `lifecycle/` لكن لا يُحدَّد الآن |
| Read-only Runtime Registries | ROADMAP — قيد الدراسة — مسؤولية `bot.py` مباشرةً |
| Lifecycle hooks (`on_startup` / `on_shutdown`) | خارج نطاق هذا القرار — يحتاج ADR مستقلاً إذا ظهر ضغط حقيقي |

---

## الخلاصة

| السؤال | الجواب |
|---|---|
| هل طبقة Lifecycle Management يجب أن توجد؟ | نعم — لأن lifecycle management ضغط حقيقي غائب في `bot.py` |
| ما مسؤوليتها الوحيدة؟ | إدارة حلقة polling وإيقاف البوت بأمان |
| هل تظهر للمطور؟ | لا — تُستخدم داخلياً من `bot.run()` / `bot.run_async()` |
| هل تُعيد تنظيم ما هو موجود؟ | لا — تُضيف فقط، لا تُحرّك |
| هل تمتد لتنسيق الأنظمة الفرعية؟ | لا — مرفوض صراحةً في هذا التحقيق |
