# ADR-009 — Runtime Contract Validator

**الحالة:** مقبول  
**التاريخ:** 2026-07-10

---

## السياق

Titan يتحقق من التعارضات عند التسجيل (أمر مكرر، callback مكرر، router مُضمَّن مرتين)، لكنه لا يتحقق من أن الـ callable المُسجَّل نفسه صالح لتنفيذه.

ثلاثة عقود لا يُتحقق منها:

| العقد | التوقيع الصحيح |
|---|---|
| Handler | `async def f(ctx)` |
| Middleware | `async def f(ctx, next)` |
| Error Handler | `async def f(ctx, exc)` |

انتهاك أي منها لا يُكتشَف حتى وصول update فعلي، حيث يصدر `TypeError` أو `RuntimeWarning` من داخل Titan بعيداً عن سطر التسجيل.

---

## القرار

### 1 — الصرامة

أي انتهاك للعقد يرفع `TitanError` فوراً عند تنفيذ decorator التسجيل — أي أثناء تحميل الملف (import time)، وليس عند `bot.run()`.

لا Warning، لا HealthFinding. إذا كان الكود لن يعمل أبداً، لا يُسمح بتسجيله.

### 2 — عمق الفحص

يُتحقق من:
1. **asyncness** — هل الدالة coroutine function؟
2. **عدد الـ parameters** — هل يطابق العقد؟

**تُحسب فقط:** parameters من نوع `POSITIONAL_ONLY` أو `POSITIONAL_OR_KEYWORD`، باستثناء `self`. لا تُحسب `*args` أو `**kwargs`.

| نوع التسجيل | عدد المعاملات المطلوب |
|---|---|
| handler (`@command`, `@on`, `@callback`) | 1 |
| middleware | 2 |
| error handler | 2 |

### 3 — Callable Objects

Callable objects ذات `__call__` async مدعومة كـ first-class citizens.

```python
class StartHandler:
    async def __call__(self, ctx): ...

bot.command("start")(StartHandler())  # ✓ مقبول
```

عند فحص callable object: يُفحص `func.__call__`، وتُستثنى `self` من العد.

### 4 — الموقع المعماري

ملف واحد مشترك: `src/titan/validation.py`

ثلاث دوال عامة:
- `validate_handler(func) → None`
- `validate_middleware(func) → None`
- `validate_error_handler(func) → None`

لا منطق مكرر داخل decorators. كل نقطة تسجيل تستدعي الدالة المناسبة.

### 5 — مبدأ "Fail as Early as Possible"

التحقق يحدث في **أقرب نقطة تسجيل**:
- `@router.command()` → يتحقق Router عند التسجيل
- `@bot.command()` → يتحقق Bot عند التسجيل
- `bot.include()` **لا يُعيد** التحقق — الـ handlers المُدمَجة من Router فُحصت مسبقاً

---

## البدائل المرفوضة

**Warning بدلاً من TitanError:** رُفض لأن التحذيرات تُتجاهَل. الخطأ قاطع لأن الكود لن يعمل أبداً.

**HealthFinding:** رُفض لأن HealthFinding مخصصة للأمور القابلة للتشغيل لكن المشكوك فيها، لا للأخطاء البرمجية القاطعة.

**التحقق في `bot.run()`:** رُفض لأنه يؤخر الاكتشاف. الهدف: إخبار المطور قبل تشغيل أي شيء.

---

## العواقب

- **إيجابي:** أخطاء العقد تُكتشَف لحظة تحميل ملف البوت.
- **إيجابي:** رسالة الخطأ تشير مباشرةً للمشكلة (sync/signature) ونوع التسجيل.
- **إيجابي:** Router يوفر حماية مستقلة — لا يعتمد على `include()`.
- **محايد:** callable objects تحتاج `__call__` async — سلوك مقصود وموثق.
