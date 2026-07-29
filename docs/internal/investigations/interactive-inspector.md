# تحقيق — Interactive Inspector

**الحالة:** مكتمل — القرار في [docs/decisions/006-interactive-inspector.md](../decisions/006-interactive-inspector.md)  
**تاريخ:** 2026-07-08  
**الميزة:** Interactive Inspector (#1) — الأولى في الـ Roadmap

---

## 1. المشكلة

**من منظور المطور:**  
"سجّلت handlers وأوامر وcallbacks وضممت routers — لكن لا توجد طريقة لأرى ما تم تسجيله فعلاً دون تشغيل البوت أو قراءة الكود من أوله."

البوت يبني حالته تدريجياً (`commands`, `handlers`, `callback_handlers`, `middleware_chain`) لكنه لا يُقدّم طريقة للاستعلام عن هذه الحالة كوحدة واحدة.

**الفرق عن Project Health:**  
| | Inspector | Health |
|---|---|---|
| السؤال | ماذا يوجد؟ | هل ما يوجد سليم؟ |
| الدور | مرآة | طبيب |
| يُصدر أحكاماً | لا | نعم |
| يعرض | كل شيء | المشكلات فقط |

Inspector يصف. Health يُقيّم. الاثنان مكمّلان ولا تداخل.

---

## 2. ما يوجد حالياً في الـ Core

### البيانات المتاحة للقراءة المباشرة (pre-run)

| المصدر | البيانات | النوع | الوصول |
|---|---|---|---|
| `bot.commands` | الأوامر المسجلة | `dict[str, Handler]` | public |
| `bot.handlers` | الـ event handlers | `dict[str, list[Handler]]` | public |
| `bot.callback_handlers` | الـ callback handlers | `dict[str, Handler]` | public |
| `bot.middleware_chain._chain` | الـ middlewares | `list[Middleware]` | private (`_chain`) |
| `bot._error_handler` | error handler | `ErrorHandler \| None` | private |
| `bot._command_sources` | مصدر كل command | `dict[str, str]` | private |
| `bot._callback_sources` | مصدر كل callback | `dict[str, str]` | private |
| `bot.banned_users` | المحظورون | `set[int]` | public |
| `bot.capabilities` | قدرات الحساب | `BotCapabilities \| None` | public (post-run) |

### الملاحظات الأولية

- `bot.commands` و`bot.handlers` و`bot.callback_handlers` مكشوفة مباشرةً لكنها بنية خام — لا توجد طريقة مهيكلة للاستعلام عنها كتقرير.
- `middleware_chain._chain` وراء `_` أي private — Inspector لا يجب أن يعتمد على private attributes.
- `_error_handler` كذلك private.
- `_command_sources` و`_callback_sources` private وتحتوي معلومات قيّمة (مصدر التسجيل — مباشر أو via router).

---

## 3. هل المشكلة حقيقية؟

نعم، بثلاثة سياقات عملية:

**أ) التطوير والـ debugging:**  
المطور يضيف `include(router)` ويريد التحقق أن الأوامر انتقلت فعلاً ولم يحدث conflict صامت.

**ب) الـ tooling:**  
Project Health تحتاج "ماذا يوجد" كمدخل قبل أن تُقيّم. حالياً تقرأ `bot.commands` مباشرةً — Inspector سيوفر نقطة وصول واحدة موثقة.

**ج) المستقبل (Architect AI):**  
Architect AI ستحتاج snapshot مهيكل عن البوت. بدون Inspector، ستعتمد هي أيضاً على القراءة المباشرة من attributes متعددة.

---

## 4. المدخلات الصامتة (مشكلات ملاحظة تزيد قيمة الـ Inspector)

من `ROADMAP.md` قسم "سلوكيات صامتة مُكتشفة":

- `bot.commands` / `bot.handlers` / `bot.callback_handlers` مكشوفة للكتابة المباشرة. Inspector يُقدّم طريقة للقراءة الآمنة بدون فتح السطح أكثر.
- لا توجد طريقة لمعرفة عدد الـ middlewares المسجلة بدون الوصول لـ `_chain`.

---

## 5. أشكال التنفيذ الممكنة

### الشكل أ — `BotSnapshot` dataclass

```python
snapshot = bot.inspect()
# snapshot.commands    → list[str]
# snapshot.events      → dict[str, int]  (event → عدد handlers)
# snapshot.callbacks   → list[str]
# snapshot.middleware_count → int
# snapshot.has_error_handler → bool
```

`bot.inspect()` تُرجع `BotSnapshot` — نوع جديد يُصدَّر من الـ Core.

**مزايا:** نوع واضح، قابل للـ type annotation، Inspector ودواخله معزولة.  
**مساوئ:** نوع جديد في الجذر = سطح إضافي.

### الشكل ب — `BotSummary` كـ TypedDict

```python
summary = bot.inspect()
summary["commands"]  # list[str]
summary["events"]    # dict[str, int]
```

**مزايا:** لا نوع جديد في الـ contract.  
**مساوئ:** TypedDict أضعف في الـ IDE support، ويُفقد إمكانية الـ method attachment مستقبلاً.

### الشكل ج — `bot.inspect()` يُرجع `dict` خاماً

```python
snapshot = bot.inspect()
snapshot["commands"]  # list[str]
```

**مزايا:** صفر تعقيد.  
**مساوئ:** لا contract رسمي، سهل الكسر، لا IDE completion.

---

## 6. التوترات المعمارية

### التوتر 1 — هل Inspector يكشف الـ private state؟

`_chain` و`_error_handler` private. Inspector يحتاج هذه المعلومات لإعطاء صورة كاملة.

الخيارات:
- **أ:** Inspector يقرأ `_chain` مباشرةً (coupling داخلي مقبول — في نفس الحزمة)
- **ب:** Inspector يُطلب من `middleware_chain` الكشف عن `count` كـ property public

**الأرجح:** خاصية `count` في `MiddlewareChain` هي الحل الأنظف وتُحل مشكلة `ROADMAP.md` الصامتة أيضاً.

### التوتر 2 — هل Inspector جزء من الـ Core أم Extra؟

- **Core:** `bot.inspect()` — كل مطور يجد الـ snapshot بدون import إضافي.
- **Extra:** `from titan.extras import Inspector; Inspector(bot).snapshot()` — لا يلوّث الـ contract الأساسي.

**مؤشر:** Project Health (`bot.health()`) قرارها كان Core لأن "المشكلة شائعة والتكلفة صغيرة". نفس الحجة تنطبق على Inspector — لكن تحتاج تأكيداً في النقاش المعماري.

### التوتر 3 — مستوى التفاصيل

هل Inspector يُرجع:
- أسماء الـ handlers فقط (function names كـ strings)؟
- بيانات شاملة (source، modules)؟
- count فقط؟

الأسماء هي الحد الأدنى المفيد. المعلومات الإضافية (مصدر التسجيل) موجودة في `_command_sources` وتُضيف قيمة للـ debugging.

---

## 7. الأسئلة المفتوحة للنقاش المعماري

1. **Core أم Extra؟** — هل `bot.inspect()` تستحق السطح المجمّد، أم تبقى in `extras`؟

2. **نوع الإرجاع** — `dataclass`، `TypedDict`، أم `dict` خام؟

3. **مستوى التفاصيل** — هل نُرجع الأسماء (strings) أم فقط العدد (ints)؟

4. **الـ middleware count** — هل نُضيف `len()` / `count` property إلى `MiddlewareChain` بشكل منفصل أم كجزء من Inspector؟

5. **الـ capabilities** — Inspector يعمل pre-run. هل يُشير إلى غياب capabilities بدون رأي؟ (مثلاً `capabilities_available: bool`)

---

## 8. تقييم أولي

**المشكلة حقيقية:** نعم — غياب snapshot مهيكل هو ثغرة فعلية في observability البوت.

**التداخل مع Health:** لا تداخل — الفصل واضح من ADR-005.

**الحجم المتوقع:**
- نموذج واحد (`BotSnapshot` أو ما يُقرر)
- دالة واحدة `bot.inspect()`
- لا checks، لا runner منفصل
- أبسط بكثير من Project Health

**التبعيات:** إذا قرر النقاش المعماري إضافة `count` لـ `MiddlewareChain`، هذا يُعدّ تعديلاً صغيراً على الـ Core قبل كتابة Inspector.
