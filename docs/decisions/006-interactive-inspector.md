# 006 — Interactive Inspector

**Status:** Accepted

---

## Proposal

إضافة `bot.inspect()` — طريقة تُرجع snapshot مهيكلة عن الحالة التسجيلية الكاملة للبوت:
الأوامر المسجلة، الـ callbacks، الـ event handlers، الـ middleware، وجود error handler، وعدد الـ routers المدمجة.

---

## Investigation

→ [docs/internal/investigations/interactive-inspector.md](../internal/investigations/interactive-inspector.md)

المشكلة الحقيقية: البوت يبني حالته تدريجياً (`commands`, `handlers`, `callback_handlers`, `middleware_chain`) لكنه لا يُقدّم طريقة للاستعلام عن هذه الحالة كوحدة واحدة.

المطور يحتاج أحياناً أن يعرف: هل اندمج الـ router فعلاً؟ هل دخل الـ middleware؟ كم callback مسجل؟ هذه ليست حالة متقدمة — بل جزء من فهم البوت أثناء التطوير، وركيزة لأدوات قادمة (Architect AI).

---

## Decision

### Core أم Extra؟

**Core.** `bot.inspect()` ليست أداة debugging اختيارية — هي قدرة أساسية للإطار نفسه: القدرة على الإجابة عن "ما حالة Titan الحالية؟"

Project Health يجيب: "هل توجد مشكلة؟"  
Interactive Inspector يجيب: "ما الذي يوجد؟"

السؤال الثاني أسبق من الأول، وكلاهما يستحق `bot.method()` مباشرة.

**القاعدة:** `bot.inspect()` نعم. كشف attributes الداخلية بشكل مباشر: لا.

---

### نوع الإرجاع

**`BotSnapshot` dataclass — frozen.**

- `dict` خام: لا — لا contract، لا IDE completion، لا استقرار.
- `TypedDict`: لا — حل وسط لا يعيش طويلاً ولا يُعبّر عن فلسفة Titan.
- `BotSnapshot` dataclass مجمّدة: نعم — عقد واضح، قابل للـ type annotation، لا يتغير بالإسناد العرضي.

**Root Export Policy:** `BotSnapshot` يُصدَّر من الجذر (`from titan import BotSnapshot`) لأن المطور يحتاجه للـ type annotation عند استخدام `bot.inspect()`. يستوفي الشرطين: يظهر في return type لدالة public، ومستقر.

---

### مستوى التفاصيل في v1

أسماء لكل ما له معرّف طبيعي من التسجيل. Counts لما لا معرّف له.

```python
@dataclass(frozen=True)
class BotSnapshot:
    commands: tuple[str, ...]       # ("start", "help") — الأسماء المسجلة
    callbacks: tuple[str, ...]      # ("yes", "no")     — الـ callback_data
    events: dict[str, int]          # {"message": 2}    — حدث → عدد handlers
    middleware_count: int            # 3                 — لا اسم طبيعي
    has_error_handler: bool          # True/False
    included_router_count: int       # 2
    capabilities_available: bool     # True إذا bot.capabilities ≠ None
```

**ما لا يُرجعه v1:**

- الـ Handler objects نفسها — handler الداخلي ليس عقداً عاماً.
- مصادر التسجيل (أي router أضاف هذا الأمر) — تُؤجَّل لـ v2 إذا ثبتت الحاجة.
- الـ capabilities التفصيلية — Inspector يُشير إلى وجودها فقط (`capabilities_available`). التفاصيل في `bot.capabilities` مباشرةً.
- أي حكم أو تقييم — هذا عمل Health.

---

### Capabilities في Inspector

Inspector لا يُقيّم ولا يُصدر أحكاماً.

```python
# ✅ مقبول في Inspector
capabilities_available = False   # حقيقة وصفية

# ❌ ممنوع في Inspector
"inline supported but unused"   # هذا عمل Health
```

المطور الذي يريد التفاصيل يقرأ `bot.capabilities` مباشرةً.

---

### `MiddlewareChain.count`

يُضاف **ضمن هذه الميزة** — لأن Inspector كشف أن `_chain` private state أصبح معلومة يحتاجها النظام. إضافتها كـ property public في `MiddlewareChain` هي الحل الأنظف:

```python
@property
def count(self) -> int:
    return len(self._chain)
```

Inspector يقرأ `bot.middleware_chain.count` وليس `bot.middleware_chain._chain` مباشرةً.

---

## Rule

**Inspector يصف، ولا يُقيّم.**

أي منطق يُصدر حكماً ("مشكلة"، "غير مستخدم"، "مفقود") لا يدخل Inspector — يذهب إلى Health.

`BotSnapshot` snapshot وصفية خالصة: ما يوجد، ليس ما يجب أن يوجد.

---

## Alternatives Considered

**Extra بدلاً من Core:**  
`from titan.extras import Inspector` — لكن هذا يعني أن أداة فهم الحالة الأساسية للبوت مخفية خلف import اختياري. معظم المطورين لن يجدوها إلا بعد أن تتعقد مشكلتهم. الـ Core placement ضمان الوصول.

**`TypedDict` بدلاً من dataclass:**  
لا يُعبّر عن ثبات الـ snapshot. `frozen=True` يجعل الـ snapshot قراءة فقط — وهو ما يجب أن يكون.

**مصادر التسجيل في v1:**  
`_command_sources` موجودة داخلياً. أُجّلت لأن تضمينها يُضخّم النموذج قبل أن تثبت الحاجة الفعلية لها خارج الـ debugging.

---

## Consequences

**المكتسب:**
- `bot.inspect()` كنقطة وصول موحدة لحالة البوت التسجيلية.
- `BotSnapshot` كعقد واضح قابل للـ type annotation.
- `MiddlewareChain.count` يُحل مشكلة الـ private state الصامتة الموثقة في ROADMAP.md.
- أساس لـ Architect AI التي ستحتاج snapshot مهيكلة عن البوت.

**المقبول:**
- نوع جديد (`BotSnapshot`) في الـ root exports — مقبول بشرط استيفاء Root Export Policy.
- `MiddlewareChain` تكتسب property جديدة — تعديل صغير في Core.
