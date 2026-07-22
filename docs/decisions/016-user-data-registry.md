# 016 — User Data Registry و`erase_user` Architecture

**Status:** Accepted

**يعتمد على:** ADR-015 — Data Lifecycle Responsibility

---

## Proposal

تصميم الآلية التي تعرف بها Titan ما هو User Data الموجود، ومن يملكه،
وكيف يُمحى — دون أن تحتاج Core إلى معرفة مباشرة بكل module.

القرار في ADR-015 جعل المحو إلزامياً. هذا القرار يحدد *كيف* يعمل.

---

## Investigation

راجع: [`docs/internal/investigations/user-privacy-erasure.md`](../internal/investigations/user-privacy-erasure.md)

**المشكلة الهندسية:**

`erase_user` يجب أن يغطي كل User Data في Titan — اليوم وكل module
يُضاف مستقبلاً. لكن Core لا تعرف ولا يجب أن تعرف بتفاصيل كل module.

إذا كتبنا في Core:

```python
async def erase_user(self, user_id: int) -> None:
    await self._ask.cancel_pending(user_id)
    # وكل module يأتي لاحقاً يُضاف هنا يدوياً؟
```

هذا يعني: Core تعرف بـ AskManager وبكل module مستقبلي. الاعتماد
في الاتجاه الخاطئ — Core يصبح مرتبطاً بكل ما فيه.

**الخيارات المدروسة موثقة في القسم التالي.**

---

## Decision

### ١. `UserDataRegistry` — المصدر الوحيد للحقيقة

`UserDataRegistry` ليس قائمة تنظيمية. هو المصدر الوحيد الذي تعود
إليه Titan لأي سؤال عن User Data:

- `/mydata` ← يسأل Registry فقط
- `/forgetme` ← يُنفّذ عبر Registry فقط
- `erase_user()` ← يُرسَل عبر Registry فقط
- أي API مستقبلية ← تمر عبر Registry

**Module يملك User Data ولا يوجد في Registry يُعدّ خطأ تصميمياً داخل
Titan — لا استثناءً قابلاً للقبول.** أي مكوّن رسمي يُضاف لاحقاً
ويخزّن User Data يدخل Registry قبل أي release.

### ٢. `UserDataModule` — هوية مُعلنة، لا dict مجهول

أي module يُطبّق `UserDataModule` Protocol يُعلن هويته الكاملة:

```python
class UserDataModule(Protocol):
    """
    عقد كل module يخزّن User Data داخل Titan.

    Module يُطبّق هذا العقد يُعلن:
        - من هو (component_name)
        - ماذا يخزّن (data_description)
        - كيف يُعرض ما يعرفه (data_for)
        - كيف يُمحى ما يعرفه (erase)

    التسجيل يجعل البيانات تظهر تلقائياً في:
        - erase_user()
        - data_held_for()
        - /mydata
        - /forgetme
    """

    @property
    def component_name(self) -> str:
        """
        اسم المكوّن — ثابت، قابل للقراءة.

        يُستخدم في تقارير /mydata كعنوان للقسم.
        مثال: "pending_asks", "user_preferences"
        """
        ...

    @property
    def data_description(self) -> str:
        """
        وصف موجز لنوع البيانات التي يديرها هذا المكوّن.

        يُعرض في /mydata بجوار البيانات.
        مثال: "Unfinished interactions waiting for user reply"
        """
        ...

    async def data_for(self, user_id: int) -> dict:
        """
        الحقيقة الداخلية: ما تعرفه Titan عن هذا المستخدم.

        المُعاد يجب أن يكون قابلاً للتسلسل (JSON-serializable).
        يُعرض في /mydata — المطوّر يُنسّق الشكل، لا يغيّر المحتوى.
        """
        ...

    async def erase(self, user_id: int) -> None:
        """
        محو حقيقي لكل User Data لهذا المستخدم.

        يجب أن يكون:
        - حذفاً حقيقياً — لا flags، لا soft delete
        - كاملاً — لا بيانات جزئية تبقى
        - نهائياً — لا إمكانية للاسترجاع عبر Titan

        Module لا يُطبّق هذا المتطلب يُرفض عند التسجيل.
        """
        ...
```

**التحقق عند التسجيل:**

`UserDataRegistry.register(module)` يتحقق في مرحلة التهيئة من أن
`module` يُعلن `component_name` و`data_description` ويُطبّق `data_for`
و`erase`. Module ناقص يرفع خطأ فورياً — لا تسجيل صامت، لا فشل في runtime.

**التسجيل:**

```python
# Modules داخل Titan — تُسجَّل تلقائياً عند تهيئة Bot
# لا فعل مطلوب من المطوّر

# Modules المطوّر — تسجيل صريح واحد
bot.declare_user_data(MyModule())
```

بعد التسجيل: `erase_user` و`data_held_for` يشملان هذا الـ module
تلقائياً — لا خطوة إضافية.

### ٢. `erase_user` — عقد عام، dispatcher داخلي

```python
# الواجهة الخارجية — ثابتة
await bot.erase_user(user_id=123456789)

# ما يحدث داخلياً — يتسع مع كل module مُسجَّل
for module in self._user_data_registry:
    await module.erase(user_id)
```

`erase_user` ليس مرتبطاً بـ AskManager أو بأي module محدد. اليوم
يُسجَّل AskManager تلقائياً فقط. غداً يُضاف Preferences — يظهر
تلقائياً بدون تغيير في `erase_user` نفسه.

### ٣. `data_held_for` — aggregator بمستويين

```python
report = await bot.data_held_for(user_id=123456789)
```

يُعيد مخرجاً يجمع من كل module مُسجَّل. كل module يُعلن عن نفسه:

```json
{
  "pending_asks": {
    "description": "Unfinished interactions waiting for user reply",
    "count": 1
  },
  "preferences": {
    "description": "User preferences stored by the bot",
    "count": 3
  }
}
```

المفاتيح وصفية بالإنجليزية — قابلة للعرض مباشرةً في `/mydata`.
اللغة والتنسيق النهائي مسؤولية المطوّر.

### ٤. First-party vs Third-party — القاعدة العامة للتسجيل

الفصل يرتكز على سؤال واحد: **هل Titan تعرف هذا الـ module بالاسم؟**

**First-party — Titan تعرفه → التسجيل تلقائي**

Module موجود داخل `titan.*` ويملك User Data. Titan تعرف بوجوده
في وقت التصميم — لا مفاجأة في runtime. المسار الصحيح لا يتطلب
فعلاً من المطوّر.

نوعان:

*ثابت* — يُنشأ دائماً في `Titan.__init__()`. التسجيل غير مشروط:

```python
# bot.py — يحدث دائماً، لا خيار
self._user_data_registry = UserDataRegistry()
# أي module ثابت يُسجَّل هنا مباشرةً
```

*اختياري* — module داخل Titan يُفعَّل بقرار من المطوّر (مثل
`AskManager`). التسجيل يحدث تلقائياً عند الربط عبر نقطة lifecycle
الرسمية — لا يحتاج `declare_user_data` منفصلاً:

```python
# عند الربط بالطريقة الرسمية → التسجيل يحدث تلقائياً
bot.enable_ask()   # ← يُنشئ AskManager ويُسجّله في Registry ويُضيف middleware
```

نقطة الربط الرسمية لكل module اختياري تُحدَّد عند تنفيذه. القاعدة
الثابتة: **الطريقة الرسمية تتضمن التسجيل — لا خطوة منفصلة.**

**Third-party — Titan لا تعرفه → الإعلان مطلوب**

Module كتبه المطوّر خارج `titan.*`. Titan لا تستطيع اكتشافه —
الإعلان الصريح مرة واحدة ضروري:

```python
bot.declare_user_data(MyPreferencesModule())
```

بعدها: `erase_user` و`data_held_for` يشملانه تلقائياً. التسجيل
يحدث مرة في مرحلة التهيئة.

**الخلاصة:**

| النوع | المثال | التسجيل |
|---|---|---|
| First-party ثابت | أي module في `Titan.__init__()` | تلقائي — دائماً |
| First-party اختياري | `AskManager` | تلقائي — عند الربط الرسمي |
| Third-party | module المطوّر | `declare_user_data()` — مرة واحدة |

**الهدف:** المسار الصحيح يجب أن يكون الأسهل. مسؤولية الخصوصية
لا تُوضَع على ذاكرة المطوّر للمكوّنات الرسمية.

### ٥. التحقق من صحة التسجيل

`bot.declare_user_data(module)` يتحقق من أن `module` يُطبّق
`UserDataModule` Protocol — رسالة خطأ واضحة إذا لم يكن كذلك.

لا تسجيل صامت لـ module ناقص.

---

## Rule

**`UserDataRegistry` هو المصدر الوحيد للحقيقة.**

أي API في Titan تتعلق بدورة حياة User Data تمر عبر Registry — لا
توجد "طريقة ثانية" أو shortcut داخلي.

**User Data في Titan لا تُخزَّن بدون عقد.**

أي module يُنشئ User Data يُطبّق `UserDataModule` ويُسجَّل في الـ
registry. لا يوجد User Data "خارج النظام" داخل Titan.

**`erase_user` عقد — لا تطبيق محدد.**

محتوياته تتحدد بما هو مُسجَّل في وقت الاستدعاء. Module جديد يُسجَّل
= `erase_user` يشمله تلقائياً.

**`UserDataModule` هوية كاملة — لا dict مجهول.**

Module بدون `component_name` و`data_description` يُرفض عند التسجيل.
التقرير الذي يُعرض في `/mydata` بعد سنة يجب أن يكون مفهوماً بلا
رجوع للكود.

---

## Alternatives Considered

**Direct Coupling — Core تعرف مباشرةً بكل module**

```python
# في Core
await self._ask.cancel_pending(user_id)
await self._prefs.delete_user(user_id)
# كل module جديد يُضاف هنا يدوياً
```

لم يُختر لأن الاعتماد في الاتجاه الخاطئ. Core يصبح مرتبطاً بكل
module — تعديل أي module يمس Core. يكسر مبدأ الاعتماد الأحادي الاتجاه.

**Event-based — Modules تستمع لحدث "erase"**

```python
@titan.on_erase
async def handle_erase(user_id: int) -> None:
    await my_module.delete(user_id)
```

لم يُختر لأن الاكتمال لا يمكن ضمانه. `erase_user` يجب أن يكون
شاملاً — إذا لم يشترك module في الحدث، بياناته لا تُحذف. هذا ثغرة
أمان في عقد المحو، وليس مجرد خطأ في التنفيذ.

**Module يُسجَّل بـ Decorator**

```python
@bot.user_data
class MyStorage:
    ...
```

لم يُختر لأن `bot` يُنشأ في runtime. Decorator يُنفَّذ عند تعريف
الكلاس — قبل وجود `bot`. يُنتج ربطاً في وقت خاطئ ويُعقّد الـ testing.

---

## Consequences

**ما يُكتسب:**
- كل User Data مُعلنة — لا يوجد تخزين "خفي" داخل Titan.
- `erase_user` شامل تلقائياً — module جديد لا يحتاج تعديل Core.
- `data_held_for` يتوسع تلقائياً مع كل module جديد.
- `/mydata` و`/forgetme` يعملان بدون تهيئة إضافية (ADR-017).

**القيود المقبولة:**
- المطوّر الذي يبني module خاص يستدعي `declare_user_data` صراحةً مرة واحدة.
  بعدها: تلقائي. قبلها: خارج النظام — بوعي.
- `erase_user` يضمن فقط ما هو مُسجَّل — التخزين خارج Titan خارج الضمان.

**يُشرِّع مباشرةً:**
- ADR-017: الأوامر المحجوزة `/mydata` و`/forgetme`
