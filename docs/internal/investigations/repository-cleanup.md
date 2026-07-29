# Investigation — Repository Cleanup & File Rationalization

**الحالة:** مكتملة — تقرير معماري. لا تعديلات مباشرة في هذه المرحلة.
**التاريخ:** 2026-07-25
**الغرض:** مراجعة بنية المستودع بالكامل قبل أي إعادة تنظيم لمجلد `system/`، وتحديد حالة كل ملف ومجلد.

---

## 1. النطاق والمنهجية

المراجعة شملت:

- كل ملفات الجذر.
- `src/titan/` بالكامل مع SOURCES.txt والـ egg-info.
- `tests/` كاملاً.
- `scripts/`.
- `docs/` بجميع أقسامها.
- الملفات الخفية والمجلدات المتجاهَلة ذات الصلة (`.titan/`، `.gitignore`، `uv.lock`).
- الـ imports الفعلية وتوابع كل وحدة.
- الإشارات المتقاطعة بين الملفات.

**المعيار:** الاستخدام الفعلي والـ imports والعقد (CONTRACT.md) والـ ADRs.

---

## 2. ملفات الجذر

| الملف | التقييم | الملاحظة |
|---|---|---|
| `README.md` | احتفاظ | الوجه العام للمشروع بالعربية |
| `README.en.md` | احتفاظ | النسخة الإنجليزية — مُشار إليها من README.md |
| `LICENSE` | احتفاظ | ضروري |
| `pyproject.toml` | احتفاظ | مصدر الحقيقة للـ metadata والتوزيعة |
| `pytest.ini` | احتفاظ | تهيئة pytest، خفيف ونظيف |
| `CHANGELOG.md` | احتفاظ | سجل التغييرات الرسمي |
| `CONTRACT.md` | احتفاظ | العقد العام، مرجع أولي |
| `CONTRIBUTING.md` | احتفاظ | إرشادات المساهمة |
| `CONTRIBUTORS.md` | احتفاظ | The Titan Ledger |
| `ROADMAP.md` | احتفاظ | خريطة المشروع |
| `replit.md` | احتفاظ | بيئة التطوير وتفضيلات المشروع |
| `.gitignore` | احتفاظ مع تعديل | **مشكلة:** `uv.lock` مدرج في .gitignore لكنه متابَع من git فعلاً. التعارض يعني أن git يتتبعه رغم وجود القاعدة. يحتاج قراراً: إما حذف السطر من .gitignore (للاعتراف بأنه متابَع) أو `git rm --cached uv.lock` (لإزالته من التتبع) |
| `uv.lock` | قرار مؤجَّل | متابَع من git رغم وجوده في .gitignore. لا خطر حالي لكن التناقض يجب حسمه |
| `.replit` | احتفاظ | تهيئة بيئة Replit |

---

## 3. `src/titan/` — الكود المصدري

### 3.1 الحالة العامة

**نظيف بالكامل.** كل ملف مستخدَم وله اختبار مقابل.

| الوحدة / الملف | الحالة | الملاحظة |
|---|---|---|
| `__init__.py` | احتفاظ | Root exports المحددة والضرورية فقط |
| `bot.py` | احتفاظ | Core |
| `ctx.py` | احتفاظ | Core |
| `adapter.py` | احتفاظ | Core |
| `telegram.py` | احتفاظ | Core |
| `router.py` | احتفاظ | Core |
| `update.py` | احتفاظ | Core |
| `errors.py` | احتفاظ | Core |
| `keyboard.py` | احتفاظ | Core |
| `middleware.py` | احتفاظ | Core |
| `inspector.py` | احتفاظ | Core |
| `validation.py` | احتفاظ | Core |
| `py.typed` | احتفاظ | PEP 561 — ضروري للـ type checkers |
| `atlas/` | احتفاظ | Titan Atlas (ADR-014) |
| `extras/` | احتفاظ | `alias.py`، `ask.py` — مستخدمان واختبارهما موجودان |
| `health/` | احتفاظ | Project Health (ADR-005) |
| `links/` | احتفاظ | Message Links (ADR-008/018) |
| `lint/` | احتفاظ | Design Linter (ADR-012) |
| `migration/` | احتفاظ | Migration Assistant (ADR-007) |
| `models/` | احتفاظ | نماذج البيانات الأساسية |
| `playground/` | احتفاظ | Playground (ADR-011) |
| `privacy/` | احتفاظ | Privacy Protocol (ADR-015→018) |
| `profiler/` | احتفاظ | Performance Profiler (ADR-013) |
| `recipes/` | احتفاظ | Welcome recipe — وثيقة استخدام حي للـ Core |
| `timeline/` | احتفاظ | Titan Timeline (ADR-010) |

### 3.2 `src/titan_lib.egg-info/`

Build artifact مُولَّد تلقائياً. مدرج في `.gitignore` (`src/*.egg-info/`) وغير متابَع من git.
موجود محلياً كنتيجة طبيعية لـ `pip install -e .`.
**لا إجراء مطلوب.**

---

## 4. `tests/`

**نظيفة.** كل ملف اختبار يقابل وحدة أو مجالاً محدداً. لا ملفات يتيمة.
عدد الاختبارات: 896+ — كلها ناجحة.
**لا إجراء مطلوب.**

---

## 5. `scripts/`

ملف واحد: `generate_decisions_readme.py`.
مُشار إليه في ADR-010 ومُشغَّل يدوياً عند إضافة قرار جديد.
**احتفاظ.**

---

## 6. المجلدات الخفية ذات الصلة

### 6.1 `.titan/links.db`

قاعدة بيانات SQLite لنظام الروابط (Links). Runtime artifact، مدرجة في `.gitignore`، غير متابَعة.
**لا إجراء مطلوب.** وجودها طبيعي في بيئة التطوير.

### 6.2 `attached_assets/`

المجلد غير موجود (الملفان اللذان كانا فيه حُذفا سابقاً).
**لا إجراء مطلوب.**

### 6.3 `system/`

غير موجود بعد. هذا هو موضوع الدراسة القادمة.
**لا إجراء مطلوب في هذه المرحلة.**

---

## 7. `docs/` — التحليل التفصيلي

### 7.1 `docs/decisions/` (ADRs)

18 قراراً معمارياً + README مُولَّد تلقائياً.
**جميعها احتفاظ.** الـ README يُجدَّد عبر `scripts/generate_decisions_readme.py`.
الرابط في README للـ ADR-014 صحيح: `014-architect-ai.md`.

### 7.2 `docs/architecture/`

| الملف | الحالة |
|---|---|
| `design_principles.md` | احتفاظ — معايير المراجعة المعمارية الرسمية |

### 7.3 `docs/concepts/`

| الملف | الحالة |
|---|---|
| `ctx.md` | احتفاظ |
| `mental_model.md` | احتفاظ |
| `middleware.md` | احتفاظ |
| `models.md` | احتفاظ |

### 7.4 `docs/reference/`

| الملف | الحالة |
|---|---|
| `api.md` | احتفاظ |
| `events.md` | احتفاظ |
| `keyboard.md` | احتفاظ |

### 7.5 `docs/migration/`

| الملف | الحالة |
|---|---|
| `README.md` | احتفاظ |
| `from-aiogram.md` | احتفاظ |
| `from-ptb.md` | احتفاظ |
| `from-telebot.md` | احتفاظ |

### 7.6 `docs/patterns/`

| الملف | الحالة |
|---|---|
| `README.md` | احتفاظ |
| `guard-middleware.md` | احتفاظ — Pattern رسمي مقبول |

### 7.7 `docs/quickstart.md` و `docs/faq.md`

**احتفاظ.** وثائق للمستخدم، نظيفة ومحدّثة.

### 7.8 `docs/context/`

| الملف | التقييم | التفاصيل |
|---|---|---|
| `architecture_reviews.md` | احتفاظ | فهرس المراجعات المعمارية الدائمة والقرارات الموحَّدة. مرجع نشط |
| `privacy_protocol.md` | **مرشح للأرشفة** | سياق جلسة محادثة حُفظ لدعم بناء ADR-015→018. تلك القرارات مكتملة ومدمجة في ADRs. لا يُشير إليه أي ملف آخر. محتواه متاح بشكل أكثر وضوحاً في ADR-015→018. **القرار مؤجَّل** — يحتاج تأكيداً قبل الحذف |

### 7.9 `docs/internal/`

#### الملفات المباشرة

| الملف | التقييم | التفاصيل |
|---|---|---|
| `design_notes.md` | احتفاظ | ورشة عمل داخلية، مُشار إليه من `docs/patterns/README.md`. يحتوي مبادئ داخلية ونقاشات لم تُنقَل بعد إلى وثائق رسمية |
| `expected-failure-cases.md` | احتفاظ | يُثبّت حالات الفشل المتوقعة لبروتوكول الخصوصية. مُشار إليه من `tests/test_privacy.py` |
| `feature-workflow.md` | احتفاظ | يُعرِّف عملية التحقيق المعتمدة في Titan. لا يُشير إليه ملف آخر صريحاً لكنه المرجع الضمني لكل تحقيق |

#### `docs/internal/investigations/`

**التصنيف الكامل:**

##### أ — مكتملة بـ ADR مُنفَّذ — احتفاظ كمرجع تاريخي

| الملف | ADR | الملاحظة |
|---|---|---|
| `api-evolution-unknown-types.md` | — | Adopt+Adapt+Reject |
| `application-state-context-enrichment.md` | — | Reject، معتمد |
| `conversation-state-multi-step-flows.md` | — | Reject |
| `error-handling-propagation.md` | — | Adapt، منفَّذ |
| `interactive-inspector.md` | ADR-006 | مكتمل |
| `library-statistics.md` | — | Adapt، مكتمل 2026-07-25 |
| `middleware-granularity.md` | — | Reject |
| `migration-assistant.md` | ADR-007 | مكتمل |
| `performance-profiler.md` | ADR-013 | مكتمل |
| `playground.md` | ADR-011 | مكتمل |
| `project-health.md` | ADR-005 | مكتمل |
| `rate-limiting-flood-control.md` | — | Adapt، منفَّذ |
| `silent-failures.md` | — | مُنفَّذ بالكامل |
| `update-routing-filtering.md` | — | Reject |
| `webhook-vs-polling.md` | — | Reject، معتمد |

##### ب — مكتملة لكن تحتاج إجراء واحداً

| الملف | التقييم | الإجراء المطلوب |
|---|---|---|
| `architect-ai.md` | احتفاظ مع إعادة تسمية | الملف يُوثّق قرار أصبح ADR-014 "Titan Atlas". الاسم `architect-ai` يحتوي على المسمى القديم. **مرشح للتسمية:** `titan-atlas.md` — يُوحَّد مع الاسم الرسمي الحالي |
| `architectural-timeline.md` | احتفاظ | 0 مراجع من ملفات أخرى. تحقيق مغلق بالكامل → ADR-010. لا مشكلة في إبقائه |
| `design-linter.md` | **تحديث Header** | Header يقول "مفتوحة — في انتظار قرار معماري" لكن ADR-012 موجود ومنفَّذ. Header قديم ومضلِّل — يحتاج تحديثاً ليعكس الحالة الصحيحة |

##### ج — نشطة أو مفتوحة — لا مسّ

| الملف | الحالة | الملاحظة |
|---|---|---|
| `message-links-protocol.md` | نشط، نسخة رابعة | تحقيق مستمر |
| `runtime-contract-validator.md` | مفتوح، تحت المراجعة | لا ADR بعد |
| `userbot-support.md` | pending ADR، اتجاه محدد | 7 مراجع — أكثر الملفات إشارةً إليه |
| `user-privacy-erasure.md` | تحقيق أولي | 4 مراجع، لا ADR |
| `telegram-surface-prep.md` | عمل تحضيري نشط | تكمل `userbot-support.md` |

---

## 8. ملخص الإجراءات

### 8.1 مؤجَّلة — تحتاج قراراً مالكاً

| الإجراء | الملف | السبب |
|---|---|---|
| قرار `.gitignore` | `uv.lock` | متابَع من git رغم وجود القاعدة — حسم: هل يُتابَع أم يُزال؟ |
| أرشفة أو حذف | `docs/context/privacy_protocol.md` | سياق جلسة قديم، ADRs تغنيه — لكنه سجل تاريخي. يحتاج قراراً واعياً |

### 8.2 لا إجراء — احتفاظ كما هو

- كل `src/titan/` بالكامل.
- كل `tests/` بالكامل.
- كل `docs/decisions/` (ADRs).
- `docs/architecture/`، `docs/concepts/`، `docs/reference/`، `docs/migration/`، `docs/patterns/`.
- `docs/context/architecture_reviews.md`.
- `docs/internal/design_notes.md`، `feature-workflow.md`، `expected-failure-cases.md`.
- التحقيقات المكتملة (الفئة أ) — مرجع تاريخي معماري.
- التحقيقات النشطة (الفئة ج) — لا مسّ.
- `scripts/generate_decisions_readme.py`.
- `.titan/links.db` — runtime، متجاهَل بـ gitignore.
- `src/titan_lib.egg-info/` — build artifact، متجاهَل بـ gitignore.

---

## 9. حالة `system/`

المجلد غير موجود. الدراسة القادمة هي تصميم بنيته.

القاعدة التي يرسيها هذا التحقيق: أي تصميم لـ `system/` يجب أن ينطلق من المستودع النظيف الموصوف أعلاه — لا فوق ملفات قديمة أو غير مستخدمة.

---

## 10. ما يجب تأجيله ولا يُلمَس

- التحقيقات النشطة (الفئة ج): لها صاحب قرار واتجاه — لا تدخّل.
- `uv.lock`: تناقض لكنه غير مؤثر تشغيلياً — يُحسم بقرار واضح وليس بحذف عشوائي.
- `docs/context/privacy_protocol.md`: سجل تاريخي — حذفه يحتاج تأكيداً صريحاً.
- أي إعادة تنظيم لمجلد `docs/internal/investigations/` نفسه: الملفات المكتملة ذات قيمة كأرشيف معماري، وترتيبها الحالي قابل للقراءة.
