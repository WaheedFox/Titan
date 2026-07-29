# 017 — الأوامر المحجوزة `/mydata` و`/forgetme`

**Status:** Accepted

**يعتمد على:** ADR-015 — Data Lifecycle Responsibility
**يعتمد على:** ADR-016 — User Data Registry و`erase_user` Architecture

---

## Proposal

جعل `/mydata` و`/forgetme` أوامر محجوزة في كل بوت Titan — مثل `/link`
تماماً — بحيث لا يستطيع المطوّر تعطيلها أو استبدالها عبر API العامة.

---

## Investigation

راجع: [`docs/internal/investigations/user-privacy-erasure.md`](../internal/investigations/user-privacy-erasure.md)

**الجذر:**

إذا كان كل مطوّر يُسمَّى أوامر الخصوصية كما يشاء أو يُطبّقها كيف
يريد — فلا يوجد عقد موحد يعرفه المستخدم النهائي. مستخدم بوت A يجد
`/myinfo`، مستخدم بوت B لا يجد شيئاً، مستخدم بوت C يجد `/mydata` لكنه
يعرض بيانات جزئية.

Titan قرّرت في ADR-015 أنها مسؤولة عن User Data التي تُنشئها. هذه
المسؤولية لا معنى لها إذا كان ظهور الشفافية والمحو خياراً للمطوّر.

**الموازنة مع /link:**

ADR-008 أنشأ `/link` كأمر محجوز. المبدأ نفسه: Titan تمتلك سلوكاً
كافياً لتبرير الحجز. `/link` تعمل على كل بوت Titan — `/mydata`
و`/forgetme` يجب أن يعملا على كل بوت Titan.

---

## Decision

### ١. الأمران محجوزان — لا override، لا disable، لا صمت

```python
# يُرفع TitanError عند التسجيل — في مرحلة التهيئة
@bot.command("mydata")    # ← TitanError
async def my_handler(ctx): ...

@bot.command("forgetme")  # ← TitanError
async def my_handler(ctx): ...

# نفس الخطأ عبر bot.include() — التعارض يُكتشف مهما كان المصدر
bot.include(router_with_mydata_command)   # ← TitanError
```

الخطأ ليس صامتاً ولا مبهماً. الرسالة تُسمّي الأمر المحجوز وسببه:

```
TitanError: Command 'mydata' is already registered
(reserved by Titan's privacy protocol — this command is part
of the user data transparency contract and cannot be overridden).
Each command can only have one handler.
```

المصدر مسجَّل في `_command_sources` منذ `__init__()` — قبل أي
تسجيل من المطوّر. المحاولة من أي مسار (`@bot.command`, `bot.include`,
`@router.command`) تصطدم بنفس الحاجز.

هذا السلوك مُثبَّت في الكود، لا في الوثيقة فقط.

### ٢. سلوك `/mydata` — شفافية كاملة real-time

عند استخدام المستخدم `/mydata`:

1. Titan تستدعي `data_held_for(user_id)` على كل module مُسجَّل (ADR-016)
2. تجمع المخرجات في تقرير واحد
3. ترسله للمستخدم

```
معلوماتك المحفوظة في هذا البوت:

انتظار رد: 1 تفاعل معلّق
تفضيلات: 3 إعدادات
```

**ما يضمنه Titan:**
- كل User Data مُسجَّلة تظهر — لا شيء مخفي داخل النظام
- التقرير real-time — يعكس الحالة الفعلية لحظة الاستدعاء
- أي module جديد يُسجَّل يظهر تلقائياً دون تعديل في الـ handler

**ما لا يضمنه Titan:**
- لغة العرض (الإنجليزية افتراضية — الترجمة مسؤولية المطوّر)
- تنسيق الرسالة النهائي (Titan تُرسل نصاً — المطوّر يستطيع التخصيص عبر hook اختياري)
- بيانات المطوّر خارج نظام Titan

### ٣. سلوك `/forgetme` — محو كامل بعقد

عند استخدام المستخدم `/forgetme`:

1. Titan تستدعي `erase_user(user_id)` — تحذف كل User Data مُسجَّلة
2. الحذف حقيقي — لا flags، لا soft delete
3. بعد نجاح المحو، تُرسل تأكيداً للمستخدم
4. لا يمكن لأي module استعادة تلك البيانات عبر Titan

**ما يشمله `/forgetme`:**
- كل User Data مُسجَّلة في نظام ADR-016
- الحالات المعلّقة (`AskManager._pending`)
- أي module مستقبلي مُسجَّل

**ما لا يشمله `/forgetme`:**
- Permanent Resource Identity (Links) — ليست User Data (ADR-015)
- بيانات المطوّر خارج Titan — موثَّق صراحةً في رسالة التأكيد

### ٤. Titan تملك العقد — المطوّر يُضيف طبقة فوقه

الفصل الأساسي:

```
Titan تملك:       العقد — ما يُحذف، ما يُعرض، متى يعمل، من لا يُسقَط
المطوّر يستطيع:   إضافة طبقة فوق الناتج — ترجمة، تنسيق، رسالة مرافقة
المطوّر لا يستطيع: تغيير ما يدخل في التقرير، منع محو أي module مُسجَّل،
                   تعطيل الأمر، إسقاط مستخدم من العقد
```

توفر Titan hooks اختيارية — لكن كل hook **تضيف فوق السلوك، لا تستبدله**.

#### `/mydata` — التقرير للقراءة فقط

```python
@bot.on_mydata_format
async def format_report(ctx, report: MappingProxyType) -> str:
    # report: read-only — MappingProxyType أو ما يعادلها
    # المطوّر يترجم أو ينسّق، لا يُصفّي ولا يحذف مفاتيح
    return my_formatter(report)
```

`report` الذي تستلمه الـ hook هو نسخة مجمّدة (read-only) من
مخرج `data_held_for()`. لا يمكن حذف مفتاح منه ولا تعديل قيمه.

هذا مُثبَّت في الكود: الـ hook تستلم `MappingProxyType` أو نسخة
مجمّدة — لا `dict` قابلاً للتعديل. محاولة التعديل ترفع `TypeError`
من Python مباشرةً.

**الأثر:** المطوّر يتحكم في *كيف* يُعرض التقرير — لا في *ماذا* يحتوي.

#### `/forgetme` — لا pre-hook، لا إلغاء

```python
@bot.on_forgetme_complete
async def after_erasure(ctx) -> None:
    # يُستدعى بعد نجاح erase_user() فقط — لا قبله بأي حال
    # مناسب لحذف بيانات خارج Titan يديرها المطوّر
    await my_external_db.delete_user(ctx.user_id)
```

الترتيب في الكود:

```
1. Titan تستدعي erase_user(user_id)    ← لا يمكن تخطيه
2. erase_user() تكتمل بنجاح            ← لا يمكن إلغاؤه
3. on_forgetme_complete يُستدعى        ← بعد اكتمال المحو
4. تأكيد يُرسَل للمستخدم
```

**لا يوجد** `on_forgetme_before` أو `on_forgetme_condition` في API.
هذا الغياب قصد — لا سهو. API التي تسمح بإيقاف المحو تُناقض
تعريف عقد `/forgetme`.

**الأثر:** المطوّر يستطيع إضافة تنظيف خارجي *بعد* المحو — لا
التحكم في *هل* يحدث المحو.

الـ hooks اختيارية. بدونها يعمل Titan بسلوك افتراضي معقول.

### ٥. العلاقة بـ `/link`

| | `/link` | `/mydata` | `/forgetme` |
|---|---|---|---|
| محجوز | ✅ | ✅ | ✅ |
| TitanError عند التعارض | ✅ | ✅ | ✅ |
| Titan تملك السلوك | ✅ | ✅ | ✅ |
| Hook اختيارية للمطوّر | — | ✅ | ✅ |

---

## Rule

**أوامر الخصوصية الأساسية محجوزة في Titan.**

لا بوت Titan بدون `/mydata` و`/forgetme`. هذا جزء من العقد مع
المستخدم النهائي، لا خيار للمطوّر.

**Titan تملك العقد — المطوّر يُضيف، لا يُبدّل.**

الحجز يضمن وجود العقد. الـ hooks تُتيح تخصيص الشكل واللغة والأفعال
المرافقة — شريطة ألّا تُغيّر ما يدخل في التقرير ولا ما يُشمل بالمحو.
Hook تُصفّي User Data من `/mydata` ليست تخصيصاً — هي كسر للعقد.

---

## Alternatives Considered

**المطوّر يُنفّذ أوامر الخصوصية بنفسه**

يعني: Titan توفر `erase_user` و`data_held_for` كـ API، والمطوّر
يبني `/forgetme` و`/mydata` كيف يشاء.

لم يُختر لأن غياب الحجز يعني غياب الضمان. بوت Titan بدون `/forgetme`
يعني Titan تخزّن User Data بدون آلية محو معروفة للمستخدم — وهذا
ينقض ADR-015 مباشرةً.

**أوامر قابلة للتعطيل بخيار صريح**

```python
bot = Titan(token=..., privacy_commands=False)  # لا /mydata ولا /forgetme
```

لم يُختر لأن "صعوبة التجاهل" هدف معماري صريح في ADR-015. خيار
تعطيل سهل يُناقض هذا الهدف. من يريد سلوكاً مختلفاً جذرياً لا
يستخدم Titan كـ framework.

**أوامر بأسماء قابلة للتهيئة**

```python
bot = Titan(token=..., privacy_commands={"data": "/info", "erase": "/delete"})
```

لم يُختر لأن القيمة من الحجز هي الاتساق — مستخدم أي بوت Titan
يعرف `/mydata` و`/forgetme`. أسماء قابلة للتهيئة تُلغي هذا الاتساق.

---

## Consequences

**ما يُكتسب:**
- المستخدم النهائي يملك ضماناً: أي بوت Titan لديه `/mydata` و`/forgetme`.
- المطوّر لا يحتاج تذكّر بناء أوامر الخصوصية — موجودة تلقائياً.
- كل module جديد يُسجَّل يظهر تلقائياً في الأمرين — لا تعديل في الـ handlers.

**القيود المقبولة:**
- المطوّر لا يستطيع تسمية `/mydata` باسم آخر — قرار واعٍ، لا قيد تقني.
- `/forgetme` لا يشمل بيانات خارج Titan — موثَّق صراحةً للمستخدم في رسالة التأكيد.
