# 005 — Project Health

**Status:** Accepted

---

## Proposal

إضافة `bot.health()` كـ method في Core تُقيّم حالة البوت الهيكلية والتشغيلية
وتُعيد قائمة من الـ findings مصنّفة بثلاثة مستويات خطورة.

---

## Investigation

**المشكلة من منظور المطور:**
البوت يعمل بصمت سواء كان مكتملاً أم فارغاً.
لا توجد آلية تُنبّه المطور لثغرات هيكلية أو ضمانات تشغيلية مفقودة
قبل أن يكتشفها المستخدم.

**أربع حالات مُثبتة:**
1. بوت بلا أي handler — يعمل ولا يفعل شيئاً بصمت
2. بلا `_error_handler` — الاستثناءات تُبتلع بصمت
3. `supports_inline_queries=True` بدون inline handler
4. `can_join_groups=True` بدون أي handler للمجموعات

**ما يوجد في Core قابل للاستخدام:**
- `bot.commands`, `bot.handlers`, `bot.callback_handlers` — introspectable dicts
- `bot._error_handler` — None يعني لا حماية
- `bot.capabilities` — قدرات الحساب (متاحة فقط post-run بعد `getMe`)

التفاصيل الكاملة: `docs/internal/investigations/project-health.md`

---

## Decision

### الحدود مع Interactive Inspector

الفصل صارم ولا تداخل:

| | Inspector | Health |
|---|---|---|
| **السؤال** | ماذا يوجد؟ | هل ما يوجد سليم؟ |
| **الدور** | مرآة | طبيب |
| **الأحكام** | لا يُصدر | يُصدر |
| **الشمولية** | يعرض كل شيء | يعرض المشكلات فقط |

Inspector يصف. Health يُقيّم.

---

### API

```python
findings = bot.health()
```

- تُعيد `list[HealthFinding]`
- كل finding يحمل: `level`, `code`, `message`
- إذا لم توجد مشكلات — قائمة فارغة
- المستهلكون يقررون ماذا يفعلون بالنتيجة (طباعة، رمي، تسجيل)

**لا side effects.** الطباعة مسؤولية المستهلك، ليست مسؤولية `health()`.

---

### مستويات الخطورة

ثلاثة مستويات فقط:

| المستوى | المعنى | مثال |
|---|---|---|
| `ERROR` | البوت معطل فعلياً | لا handlers مسجلة |
| `WARNING` | غالباً خطأ، نادراً مقصود | لا error handler |
| `INFO` | ملاحظة، قد يكون مقصوداً | لا middleware |

**مرفوض:** `CRITICAL`, `DEBUG`, `HEALTH_SCORE`, percentages.
هذه تحوّل الأداة إلى نظام مراقبة — خارج نطاق Titan.

---

### الـ Checks — مرحلتان

**المرحلة الأولى (Structural — pre-run):**
تعمل قبل الاتصال بـ Telegram. deterministic. قابلة للاختبار في CI.

| الكود | المستوى | الشرط |
|---|---|---|
| `NO_HANDLERS` | ERROR | لا handlers، لا commands، لا callbacks |
| `NO_ERROR_HANDLER` | WARNING | `_error_handler is None` |

**المرحلة الثانية (Operational — post-run):**
تعمل فقط إذا كانت `bot.capabilities` متاحة (بعد `getMe`).
إذا كانت `None` — تُتجاهل هذه الفحوصات بصمت.

| الكود | المستوى | الشرط |
|---|---|---|
| `INLINE_CAPABILITY_UNUSED` | WARNING | `supports_inline_queries=True` + لا `inline_query` handler |
| `GROUP_CAPABILITY_UNUSED` | INFO | `can_join_groups=True` + لا handlers للمجموعات (`new_member`, `left_member`، `message`، أو أوامر). الأوامر تُعدّ كافية لأنها تعمل في المجموعات. |
| `PRIVACY_MODE_DISABLED_UNUSED` | INFO | `can_read_all_group_messages=True` + لا `message` handler |

**خارج نطاق v1 (مرفوض صراحةً):**
- Callback reachability (هل يوجد زر يستدعي هذا الـ handler؟)
- Static analysis / AST / file scanning
- Import inspection

---

### البنية الداخلية

```
src/titan/health/
    __init__.py   ← يُصدِّر HealthFinding و HealthLevel فقط
    models.py     ← HealthFinding dataclass، HealthLevel enum
    checks.py     ← دالة مستقلة لكل check
    runner.py     ← run_checks(bot) → list[HealthFinding]
```

`bot.py` يستورد فقط `run_checks` من `titan.health.runner`.
`runner.py` يستخدم `TYPE_CHECKING` لتفادي circular import مع `titan.bot`.

**لماذا `runner` وليس `engine`؟**
الوظيفة تشغيل فحوصات محددة — ليست "محركاً". `runner` يصف ما يحدث فعلاً.

---

### Core أم Extra؟

**Core.** لأن:
- المشكلة عامة وتمس كل مطور Telegram تقريباً
- التكلفة على الـ contract صغيرة (method واحدة + كائن بسيط)
- لا تضيف مفهوماً جديداً — تُقيّم ما هو موجود أصلاً
- الفائدة تمتد لأدوات أخرى (Migration Assistant, Architect AI)

---

## Rule

**أي فحص جديد يُضاف لـ `bot.health()` يجب أن يستوفي ثلاثة شروط:**
1. قابل للتحقق من الـ state الداخلي الموجود في `Titan` (لا file scanning، لا AST)
2. يمثّل مشكلة شائعة لا حالة افتراضية (الغياب غير المقصود، ليس الاختيار الواعي)
3. قابل للاختبار بشكل مستقل بدون Telegram session حقيقية

**Project Health تُقيّم حالة المشروع. لا تُصلحها.**

`bot.health()` تُعيد ما لاحظته. قرار التصرف يعود للمطور.
أي مسار يُضيف `fix=True` أو ما شابهه يُحوّل الطبيب إلى جراح آلي —
برنامج يُعدّل مشروعاً لم يفهمه. هذا مرفوض بدون نقاش.

---

## Consequences

**ما يُكتسب:**
- المطور يكتشف الثغرات الهيكلية قبل أن يكتشفها المستخدم
- `bot.health()` صالحة للاستخدام في CI، في scripts، وفي أدوات مستقبلية
- السلوك الصريح يتوافق مع فلسفة Titan (لا magic، لا side effects خفية)

**ما يُقبل كتنازل:**
- checks الـ capabilities تعتمد على توقيت `getMe` — لا ضمان أن `bot.health()` post-run ستُشغَّل دائماً
- الـ callback reachability (هل يوجد زر لكل handler؟) لا يمكن حلها بهذا النهج — مؤجلة للمستقبل
