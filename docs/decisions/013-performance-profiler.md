# 013 — Performance Profiler

**Status:** Accepted

## Proposal

أداة تتيح للمطور قياس أداء البوت وفهم أين يُقضى الوقت خلال معالجة كل update،
دون الحاجة لبوت متصل حقيقياً.

المشكلة من منظور المطور:
> "البوت يعمل، لكنه يبدو بطيئاً — ولا أعرف أين المشكلة بالضبط."

---

## Investigation

### ما لا تستطيع inspect/health/lint اكتشافه

الأدوات الثلاث تقرأ **حالة تسجيل ثابتة**. الـ Profiler يحتاج ملاحظة **تنفيذ ديناميكي**.
هذا فارق في الطبيعة لا في التفاصيل.

### الاكتشاف الرئيسي من قراءة الكود

`feed_update()` هو entry point رسمي نظيف، موثَّق في CONTRACT، ويدعو `_handle_update`
بدون أي منطق مكرر:

```python
async def feed_update(self, update: dict[str, Any]) -> None:
    await self._handle_update(update)
```

هذا يعني: قياس wall time الكلي ممكن من **خارج Core بالكامل** بـ `time.perf_counter()`
قبل وبعد `await bot.feed_update(update)`. لا hooks مطلوبة.

في المقابل: `dispatch` داخل `_handle_update` هو closure لا method منفصلة.
تفكيك الوقت داخلياً يتطلب إعادة هيكلة `bot.py` أو إضافة conditionals داخل الـ closure —
تكلفة حقيقية على ملف كان بسيطاً.

### السؤال المحوري

**هل Profiler أداة تطوير فقط، أم مراقبة production أيضاً؟**

هذا السؤال يحكم الموقع المعماري الكامل:

| | أداة تطوير فقط | أداة production أيضاً |
|---|---|---|
| يحتاج Core changes | ❌ لا | ✅ نعم — state + hooks |
| يرى real Telegram updates | ❌ لا | ✅ نعم |
| overhead في production | ❌ صفر | ⚠️ opt-in فقط |

**القرار: أداة تطوير فقط في v1.**

المطور الذي يريد فهم أداء البوت قبل الإطلاق يحتاج بيئة محكومة قابلة للتكرار —
وهذا ما يوفره Playground بالضبط. رؤية real updates تخص production monitoring،
وهو قرار مستقل لا يُتخذ إلا إذا ظهر use case حقيقي.

### التوترات الأربعة — مُحسومة جميعاً بهذا القرار

| التوتر | الحل |
|---|---|
| أين يعيش؟ | `titan.profiler` — domain منفصل، Playground-based |
| ماذا يقيس؟ | Wall time كلي per event type — لا تفكيك مراحل |
| كيف يُشغَّل في الـ pipeline؟ | يُقاس من الخارج عبر `feed_update()` — لا hooks |
| development tool أم production؟ | أداة تطوير فقط في v1 |

---

## Decision

**`titan.profiler` — domain منفصل، يبني فوق `feed_update()` + `titan.playground`.**

لا تعديلات في Core. لا state جديدة على `bot`. لا overhead في production.

### النماذج

```python
@dataclass(frozen=True)
class ProfileEntry:
    event_type: str    # "command/start"، "callback/yes"، "message"، "channel"، ...
    duration_ms: float # wall time الكلي — perf_counter بعد − قبل
    metadata: dict     # مفتوح للتوسع — فارغ {} في v1

class ProfilingSession:
    entries: list[ProfileEntry]

    def summary(self) -> dict[str, dict[str, float]]:
        """count / avg_ms / min_ms / max_ms لكل event_type."""
        ...
```

**قرار تصميمي: `metadata: dict` بدلاً من حقول متخصصة**

النموذج لا يحتوي على `handler_time` أو `middleware_time` أو `routing_time` —
لأن هذه تفترض تفكيكاً داخلياً يحتاج Core hooks (خارج نطاق v1).

`metadata` يُبقي الباب مفتوحاً لـ `ProfileTrace` المستقبلي:

```
ProfileTrace (v2 أو لاحقاً):
    update
     ├── context_building: 0.2ms
     ├── middleware: 1ms
     ├── handler: 10ms
     └── telegram_api: 50ms
```

هذا قرار مستقل يتطلب Core hooks — لا يُبنى الآن.
في v1، كل إدخال يُنشأ بـ `metadata={}`.

**`metadata` ليست عقداً ثابتاً**

Titan لا تضمن محتويات `metadata` في v1.
المستهلكون لا يجب أن يبنوا كوداً يعتمد على مفاتيح داخلها:

```python
# ✅ صحيح — يستخدم فقط الحقول المضمونة
entry.event_type   # "command/start"
entry.duration_ms  # 12.4

# ❌ خطأ — metadata ليست عقداً
entry.metadata["handler_name"]   # غير مضمون
entry.metadata["middleware_count"]  # غير موجود في v1
```

مفاتيح مثل `handler_name` و`middleware_count` غير موجودة في v1 أصلاً —
إضافتها كعقد الآن ستجعل المستهلكين يبنون اعتماداً على شيء لم نعد به.

### الـ API

```python
from titan.profiler import profile_update
from titan.playground import fake_command, fake_message, fake_callback

# قياس أمر معين 100 مرة
session = await profile_update(bot, fake_command("start"), n=100)
print(session.summary())
# {
#   "command/start": {"count": 100, "avg_ms": 1.2, "min_ms": 0.8, "max_ms": 4.3}
# }

# قياس أنواع متعددة
session = await profile_update(bot, fake_message("hello"), n=50)
```

### استنتاج event_type

يُستنتج من بنية الـ update dict — لا يُمرَّر صريحاً:

| الشرط | event_type |
|---|---|
| `callback_query` موجود | `"callback/{data}"` |
| `message.text` يبدأ بـ `/` | `"command/{name}"` |
| `channel_post` موجود | `"channel"` |
| `new_chat_members` موجود | `"new_member"` |
| `left_chat_member` موجود | `"left_member"` |
| غير ذلك | `"message"` |

### ما يُرفض بوعي في v1

| المرفوض | السبب |
|---|---|
| Percentiles (p50/p95/p99) | تحتاج مكتبة إحصائيات — ليس v1 |
| تفكيك الوقت (middleware vs routing vs handler) | يتطلب Core hooks |
| Network timing (Telegram API latency) | قرار production monitoring مستقل |
| Flame graphs / traces | نظام observability كامل — خارج النطاق |
| Production always-on | overhead دائم يتعارض مع stability-driven philosophy |
| تخزين دائم (DB/file) | لا persistence layer في Titan |
| Per-user profiling | PII concerns + scope ضخم |

---

## Rule

**يبني على ما هو موجود قبل إضافة ما هو جديد.**

إذا كانت الأداة تخدم التطوير فقط، فحدودها هي حدود بيئة التطوير — لا overhead في
production يُبرر complexity في Core. `feed_update()` وُجد لأسباب معمارية سليمة
(Playground، Userbot Support المستقبلي) — الـ Profiler يستفيد من هذا القرار دون
أن يطلب من Core شيئاً جديداً.

---

## Alternatives Considered

### Core opt-in (`bot.enable_profiling()` / `bot.profiling_report()`)
يتيح رؤية real Telegram updates ويُضيف تفكيكاً أعمق للمراحل. لكنه يحتاج
state وconditionals داخل `_handle_update`. هذه التكلفة مُبررة فقط إذا كان
الهدف production monitoring — وهو ليس الهدف في v1.

### دائماً مفعّل (مثل `health()`)
يُضيف overhead دائم في production. غير مقبول لمكتبة stability-driven.

---

## Consequences

### مكتسبات
- صفر تغييرات في Core — `bot.py` يبقى كما هو
- صفر overhead في production بالمطلق
- بيئة قياس محكومة: لا شبكة، نتائج قابلة للتكرار
- يستفيد من `feed_update()` الموجود — قرار معماري سابق يُثمر هنا

### قيود مقبولة
- لا يرى real Telegram updates — يقيس handler logic فقط، لا network latency
- لا تفكيك داخلي (middleware vs routing vs handler) في v1
- يعتمد على `titan.playground` لبناء fake updates

### حدود `titan.profiler`

`titan.profiler` ليس مُصدَّراً من جذر الحزمة — الاستيراد صريح دائماً:

```python
from titan.profiler import profile_update   # ✅
from titan import profile_update            # ❌ غير موجود
```

هذا متسق مع نمط `titan.playground` وسياسة Root Export.
