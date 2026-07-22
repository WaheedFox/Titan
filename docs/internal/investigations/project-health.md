# تحقيق — Project Health

**الحالة:** مكتمل — القرار في [docs/decisions/005-project-health.md](../decisions/005-project-health.md)  
**تاريخ:** 2026-07-08  
**الميزة:** Project Health — الميزة التالية في الـ Roadmap بعد Architectural Timeline (المؤجلة)

---

## 1. المشكلة

**من منظور المطور:**
"أنجزت تسجيل الـ handlers وشغّلت البوت، لكنني لا أعلم إن كان هناك ثغرات هيكلية أو handlers لن تُستدعى أبداً أو ضمانات تشغيلية مفقودة — حتى تحدث المشكلة فعلاً."

البوت يعمل بصمت سواء كان مكتملاً أم فارغاً.

---

## 2. ما يوجد حالياً في الـ Core

### البيانات المتاحة للفحص (pre-run)

| المصدر | ما يمثله |
|---|---|
| `bot.commands: dict[str, Handler]` | الأوامر المسجلة |
| `bot.handlers: dict[str, list[Handler]]` | الأحداث المسجلة (fan-out) |
| `bot.callback_handlers: dict[str, Handler]` | أزرار الـ inline المسجلة |
| `bot._error_handler` | هل يوجد معالج للأخطاء؟ (None = لا) |
| `bot.middleware_chain._chain: list` | الـ middleware المسجلة |
| `bot.banned_users: set[int]` | قائمة الحظر المحلية |
| `bot._included_routers: set[int]` | عدد الـ routers المُدمجة |

### البيانات المتاحة بعد الاتصال فقط (post-run)

| المصدر | ما يمثله |
|---|---|
| `bot.capabilities` | قدرات حساب البوت (من getMe) |
| `bot.capabilities.can_join_groups` | هل يمكنه دخول مجموعات؟ |
| `bot.capabilities.supports_inline_queries` | هل يدعم inline mode؟ |
| `bot.capabilities.can_read_all_group_messages` | هل privacy mode مُعطَّل؟ |

**ملاحظة:** `bot.capabilities` تُعيد `None` قبل أن يتصل البوت بـ Telegram (قبل `bot.run()`).  
هذا يعني أي فحص يعتمد عليها لا يمكن تشغيله قبل التشغيل.

---

## 3. هل المشكلة حقيقية؟

نعم. هذه الحالات موجودة ومُثبتة:

### الحالة 1 — بوت بلا handlers
```python
bot = Titan("token")
bot.run()
```
يعمل. لا خطأ. لا تحذير. كل رسالة تُتجاهل بصمت.

### الحالة 2 — بلا error handler
```python
@bot.command("start")
async def start(ctx):
    result = do_something_that_might_fail()
    await ctx.reply(result)

bot.run()
```
إذا رمت `do_something_that_might_fail()` استثناءً، يُطبع فقط:
```
Unhandled exception: ...
```
ويستمر البوت. لا يعلم المطور إلا بعد مراجعة الـ logs.

### الحالة 3 — capabilities غير مستغلة
```python
bot.run()
# bot.capabilities.supports_inline_queries == True
# لكن لا يوجد أي handler لـ inline_query
```
المطور فعّل Inline Mode في BotFather ثم نسي تسجيل الـ handler.

### الحالة 4 — handler مسجّل لا يُستدعى أبداً
```python
@bot.callback("confirm_order")
async def confirm(ctx): ...

# لكن لا يوجد في البوت كله InlineButton(callback_data="confirm_order")
```
الـ handler موجود ولا توجد طريقة لتشغيله.

---

## 4. الحجم الحقيقي للمشكلة

قبل تحديد أي حل، يجب تصنيف الفحوصات الممكنة:

| الفئة | الأمثلة | متى يمكن تشغيلها |
|---|---|---|
| **هيكلية — قبل التشغيل** | لا handlers، لا error handler، لا middleware | في أي وقت |
| **تشغيلية — بعد الاتصال** | capabilities vs handlers mismatch | بعد `bot.run()` (بعد getMe) |
| **منطقية — صعبة الكشف** | handler مسجّل لكن لا زر يستدعيه | تحتاج تحليل كامل للكود |

**الفئة الثالثة (منطقية) خارج نطاق أي أداة runtime — هي مشكلة static analysis.**

---

## 5. التوترات المعمارية

### التوتر 1 — التداخل مع Interactive Inspector (#1)

Interactive Inspector (المُنجز سابقاً) — ما هو بالضبط؟  
**يجب تحديد الحدود قبل تصميم أي شيء جديد.**

إذا كان Inspector يعرض الحالة (ماذا يوجد)،  
فـ Project Health يقيّمها (هل ما يوجد كافٍ؟).

لكن هذا الفرق يحتاج تأكيداً من السياق الفعلي لـ Inspector.

### التوتر 2 — هل هذا Core أم Extra؟

إضافة `bot.health()` كـ public method = إضافة إلى السطح المجمّد.  
فصلها في `titan.extras` = اختيارية، لا تُكلّف contract.

لكن إذا كانت المشكلة حقيقية وشائعة بما يكفي،  
الفصل قد يعني أن معظم المطورين لن يجدوها أبداً.

### التوتر 3 — static vs runtime

الفحوصات الأكثر قيمة (capabilities mismatch) تحتاج بيانات runtime.  
الفحوصات الأقل احتياجاً للبيانات (structural) يمكن تشغيلها قبل run().

أي من الاثنتين الأولوية؟

---

## 6. الخيارات المعمارية الأولية (للنقاش — لا قرار بعد)

**الخيار أ — Method على Titan**
```python
findings = bot.health()
# تُعيد list من نصوص أو كائنات
```
- مرئية للجميع
- تُضاف للـ contract المجمّد
- تتكامل طبيعياً مع `bot.run(debug=True)`

**الخيار ب — Extra Utility**
```python
from titan.extras import check_health
findings = check_health(bot)
```
- لا تلمس Core
- اختيارية
- قد تظل مجهولة لمعظم المطورين

**الخيار ج — جزء من `bot.run(debug=True)`**
```python
bot.run(debug=True)
# [titan.health] No error_handler registered
# [titan.health] supports_inline_queries=True but no inline handler found
```
- لا API جديد
- لكنها تربط Health بـ debug mode — وهما مفهومان منفصلان

**الخيار د — مرحلة من `run_async` قبل polling**
```python
async def run_async(self, ...):
    await self._api.start()
    await self._run_health_check()  # internal, يُطبع تحذيرات فقط
    await self._poll(...)
```
- تلقائية بدون أي API جديد
- لكنها سلوك خفي — تعارض مع فلسفة Titan الصريحة

---

## 7. الأسئلة المفتوحة للنقاش

1. **ما حدود Project Health مقابل Interactive Inspector؟**  
   هل Inspector يغطي جزءاً من هذا أم لا؟

2. **هل الأولوية للفحوصات الهيكلية (pre-run) أم التشغيلية (post-run)؟**  
   أم الاثنتان معاً؟

3. **Core أم Extra؟**  
   هل هذه أداة اختيارية للمطور المتقدم أم حاجة أساسية لكل مطور؟

4. **ماذا يُفعل بالـ findings؟**  
   هل تُطبع؟ تُرجع؟ تُرمى كـ warnings؟ تُسجَّل في logger؟

5. **هل يوجد مفهوم "خطورة" للـ findings؟**  
   غياب error handler (خطير) ≠ غياب middleware (مقبول تماماً).

---

---

## 8. جاهزية القرار

التحقيق مكتمل. يمكن الانتقال للنقاش المعماري بعد الإجابة على هذه الأسئلة:

| السؤال | لماذا ضروري قبل التصميم |
|---|---|
| ما حدود Project Health مقابل Interactive Inspector؟ | تحديد ما يجب بناؤه فعلاً وما هو مكرر |
| الأولوية: هيكلية (pre-run) أم تشغيلية (post-run)؟ | يحدد ما إذا كانت الـ API تحتاج connection أم لا |
| Core أم Extra؟ | يحدد ما إذا كانت ستُضاف للـ contract المجمّد |
| ماذا يُفعل بالـ findings؟ | يحدد شكل الـ API (return value vs. side effect) |
| هل يوجد مفهوم "خطورة"؟ | يحدد تعقيد البنية الداخلية للـ findings |

إذا أُجيب على هذه الأسئلة، يمكن تحديد الحل الأدنى واتخاذ قرار بشأن ADR.

*هذا تقرير تحقيق — لم يُتخذ قرار بعد.*  
*القرار يأتي بعد النقاش المعماري.*
