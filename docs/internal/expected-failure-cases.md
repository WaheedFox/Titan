# Expected Failure Cases — Privacy Protocol

**المرجع:** ADR-015، ADR-016، ADR-017

هذه الوثيقة تُثبّت حالات الفشل المتوقعة وقرارات التنفيذ المتعلقة بعقد الخصوصية.
الاختبارات المبنية على هذه الحالات أهم من الكود نفسه لأنها تُثبت أن العقد حقيقي.

---

## الحالات الجوهرية

### 1. المطوّر يحاول تسجيل /mydata أو /forgetme يدوياً

**السيناريو:**
```python
@bot.command("mydata")
async def my_handler(ctx): ...
```

**النتيجة المتوقعة:** `TitanError` فورية عند محاولة التسجيل — لا صمت.

**الرسالة:**
```
TitanError: Command 'mydata' is already registered
(reserved by Titan's privacy protocol — this command is part of
the user data transparency contract and cannot be overridden).
Each command can only have one handler.
```

**نفس السلوك عبر:**
- `@bot.command("mydata")`
- `@bot.command("forgetme")`
- `bot.include(router_with_mydata)`
- `@router.command("mydata")` ثم `bot.include(router)`

**السبب:** `_command_sources` يُسجَّل في `__init__()` قبل أي تسجيل من المطوّر.

---

### 2. Module يُعلن User Data لكن ينقصه erase() أو أي حقل آخر

**السيناريو:**
```python
class BadModule:
    component_name = "preferences"
    data_description = "User preferences"
    # erase() غائبة
    async def data_for(self, user_id): return {}

bot.declare_user_data(BadModule())
```

**النتيجة المتوقعة:** `TitanError` فورية عند التسجيل — لا تسجيل صامت.

**الرسالة:**
```
TitanError: UserDataModule registration failed for 'BadModule':
missing erase() (async method). Every module that holds User Data
must declare component_name, data_description, data_for(), and erase().
```

**السبب:** `UserDataRegistry._validate()` تفحص وجود كل الحقول قبل التسجيل.

---

### 3. Hook تحاول تعديل تقرير /mydata — تجميد عميق

**القرار المُتخَّذ:** التجميد عميق recursive، يشمل كل المستويات.

**السيناريو:**
```python
@bot.on_mydata_format
async def format_report(ctx, report):
    del report["pending_asks"]              # TypeError — مستوى أول
    report["ask"]["questions"].append("x")  # TypeError — مستوى ثانٍ (tuple)
    report["ask"]["questions"][0] = "y"    # TypeError — مستوى ثانٍ (tuple)
    return str(report)
```

**النتيجة المتوقعة:** `TypeError` من Python مباشرةً على أي مستوى.

**آلية التجميد:**
```
dict  → MappingProxyType  (لا إضافة/حذف/تعديل مفاتيح)
list  → tuple             (لا إضافة/حذف/تعديل عناصر)
```

مثال على التحويل:
```python
# ما يُعيده data_for():
{"questions": ["ما اسمك؟"]}

# ما يصل إلى الـ hook:
MappingProxyType({"questions": ("ما اسمك؟",)})
```

**السبب:** `MappingProxyType` وحده تجميد سطحي — قيمة `list` داخلية قابلة للتعديل.
`_deep_freeze()` في `handler.py` يُحوّل recursively كل dict وlist.

---

### 4. /forgetme يعمل — كل registered modules تستلم erase حتى عند فشل واحدة

**القرار المُتخَّذ:** erase_user() يُكمل على كل modules — لا يتوقف عند فشل.

**السيناريو:**
```python
class FailingModule:
    component_name = "failing"
    data_description = "يفشل دائماً"
    async def data_for(self, user_id): return {"count": 0}
    async def erase(self, user_id): raise RuntimeError("DB connection lost")

class GoodModule:
    component_name = "good"
    data_description = "يعمل"
    def __init__(self): self.erased = []
    async def data_for(self, user_id): return {"count": 1}
    async def erase(self, user_id): self.erased.append(user_id)

bot.declare_user_data(FailingModule())
bot.declare_user_data(good := GoodModule())

await bot.erase_user(123)
```

**النتيجة المتوقعة:**
- `good.erased` يحتوي `123` — المحو نجح
- يُرفع `TitanError` بعد اكتمال الجميع تذكر أسماء الـ modules الفاشلة
- لا module تُوقف module أخرى

**الرسالة:**
```
TitanError: erase_user() completed with errors in 'failing'.
All other modules were erased successfully.
Details: failing: RuntimeError(DB connection lost)
```

---

### 5. Module يُسجَّل — يظهر في /mydata تلقائياً

**السيناريو:**
```python
class PrefsModule:
    component_name = "preferences"
    data_description = "User preferences"
    async def data_for(self, user_id): return {"count": 3}
    async def erase(self, user_id): pass

bot.declare_user_data(PrefsModule())
# المستخدم يُرسل /mydata
```

**النتيجة المتوقعة:** التقرير يحتوي قسم "preferences" تلقائياً — لا تعديل في الـ handler.

---

### 6. AskManager يدوياً بدون تسجيل → تحذير واضح

**القرار المُتخَّذ:** تحذير `UserWarning` في وقت التشغيل — لا صمت.

**السيناريو:**
```python
ask = AskManager()
bot.middleware(ask.as_middleware())  # ← تحذير
```

**النتيجة المتوقعة:** `UserWarning` يصف المشكلة والحل.

**الرسالة:**
```
UserWarning: AskManager.as_middleware() called directly on an unregistered instance.
Pending asks will NOT appear in /mydata and will NOT be erased by /forgetme.
Use bot.enable_ask() to ensure full privacy compliance,
or call bot.declare_user_data(ask) before bot.middleware(ask.as_middleware()).
```

**المسار الصحيح بدون تحذير:**
```python
# المسار الرسمي:
ask = bot.enable_ask()

# المسار اليدوي مع امتثال كامل:
ask = AskManager()
bot.declare_user_data(ask)           # يُسجِّل ويُعيِّن الـ flag
bot.middleware(ask.as_middleware())  # لا تحذير
```

---

## حالات سلوك مؤجَّل

### أ — Module يُسجَّل مرتين

**السيناريو:**
```python
module = MyModule()
bot.declare_user_data(module)
bot.declare_user_data(module)  # مرة ثانية
```

**السلوك الحالي:** يُسجَّل مرتين — يظهر في التقرير مرتين.
**القرار:** الحماية من التكرار غير مطلوبة في v1.

### ب — enable_ask() يُستدعى مرتين

**السيناريو:**
```python
ask1 = bot.enable_ask()
ask2 = bot.enable_ask()
```

**السلوك الحالي:** ينشئ AskManager مستقلَّين — كلاهما في Registry.
**القرار:** الحماية من الاستدعاء المتكرر تُضاف عند الحاجة.
