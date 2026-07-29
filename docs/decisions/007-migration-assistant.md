# 007 — Migration Assistant

**Status:** Accepted

---

## Proposal

بناء طبقتين لمساعدة المطورين القادمين من frameworks أخرى على الانتقال إلى Titan:
1. أدلة انتقال فلسفية في `docs/migration/`
2. Migration Knowledge API في `src/titan/migration/` — قابلة للقراءة برمجياً من الأدوات المستقبلية

---

## Investigation

→ [docs/internal/investigations/migration-assistant.md](../internal/investigations/migration-assistant.md)

**المشكلة الحقيقية:** مطور PTB أو aiogram يواجه خمسة نقاط احتكاك غير واضحة عند الانتقال لـ Titan — ليست syntax فقط، بل نموذج تفكير مختلف. بدون دليل يشرح الفلسفة لا مجرد المقابلات، المطور يكتب Titan بعقلية إطاره القديم ثم يتعجب من السلوك.

**الأهمية الاستراتيجية:** نمو Titan يعتمد على استقطاب مطوري Telegram الحاليين. Migration Assistant ليست ميزة جانبية — هي بوابة الدخول.

---

## Decision

### لماذا طبقتان وليس واحدة

**التوثيق وحده لا يكفي** لأن المعرفة تبقى مدفونة في Markdown — لا تستطيع Architect AI ولا أدوات مستقبلية الاستفادة منها برمجياً.

**الكود وحده لا يكفي** لأن المطور البشري يحتاج شرحاً فلسفياً، لا استدعاء API.

**الطبقتان متكاملتان:**

| الطبقة | المستخدم | الغرض |
|---|---|---|
| `docs/migration/` | المطور البشري | يفهم الفلسفة والفروقات قبل البدء |
| `titan.migration` | الأدوات (Architect AI, Playground...) | تستعلم عن المعرفة برمجياً |

---

### الطبقة 1 — Documentation Layer

```
docs/migration/
    README.md          — نقطة الدخول: اختر إطارك
    from-ptb.md        — انتقال من python-telegram-bot
    from-aiogram.md    — انتقال من aiogram
    from-telebot.md    — انتقال من pyTelegramBotAPI (telebot)
```

**هيكل كل دليل (ليس جدول syntax فقط):**

1. **الفرق الفلسفي الرئيسي** — لماذا Titan يفعل الأشياء بطريقة مختلفة؟
2. **خريطة المقابلات** — هذا المفهوم في إطارك = هذا في Titan
3. **الأشياء التي ستنكسر** — friction points غير الواضحة
4. **الأشياء التي لا يوجد لها مقابل مباشر** — تحتاج إعادة تصميم، لا مجرد ترجمة

---

### الطبقة 2 — Migration Knowledge API

```
src/titan/migration/
    __init__.py        — public API: frameworks(), concepts(), compare()
    models.py          — ConceptMapping dataclass (frozen)
    _data.py           — البيانات الخام (private — لا يُستورد مباشرةً)
```

**API العامة:**

```python
from titan.migration import frameworks, concepts, compare

frameworks()
# ["ptb", "aiogram", "telebot"]

concepts("aiogram")
# ["middleware", "command", "handler", "context", "callback", "routing", "error_handler", "startup"]

compare("aiogram", "middleware")
# ConceptMapping(
#     framework="aiogram",
#     concept="middleware",
#     source_name="outer/inner middleware",
#     titan_equivalent="bot.middleware()",
#     difference="Titan uses one update-level chain. No per-handler granularity.",
#     note="If you need different behavior per handler, redesign — not translate.",
# )
```

**نوع الإرجاع — `ConceptMapping` (frozen dataclass):**

```python
@dataclass(frozen=True)
class ConceptMapping:
    framework: str           # "aiogram"
    concept: str             # "middleware"
    source_name: str         # الاسم في الإطار الأصلي
    titan_equivalent: str    # المقابل في Titan
    difference: str          # الفرق الجوهري
    note: str | None         # ملاحظة للحالات التي تحتاج إعادة تصميم
```

---

### Root Export Policy

`ConceptMapping` **لا يُصدَّر من الجذر.**

المبرر: المطور لا يحتاجه للـ type annotation عند استخدام الـ public API — `compare()` تُرجعه مباشرةً، ومن يحتاج النوع يستورده من `titan.migration`.

يستوفي Root Export Policy: `from titan.migration import ConceptMapping` — لا `from titan import ConceptMapping`.

---

### الأطر المُغطّاة في v1

**PTB + aiogram + telebot** — الأكثر شيوعاً في مجتمع Telegram.

**المفاهيم المُغطّاة لكل إطار:**

| المفهوم | PTB | aiogram | telebot |
|---|---|---|---|
| `command` | ✅ | ✅ | ✅ |
| `handler` | ✅ | ✅ | ✅ |
| `middleware` | ✅ | ✅ | — |
| `context` | ✅ | ✅ | ✅ |
| `callback` | ✅ | ✅ | ✅ |
| `routing` | ✅ | ✅ | ✅ |
| `error_handler` | ✅ | ✅ | ✅ |
| `startup` | ✅ | ✅ | ✅ |

---

### ما يُؤجَّل

**Version Migration (المسار ب):** يُسجَّل كمؤجَّل بوعي في الـ Roadmap. Titan لا يملك v2 بعد — لا مشكلة حقيقية تُحل الآن.

**Code Scanner / CLI Migration (المستوى 3):** يُسجَّل كمؤجَّل. محاولة تحويل مشاريع كاملة تلقائياً تعني بناء "مترجم لغات برمجية" قبل أن يثبت Titan نفسه.

---

## Rule

**Migration Assistant يشرح الفلسفة، لا يُترجم الكود.**

الهدف: المطور يفهم **لماذا** Titan يعمل بهذه الطريقة، لا فقط **ماذا** يكتب. مطور يفهم الفلسفة يكتب Titan صحيحاً — مطور يرى جدول syntax فقط يترجم بعقلية إطاره القديم.

---

## Alternatives Considered

**توثيق فقط، بلا `titan.migration` module:**  
رُفض — المعرفة تبقى مدفونة في Markdown. Architect AI والأدوات المستقبلية لن تستطيع الاستفادة منها.

**CLI يحلل المشاريع:**  
مؤجَّل — يحل مشكلة التحويل التلقائي، وهذه ليست المشكلة الأساسية في v1. المشكلة هي الفهم، لا الأتمتة.

**تغطية PTB فقط في v1:**  
رُفض — aiogram له مجتمع كبير وفلسفة مختلفة جداً (filters, FSM). حذفه يُضعف قيمة الميزة.

---

## `titan.migration` كقاعدة معرفة عامة

`titan.migration` لم تُبنَ لغرض واحد — "مساعدة الانتقال". بُنيت كـ **knowledge base قابلة للاستعلام** يمكن أن تخدم:

| المستهلك المستقبلي | كيف يستخدم `titan.migration` |
|---|---|
| **Architect AI** | يسأل `compare()` لفهم الفروقات ويُضمّنها في شرحه |
| **Runtime hints** | عند اكتشاف نمط قديم، يقترح المقابل في Titan |
| **Documentation generators** | يستعلم `concepts()` لبناء صفحات مقارنة تلقائياً |
| **أدوات ذكية أخرى** | أي أداة تحتاج معرفة مُهيكلة عن الفروقات بين الأطر |

**المبدأ:** المعرفة مبنية مرة واحدة في `_data.py` وتُقرأ من أي أداة. لا نسخ، لا Markdown مدفون.

**القيد المعتمد:** الـ API تبقى صغيرة ومركّزة — `frameworks()`, `concepts()`, `compare()`. أي وظيفة جديدة تنتظر حاجة حقيقية من مستهلك حقيقي.

---

## Consequences

**المكتسب:**
- بوابة دخول واضحة لمطوري Telegram الحاليين.
- معرفة الانتقال مُهيكلة وقابلة للاستعلام — تخدم Architect AI والأدوات القادمة.
- الفلسفة موثَّقة قبل أن تُسأل: "لماذا Titan يفعل X وليس Y؟"

**المقبول:**
- `titan.migration` يُضيف سطحاً جديداً — محدوداً ومعزولاً.
- الـ docs تحتاج صيانة عند تغيير PTB/aiogram API (نادر للمفاهيم الأساسية).
