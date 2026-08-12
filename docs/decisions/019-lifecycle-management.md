# 019 — Lifecycle Management Layer

**Status:** Accepted

---

## Proposal

استخراج منطق دورة حياة تشغيل البوت من `bot.py` إلى طبقة داخلية منفصلة:
تحديداً حلقة polling والـ backoff وإغلاق الـ workers والإشارات (signals).

---

## Context

`Titan.run_async()` في `bot.py` تحمل مسؤوليتين متمايزتين:

1. **تنسيق الدورة:** بدء الجلسة، جلب الهوية، تسجيل الإشارات، الإغلاق.
2. **تفاصيل الحلقة:** جلب التحديثات، الـ backoff، التوزيع على الـ workers.

المسؤولية الثانية قابلة للاستخراج بشكل نظيف دون أي تغيير في Public API.

---

## Decision

### ١. طبقة داخلية جديدة: `titan/lifecycle/`

مجلد داخلي يحتوي على:

- `runner.py` — `PollingRunner`: حلقة polling وبروتوكول الإغلاق.
- `signals.py` — `install` / `uninstall`: تسجيل SIGTERM/SIGINT.

`bot.py` تبقى نقطة التنسيق — تستدعي الطبقة الداخلية، لا العكس.

### ٢. اسم المجلد: `lifecycle/` لا `system/`

`system/` محجوز للاستخدام المستقبلي المتعلق بالنظام البيئي للمشروع
(الخدمات الرسمية، المساهمون، الاشتراكات، الخدمات المصاحبة).

`lifecycle/` يصف المسؤولية الفعلية بدقة: إدارة دورة حياة تشغيل البوت —
بدء → حلقة → إغلاق. لا التباس مع أي استخدام مستقبلي آخر.

### ٣. الحدود الصارمة

- **لا public API:** `lifecycle/` داخلي بالكامل. لا يُصدَّر من `titan/__init__.py`.
- **لا event bus:** التواصل عبر استدعاء مباشر فقط.
- **لا subsystem registry:** كل dependency تُمرَّر صراحةً في `__init__`.
- **لا نقل ملفات حالية:** الكود القائم يبقى في مكانه.
- **Public API محمية:** توقيع `run()` و`run_async()` لا يتغير.

### ٤. `PollingRunner`

```python
runner = PollingRunner(
    api=self._api,
    handle_update=self._handle_update,
    chat_id_from_raw=self._chat_id_from_raw,
    ensure_chat_worker=self._ensure_chat_worker,
    chat_queues=self._chat_queues,
    chat_workers=self._chat_workers,
    log=self._log,
)

await runner.run(initial_offset=..., debug=..., offset_updated=...)
await runner.shutdown()
```

`run()` تتوقف عند CancelledError أو أي BaseException غير قابلة للمعالجة.
`shutdown()` ترسل sentinel لكل worker وتنتظر انتهاءه.

### ٥. `signals.py`

يُثبّت معالجات SIGTERM وSIGINT تُلغي الـ task الجاري،
فتُشغَّل كتلة `finally` في `run_async()` — نفس مسار الإغلاق النظيف.

No-op على Windows وفي بيئات لا تدعم إضافة signal handlers.

---

## Rule

`lifecycle/` طبقة داخلية بحتة. أي تغيير يجعلها مرئية للمطوّر
(export في `__init__.py`، ذكر في docs العامة، إضافة إلى Public API)
يتطلب ADR منفصلاً.

---

## Consequences

**ما يُكتسب:**
- `bot.py` تصف التنسيق فقط — تفاصيل الحلقة لا تلوّث الكلاس الرئيسي.
- SIGTERM يُشغّل نفس مسار الإغلاق النظيف كـ KeyboardInterrupt.
- `PollingRunner` قابل للاختبار بشكل مستقل دون الحاجة لـ `Titan` كاملاً.

**القيود المقبولة:**
- `PollingRunner` تحتاج تمرير عدة dependencies — هذا تصميم، لا عيب.
  التبعيات الصريحة أفضل من التبعيات المخفية.
- لا تغيير في السلوك الخارجي — هذا refactoring داخلي بحت.

**ما يبقى خارج نطاق هذا القرار:**
- Webhook mode (إن جاء) — مسار منفصل لا يمر بـ `PollingRunner`.
- آلية restart تلقائي — خارج v1.
- تسجيل metrics لحلقة polling — خارج نطاق هذا الـ ADR.
