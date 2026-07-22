# 014 — Titan Light

**Status:** Accepted

## Proposal

**Titan Light** — طبقة المعرفة المعمارية لـ Titan (`titan.light`).

تفهم قرارات المشروع، تعرض فلسفته، وتجعل المطورين والأدوات يفهمون لماذا أصبح Titan كما هو.
ليست chatbot، وليست wrapper لـ LLM — هي طبقة استعلام محددة النتائج تماماً.

المشكلة من منظور المطور:
> "المعرفة موجودة — في `titan.timeline`، في ملفات القرار، في القواعد.
> لكن لا توجد طريقة موحدة للاستعلام عنها."

---

## Investigation

### ما تعرفه Titan بالفعل

كل نظام معرفي في Titan يُجيب على سؤال واحد:

| الأداة | السؤال |
|---|---|
| `bot.inspect()` | ماذا يوجد في البوت الآن؟ |
| `bot.health()` | هل الهيكل مكتمل وسليم؟ |
| `bot.lint()` | هل التصميم يحترم الاتفاقيات؟ |
| `titan.timeline` | ما القرارات المعمارية ولماذا؟ |
| `titan.profiler` | كم يستغرق هذا الـ update؟ |

لا أحد منها يُجيب على: "لماذا feed_update موجود؟" أو "ما الفلسفة خلف هذا الـ API؟"

### الاكتشاف الرئيسي

`titan.timeline` يحتوي على `ArchiveEntry` لكل ADR مع:
- `rule` — القاعدة المعمارية الجوهرية
- `summary` — ملخص القرار
- `tags` — تصنيف موضوعي
- `path` — مسار ملف ADR الكامل

**كل المعرفة موجودة ومُهيكلة.** Architect لا يحتاج معرفة خارجية — يُعيد تنظيم ما يعرفه Titan بالفعل.

### لماذا rule-based وليس LLM في v1

الأسئلة الأكثر قيمة في v1 محددة ومتكررة:
- "ما القرارات المتعلقة بـ playground؟" → `search("playground")`
- "اشرح ADR-011" → `explain("011")`
- "ما القواعد المعمارية كلها؟" → `rules()`

هذه يُجيب عليها keyword matching بدقة كاملة.
LLM يُضيف تبعية خارجية + تكاليف + latency + مخاوف privacy — قبل أن يثبت الـ use case.

---

## Decision

**`titan.light` — domain منفصل، rule-based، يستهلك `titan.timeline`.**

### الموقع المعماري

```
titan.light
       |
       v
titan.timeline          ← المصدر الرئيسي للمعرفة
       |
  ArchiveEntry(number, title, status, rule, summary, tags, date, path)
```

`titan.light` لا يُلحق بـ `bot`. Bot محرك تنفيذ — Titan Light مستهلكة لأنظمة المعرفة.
استيراد `bot` instance غير مطلوب للإجابة على "لماذا هذا القرار موجود؟".

### النماذج

```python
@dataclass(frozen=True)
class SearchResult:
    number: str          # "011"
    title: str           # "Playground"
    matched_fields: list[str]  # الحقول التي احتوت على الكلمة: ["title", "tags"]
    relevance: int       # عدد الحقول المتطابقة — للترتيب
    entry: ArchiveEntry  # الإدخال الكامل للمزيد من التفاصيل

@dataclass(frozen=True)
class ArchitectExplanation:
    number: str
    title: str
    status: str
    date: str
    rule: str      # القاعدة الجوهرية
    summary: str   # ملخص القرار
    tags: list[str]
    path: str      # مسار ملف ADR الكامل

@dataclass(frozen=True)
class ArchitectRule:
    number: str    # "011"
    title: str     # "Playground"
    rule: str      # القاعدة نفسها
    date: str

@dataclass(frozen=True)
class DecisionSummary:
    number: str
    title: str
    status: str
    date: str
    summary: str
    tags: list[str]
    rule: str
```

### الـ API

```python
from titan.light import search, explain, rules, decisions

# 1. search — بحث keyword محدد النتائج (deterministic)
#    ليس ذكاءً اصطناعياً — keyword matching موزون على حقول محددة.
#    نفس الكلمة تُعطي دائماً نفس النتائج بنفس الترتيب.
results = search("feed_update")
# list[SearchResult] مرتبة بالأكثر صلة أولاً

results = search("feed_update", status="Accepted")
# فلترة بالحالة

search("")  # يُعيد كل القرارات

# 2. explain — تفسير قرار معماري واحد، لا مجرد retrieval
#    يُبرز الـ rule (المبدأ) + summary (لماذا اتُّخذ) + path (للتفاصيل الكاملة)
exp = explain("011")           # بالرقم المباشر
exp = explain("playground")    # بالكلمة → أفضل تطابق
# ArchitectExplanation | None

# 3. rules — القواعد المعمارية المستخرجة من قرارات ADR
#    ليست قواعد lint أو قواعد Python — هي المبادئ التي وجّهت قرارات التصميم
r = rules()                       # list[ArchitectRule] — إنجليزي (افتراضي)
r = rules(locale="ar")            # نفس القواعد بالعربية
r = rules(status="Accepted")      # فلترة بالحالة

# 4. decisions — ملخصات منظمة لكل القرارات
d = decisions()
d = decisions(locale="ar")
d = decisions(status="Accepted")
d = decisions(tags=["routing"])

# 5. explain — يدعم locale أيضاً
exp = explain("011", locale="ar")
```

### قواعد البحث في `search()`

يبحث في هذه الحقول بهذا الترتيب (لتحديد الأولوية):
1. `title` — وزن 3
2. `tags` — وزن 2
3. `rule` — وزن 2
4. `summary` — وزن 1

الـ relevance = مجموع الأوزان للحقول المتطابقة.
البحث case-insensitive، بدون stemming أو fuzzy في v1.

### `explain()` — منطق التطابق

```
الإدخال:
  - رقم فقط ("011"، "11"، "ADR-011") → تطابق مباشر بالرقم
  - نص → search() والإدخال الأعلى relevance
الإخراج:
  - ArchitectExplanation | None
```

### ما يُرفض بوعي في v1

| المرفوض | السبب |
|---|---|
| LLM API خارجي إجباري | تبعية خارجية + تكاليف — قبل إثبات الـ use case |
| `check_against_rules()` | يتداخل مع Design Linter ويفترض تحليل كود |
| توليد كود أو اقتراح implementations | خارج النطاق — Architect يُجيب لا يبني |
| تحليل AST أو كود المشروع | تعقيد ضخم يتداخل مع `inspect`/`lint` |
| Persistent memory (محادثات) | لا persistence layer في Titan |
| ربط تلقائي بـ `bot` instance | opt-in فقط — لا spy على `bot` بدون طلب صريح |
| Fuzzy search أو stemming | مكتبات إضافية — ليس v1 |

---

## Rule

**Titan Light تُلخّص ما يعرفه Titan بالفعل — محددة النتائج في v1، LLM اختياري لاحقاً.**

الـ output مُهيكل دائماً (dataclasses قابلة للاستهلاك برمجياً)
ومقروء بشرياً في نفس الوقت — human developer first،
لكن الأدوات وأنظمة AI الخارجية تستطيع استهلاكه مستقبلاً بدون تعديل.

حقول الترجمة (`rule["en"]` / `rule["ar"]`) موجودة لتسهيل استهلاك المعرفة —
لا لتحلّ محل ADR files كمصدر تاريخي. المصدر الأصلي للقرارات هو `docs/decisions/` دائماً.

---

## Alternatives Considered

### LLM integration من v1
يتيح Natural language Q&A. لكنه يُضيف تبعية إلزامية + تكاليف + latency +
مخاوف privacy. المعرفة الموجودة في `titan.timeline` قابلة للاستعلام بدون LLM
لمعظم الأسئلة الشائعة في v1.

### إلحاق Titan Light بـ `bot` كـ `bot.explain()` / `bot.ask()`
`health()` و`lint()` تقرآن state الـ `bot` — منطقي أنها methods عليه.
Architect تقرأ `titan.timeline` بشكل رئيسي — لا تحتاج `bot` instance.
الفصل يحافظ على وضوح المسؤوليات ويُبقي `bot` محرك تنفيذ فقط.

### `check_against_rules()` في v1
يتداخل مع Design Linter (`bot.lint()`) ويفترض قدرة تحليل كود —
وهي قدرة خارج نطاق Architect. مؤجل إلى حين وضوح الـ use case.

---

## Consequences

### مكتسبات
- مطوّر جديد يفهم Titan بسطرين: `search("topic")` أو `explain("011")`
- كل المعرفة قابلة للاستعلام برمجياً — لأدوات CI/CD أو AI خارجي
- صفر تبعيات خارجية في v1
- التصميم يترك مجالاً لـ LLM backend اختياري لاحقاً بدون كسر الـ API

### قيود مقبولة
- لا natural language Q&A في v1 — الأسئلة المركّبة تحتاج تجميع يدوي للنتائج
- البحث keyword فقط — لا fuzzy، لا synonyms
- لا ربط بـ `bot` instance — السياق الحالي للبوت لا يُضاف تلقائياً

### حدود `titan.light`

```python
from titan.light import search, explain, rules, decisions   # ✅
from titan import search                                     # ❌ غير موجود
```

غير مُصدَّر من جذر الحزمة — متسق مع سياسة `titan.playground` و`titan.profiler`.
