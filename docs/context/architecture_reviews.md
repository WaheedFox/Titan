# Context: Architectural Review Session (Execution Model)

## Purpose

هذا الملف يحفظ السياق المعماري الدائم لسلسلة مراجعات Titan. لا يُلخَّص — يُقرأ كمرجع.

إذا تعارض محتوى هذا الملف مع ADR أو وثيقة تحقيق أحدث، الوثيقة الأحدث هي المرجع.

---

## المنهجية المعتمدة

لكل مراجعة:

1. ابدأ من مشكلة حقيقية في الاستخدام الفعلي (GitHub Issues، Reddit، Stack Overflow).
2. حلّل الجذر المعماري — لا الحل الذي اختاره الإطار الآخر.
3. تحقق من التنفيذ الفعلي لـ Titan قبل استخلاص أي نتيجة.
4. قارن الجذر مع Titan: هل المشكلة موجودة؟ هل يمنعها التصميم؟ هل هناك نقص حقيقي؟
5. انتهِ بقرار واحد فقط: **Adopt / Adapt / Reject** مع سبب هندسي.

**قاعدة الترتيب:** لا نراجع طبقة تعتمد على طبقة أخرى قبل استقرار الأخيرة.

**مقارنة الأطر:** ليست لاختيار سلوك إطار بعينه أو تقليده. هدفها استخراج المشكلة المعمارية المشتركة فقط. القرار النهائي ينبثق من عقد Titan وفلسفته.

**النتيجة المقبولة تماماً:** "لا حاجة لأي تغيير."

---

## ترتيب التحقيقات

### مكتملة

| # | المجال | الملف | القرار |
|---|---|---|---|
| 1 | API Evolution & Unknown Update Types | `docs/internal/investigations/api-evolution-unknown-types.md` | Adopt + Adapt + Reject |
| 2 | Conversation State & Multi-step Flows | `docs/internal/investigations/conversation-state-multi-step-flows.md` | Reject |
| 3 | Error Handling & Propagation | `docs/internal/investigations/error-handling-propagation.md` | Adapt — **مُنفَّذ** |
| 4 | Update Routing & Filtering | `docs/internal/investigations/update-routing-filtering.md` | Reject |
| 5 | Middleware Granularity | `docs/internal/investigations/middleware-granularity.md` | Reject |
| 6 | Rate Limiting & Flood Control | `docs/internal/investigations/rate-limiting-flood-control.md` | Adapt (retry_after) + Reject (throttling) — **مُنفَّذ** |
| 7 | Webhook vs Polling | `docs/internal/investigations/webhook-vs-polling.md` | Reject — **معتمد** |
| 8 | Application-level State & Context Enrichment | `docs/internal/investigations/application-state-context-enrichment.md` | Reject — **معتمد** |
| 9 | Library Statistics & Project Profile | `docs/internal/investigations/library-statistics.md` | Adapt — Project Profile توثيقي، لا Statistics Subsystem |

| 10 | Repository Cleanup & File Rationalization | `docs/internal/investigations/repository-cleanup.md` | تقرير — لا تعديلات بعد |
| 11 | System Directory Architecture | `docs/internal/investigations/system-directory-architecture.md` | Adapt — Lifecycle Management (نطاق محدود) |

### التالي

لا تحقيقات مجدولة حالياً.

---

## قرارات معمارية دائمة

### فصل المسؤوليات في معالجة الـ updates

- `BotApiTranslator` مسؤوليته الترجمة فقط. لا تُضاف إليه سياسة.
- سياسة التعامل مع updates غير المدعومة أو غير المعروفة تُملَك بالكامل من `dispatch()` في `_handle_update`.
- **Unsupported update:** معروف في Telegram، Titan لم يبنِ له route — قرار واعٍ أو تأجيل.
- **Unknown update:** أُضيف بعد بناء الإصدار — لا قرار اتُّخذ بشأنه.
- السياسة لكليهما: drop صريح — لا يصل لأي handler، لا يُعامَل كخطأ، لا يؤثر على polling.

### "بلا route" ≠ "بلا handler"

- *بلا route:* Titan لا تعرف كيف تُصنّف هذا الـ update في نموذجها — النوع غير مدعوم أو غير معروف.
- *بلا handler:* النوع معروف لـ Titan، لكن المطور لم يُسجّل handler لهذا الحدث.
- الحالة الأولى تعامَل بـ drop صريح. الحالة الثانية سلوكها موثق منفصلاً.

### نموذج Conversation State

- `ask()` هو coroutine حقيقي، لا state machine. الحالة هي call stack، لا تخزين خارجي.
- هذا يُلغي الجذر المعماري الذي أجبر PTB وaiogram على بناء ConversationHandler وFSM.
- القيود (لا persistence، لا timeout مدمج، رسائل غير نصية تُحلّ بـ "") حدود نطاق واعية.

### Error Handling

- كل استثناء يصل لـ `_handle_error` بضمان بنيوي — لا مسار ينتهي بـ unhandled exception.
- الفجوة كانت في السياق التشخيصي في مسار الـ fallback — **مُصلَحة** (Adapt).

### Rate Limiting & Flood Control

- Outbound Throttling: ينتمي للـ middleware، ليس للـ Core — مُوثَّق في CONTRACT §10 (Reject).
- `retry_after`: `parameters.retry_after` من استجابة 429 يُعرَض الآن كحقل منفصل في `TelegramError` — **مُنفَّذ** (Adapt).
- مبدأ ظهر من هذا التحقيق ومن #3: **External Protocol Data Preservation** — البيانات المنظمة الواردة من النظام الخارجي لا تُختزل إلى نص قبل أن تصل للمطور. مُضاف كمبدأ #6 في `docs/architecture/design_principles.md`.

### Update Routing & Filtering

- نموذج routing بـ string key فقط دون predicates قرار نطاق واعٍ في هذه المرحلة.
- الضغط الذي يُحوِّل الجذر إلى مشكلة معمارية (بوتات كبيرة، فرق متعددة) لم يظهر بعد في Titan's scope.
- Reject: لا Filters system حتى يظهر ضغط استخدام حقيقي يُبرّره.
