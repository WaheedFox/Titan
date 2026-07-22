# تحقيق — Architect AI

**الحالة:** مُغلقة — القرار المعماري اتُّخذ — راجع ADR-014 (Titan Light)
**تاريخ:** 2026-07-11
**الميزة:** Titan Light (#9) — من قائمة Planned

---

## 1. المشكلة التي تحلها Titan Light

**من منظور المطور:**

> "لماذا تصرف Titan هكذا؟ هل التغيير الذي أريده يتعارض مع قرار سابق؟ ما الفلسفة التي تحكم هذا الـ API؟"

الأنظمة المعرفية الموجودة تُجيب كلٌّ منها على سؤال واحد:

| الأداة | السؤال |
|---|---|
| `bot.inspect()` | ماذا يوجد في البوت الآن؟ |
| `bot.health()` | هل الهيكل مكتمل وسليم؟ |
| `bot.lint()` | هل التصميم يحترم الاتفاقيات؟ |
| `titan.timeline` | ما القرارات المعمارية المُتخذة ولماذا؟ |
| `titan.profiler` | كم يستغرق هذا الـ update؟ |

**ما لا يُجيب عليه أيٌّ منها:**

- "لماذا `feed_update()` موجود أصلاً؟ ما المشكلة التي حلّها؟"
- "هل إضافة `bot.enable_profiling()` تتعارض مع ADR موجود؟"
- "اشرح لي فلسفة Titan في جملتين."
- "ما القرارات التي اتُّخذت بخصوص الـ middleware؟"
- "هل هناك precedent معماري لما أريد بناءه؟"

الإجابة على هذه الأسئلة موجودة في النظام — في `titan.timeline`، في قواعد ADRs، في ملفات القرار.
المشكلة: **لا توجد طريقة موحدة للاستعلام عنها.**

المطور الآن يقرأ `docs/decisions/` يدوياً، يبحث في ملفات `.md`، يتذكر ما قرأه.
هذا يعمل لمطوّر واحد يعرف المشروع — لكنه لا يعمل لمساهم جديد، ولا لأداة، ولا لـ AI خارجي يحاول فهم Titan.

---

## 2. ما يملكه Titan اليوم كقاعدة بيانات معرفية

### 2أ. titan.timeline — الذاكرة المعمارية

```python
from titan.timeline import entries, rules, latest, by_status, entry

entries()   # list[ArchiveEntry] — كل القرارات مرتبة
rules()     # list[str]           — القواعد المعمارية الجوهرية فقط
latest(3)   # آخر 3 قرارات
by_status("Accepted")
entry("011")  # ADR-011 بالتفصيل
```

كل `ArchiveEntry` يحتوي: `number`, `title`, `status`, `rule`, `summary`, `tags`, `date`, `path`.

هذا هو العمود الفقري الأغنى — كل قرار موثَّق مع سببه ورفضه للبدائل.

### 2ب. bot.inspect() — الهيكل الحالي

```python
snapshot = bot.inspect()
# BotSnapshot:
#   commands: tuple[str, ...]
#   callbacks: tuple[str, ...]
#   events: Mapping[str, int]
#   middleware_count: int
#   has_error_handler: bool
#   included_router_count: int
```

يصف *ما هو موجود الآن* — لا تاريخ، لا سبب.

### 2ج. bot.health() — سلامة الهيكل

```python
findings = bot.health()
# list[HealthFinding]: level (ERROR/WARNING/INFO), code, message
```

يكشف *الفجوات* — ما يجب أن يوجد ولا يوجد.

### 2د. bot.lint() — الامتثال للفلسفة

```python
findings = bot.lint()
# list[LintFinding]: level, code, message, hint
```

يكشف *الانحرافات* عن الاتفاقيات — ليس ما هو خاطئ بل ما يخالف الفلسفة.

### 2هـ. الاكتشاف الرئيسي

**كل المعرفة موجودة — لكنها مجزأة.**

`titan.timeline` يحتوي على الكنز الأكبر: كل ADR يحتوي `summary` موجز + `rule` جوهرية.
ملفات `docs/decisions/` تحتوي على التفاصيل الكاملة + "Alternatives Considered" + "Consequences".

هذا يعني: Titan Light لا تحتاج معرفة خارجية — **المعرفة موجودة ومُهيكلة بالفعل**.

---

## 3. ما هي "Titan Light" بالضبط — وما ليست هي

### ما هي:

طبقة المعرفة المعمارية لـ Titan (`titan.light`) — تُجيب على أسئلة حول Titan نفسها: لماذا اتُّخذت قرارات، ما الفلسفة، هل تغيير مقترح يتعارض مع ADR.

### ما ليس هو:

- **ليس ChatGPT wrapper** — لا يستدعي OpenAI/Anthropic/Gemini في v1
- **ليس sandbox للكود** — لا يُنفّذ كوداً أو يقترح كتابة handlers
- **ليس docs generator** — لا يكتب README أو توثيقاً خارجياً
- **ليس RAG system** — لا embedding، لا vector database في v1
- **ليس monitoring** — لا يراقب production، لا يجمع telemetry

---

## 4. التوترات المعمارية المفتوحة

### التوتر 1 — هل يحتاج LLM في v1؟

**حجة نعم:** الأسئلة بلغة طبيعية — "لماذا feed_update موجود؟" — لا يمكن الإجابة عليها بدون فهم semantics.

**حجة لا:** كل ADR له `rule` و`summary` و`tags` — استعلام keyword + tags قادر على الإجابة على معظم الأسئلة الشائعة بدقة كافية في v1. اللغة الطبيعية الحرة يمكن تأجيلها.

**المخاطرة:** LLM API في v1 = تبعية خارجية + تكاليف + latency + privacy concerns.
هذا يتعارض مع فلسفة Titan: "لا تجرّ النظام إلى نطاق أكبر".

**السؤال المحوري:** هل v1 يكون rule-based/query أم يبدأ فوراً بـ LLM integration؟

### التوتر 2 — أين تعيش؟

الخيارات:
- **`titan.light`** — domain منفصل مثل `titan.playground` و`titan.profiler`
- **`bot.explain()` أو `bot.ask()`** — قدرة Core مثل `health()`/`lint()`

الفارق الجوهري:

`health()` و`lint()` تقرآن **حالة `bot` نفسها** — منطقي أنها method على `bot`.

Architect يقرأ بشكل رئيسي `titan.timeline` — لا يحتاج `bot` instance أصلاً للإجابة على "لماذا هذا القرار موجود؟".

لكن للإجابة على "هل هذا التغيير يتعارض مع بوتي الحالي؟" — يحتاج `bot.inspect()`.

**ما هو المسار الأكثر استخداماً في v1؟**
- استعلام عن تاريخ القرارات → لا يحتاج `bot` instance
- فحص تعارض مع بوت حالي → يحتاجه

هذا يفتح سؤالاً حول الـ API الصحيح.

### التوتر 3 — ما نوع "الذكاء" المقصود في v1؟

ثلاثة مستويات ممكنة:

**المستوى أ — Lookup محض:**
```python
architect.search("feed_update")
# يُعيد: كل ADRs تذكر "feed_update" مع سياقها
```
هذا قابل للتنفيذ 100% بدون AI. مفيد لكن محدود.

**المستوى ب — Rule matching:**
```python
architect.check("adding bot.enable_profiling()")
# يُعيد: يتعارض مع ADR-013 (rule: "لا Core state للـ profiler")
```
يحتاج parsing للقاعدة + keyword matching. لا يحتاج LLM.

**المستوى ج — Natural language Q&A:**
```python
architect.ask("لماذا feed_update موجود؟")
# يُعيد: إجابة مركّبة من عدة ADRs
```
هذا يحتاج قدرة LLM لربط الأجزاء ببعضها وتوليف إجابة مفهومة.

**السؤال:** هل يبدأ v1 من أ أو ب؟ أم يقفز مباشرة إلى ج بـ LLM؟

### التوتر 4 — "يترك مجالاً لـ AI مستقبلي" ماذا يعني عملياً؟

الـ vision يقول: "التصميم يجب أن يترك مجالاً لنظام AI ذاتي الاستضافة مستقبلاً."

هذا يعني:
- الـ API يجب أن لا يفترض provider محدد (OpenAI, etc.)
- المعرفة تُمرَّر للـ AI كـ context، ليس مضمّنة في model
- يمكن استبدال الـ "backend" لاحقاً بدون تغيير الـ API الخارجي

**السؤال:** ما التصميم الذي يُحقق هذا؟ هل هو:
- `ArchitectBackend` protocol يمكن توصيل أي LLM به؟
- أم شيء أبسط — دوال `query()` تُعيد structured data وتترك التوليف للمستدعي؟

---

## 5. نماذج الاستخدام الأكثر قيمة في v1

بغض النظر عن التوترات، هذه هي الاستخدامات التي تُبرر الميزة:

**أ. مساهم جديد يفهم Titan:**
```python
from titan.light import explain
explain("feed_update")
# يُعيد: لماذا موجود، من أي ADR، ما القاعدة خلفه
```

**ب. مطوّر يتصفح كل القرارات:**
```python
from titan.light import decisions
for d in decisions(status="Accepted"):
    print(d.number, d.title, d.rule)
```

**ج. أداة تحليل تسأل عن الفلسفة:**
```python
from titan.light import rules
for r in rules(status="Accepted"):
    print(f"ADR-{r.number}: {r.rule}")
```

**د. بحث سريع بالكلمة المفتاحية:**
```python
from titan.light import search
for r in search("middleware"):
    print(r.number, r.title, r.relevance)
```

---

## 6. ما الذي سيُرفض في v1 عمداً

| المرفوض | السبب |
|---|---|
| استدعاء LLM API خارجي بشكل إجباري | تبعية خارجية تتعارض مع فلسفة v1 |
| توليد كود أو اقتراح implementation | خارج النطاق — Architect يُجيب، لا يبني |
| تحليل كود المشروع (AST) | تعقيد ضخم + يتداخل مع `inspect`/`lint` |
| Persistent memory (تذكر محادثات) | لا persistence layer في Titan |
| Training أو fine-tuning | خارج نطاق مكتبة Python |
| تحليل performance أو metrics | هذا شأن `titan.profiler` |
| Context عن بوت المستخدم تلقائياً | opt-in فقط — لا spy على `bot` بدون طلب صريح |

---

## 7. التوترات المفتوحة — تحتاج قراراً قبل ADR

الميزة تحتاج إجابة على هذه الأسئلة قبل أن يُكتب ADR:

**السؤال أ:** هل v1 rule-based/keyword فقط (بدون LLM)؟  
أم يشمل LLM integration اختياري (pluggable backend)؟

**السؤال ب:** هل تعيش في `titan.light` (domain منفصل)؟  
أم هناك منطق لجزء منه في `bot.ask()` أو `bot.explain()`؟

**السؤال ج:** ما الـ API الأدنى الذي يجعل v1 مفيداً حقاً؟  
`search()` فقط؟ أم `check_against_rules()` + `explain()` + `philosophy()`؟

**السؤال د:** من هو المستهلك الأساسي في v1 — المطور البشري أم أداة/AI خارجي؟  
هذا يحدد شكل الـ output: human-readable strings أم structured data.

---

## 8. القرارات النهائية — مُحسومة

**أ. v1 rule-based فقط.**
لا LLM backend في v1. المعرفة محددة النتائج — `search()` و`explain()` و`rules()` و`decisions()`
تقرأ `titan.timeline` مباشرةً. LLM اختياري لاحقاً كـ interpretation backend.

**ب. `titan.light` — domain منفصل (الاسم الرسمي: Titan Light).**
لا يُلحق بـ `bot`. Bot هو محرك التنفيذ — Titan Light مستهلكة لأنظمة المعرفة.

**ج. API v1: `search()` + `explain()` + `rules()` + `decisions()`.**
`check_against_rules()` مؤجّل — يتداخل مع Design Linter ويفترض تحليل كود.

**د. المستهلك الأساسي: مطوّر بشري.**
الـ output مقروء ومُهيكل في نفس الوقت — human-readable strings + structured data
حتى تستطيع الأدوات وأنظمة AI الخارجية استهلاكه مستقبلاً.

راجع: [docs/decisions/014-architect-ai.md](../decisions/014-architect-ai.md)
