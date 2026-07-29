# تحقيق — Silent Failures في Titan

**الحالة:** مُنفَّذ — القرارات اتُّخذت ونُفِّذت (انظر `CHANGELOG.md` تحت "Silent failures cleanup")

**القرارات النهائية:**
- SF-01: Fail Fast في `AliasMap.register()` (الخيار أ) — منفَّذ.
- SF-02: تحذير runtime في `MiddlewareChain.run()` عند إرجاع middleware لقيمة غير `None` (الخيار ب) — منفَّذ. لا استثناء يُرفع، تدفق التنفيذ يبقى محكوماً بـ `next()` فقط.
- SF-03: لا تغيير على قابلية الكتابة لـ `bot.commands`/`bot.handlers` الآن — توثيق فقط في CONTRACT §1 أن التعديل المباشر غير مدعوم وسلوكه غير معرَّف.
- SF-04: لا تغيير — موثق في ADR-004.
- SF-05: لا تغيير — best-effort مقصود.
- SF-06: استبدال `except: pass` في `get_me()` عند startup بتحذير — البدء يستمر بعد التحذير.

**الهدف:** تحديد كل السلوكيات الصامتة الموجودة فعلاً، تشخيص سببها، وتقديم البدائل المعمارية
قبل اتخاذ أي قرار بالمعالجة.

**لا تنفيذ في هذه المرحلة.** التحقيق يُوثّق ويُحلّل فقط.

---

## ملخص

| # | الموقع | نوع الصمت | التصنيف |
|---|---|---|---|
| SF-01 | `AliasMap.apply()` | alias يكتب ctx attribute موجودة دون تحذير | **Bug / فجوة غير مقصودة** |
| SF-02 | `MiddlewareChain.run()` | return value من middleware لا يُكشف | **مخالفة CONTRACT غير مُنفَّذة** |
| SF-03 | `bot.commands` / `bot.handlers` | قابلة للكتابة مباشرة دون حماية | **فجوة معمارية** |
| SF-04 | `ctx.reply()` وأخواتها | `chat_id is None` → warning + `return None` | **قرار تصميم موثق (ADR-004)** |
| SF-05 | `ctx._register_identity()` | exception في تسجيل الهوية يُبتلع | **قرار تصميم موثق (best-effort)** |
| SF-06 | `bot.run_async()` startup | `get_me()` failure تُبتلع بصمت تام | **فجوة محتملة — لا توثيق** |

---

## SF-01 — Alias يكتب ctx attribute موجودة بصمت

### الكود

```python
# src/titan/extras/alias.py

def register(self, alias: str, target: str) -> None:
    if not hasattr(Context, target):       # ✅ يتحقق: هل target موجود في Context؟
        raise TitanError(...)
    self._map[alias] = target              # ❌ لا يتحقق: هل alias يتعارض مع attribute موجودة؟

def apply(self, ctx: Context) -> None:
    for alias, target in self._map.items():
        setattr(ctx, alias, getattr(ctx, target))  # ❌ setattr دون أي فحص للتعارض
```

### السلوك الفعلي

```python
aliases = AliasMap()
aliases.register("text", "reply")   # لا خطأ هنا — "text" ليست method في Context class
bot.middleware(aliases.as_middleware())

@bot.command("start")
async def start(ctx):
    await ctx.text("مرحباً!")   # ← يعمل (= ctx.reply)
    msg = ctx.text              # ← property أصبحت method — سلوك مختلف كلياً
```

`ctx.text` property (نص الرسالة) تُستبدل بـ `ctx.reply` method على كل update يمر بالـ middleware.
المطور الذي يستخدم `ctx.text` في نفس handler يحصل على coroutine function بدلاً من string — صمت تام.

### سبب الوجود

`register()` صُمّم ليتحقق أن `target` موجود في `Context` (منع الأخطاء المطبعية).
لم يُصمَّم ليتحقق أن `alias` لا يتعارض مع attribute موجودة — الفجوة غير مقصودة.

### التصنيف

**Bug / فجوة غير مقصودة.** CONTRACT §9: *"الأسماء الأصلية في ctx تبقى ثابتة بدون أي تغيير"* —
لكن attributes الـ ctx instance (مثل `ctx.text`) ليست محمية، فقط Class attributes.

### البدائل المعمارية

**أ. Fail Fast عند `register()`:** فحص إضافي:
```python
if hasattr(Context, alias):
    raise TitanError(f"'{alias}' is an existing ctx attribute — choose a different alias name.")
```
✅ مبكر وصريح. ⚠️ يمنع aliases على instance-level attrs فقط، لا dynamic attrs.

**ب. Fail Fast عند `apply()`:** فحص عند كل update:
```python
if hasattr(ctx, alias) and alias not in self._map:
    raise TitanError(f"Alias '{alias}' conflicts with existing ctx attribute.")
```
✅ يصطاد التعارضات الديناميكية. ⚠️ overhead لكل update.

**ج. تحذير بدلاً من exception:** `_log.warning(...)` في `register()` أو `apply()`.
✅ لا كسر API. ⚠️ قد يُتجاهل.

**د. توثيق وتثبيت:** لا تغيير في الكود — إضافة تحذير صريح في docstring.
✅ صفر تأثير على existing code. ⚠️ المطور لا يزال يستطيع الوقوع في الفخ.

### تأثير الإصلاح على CONTRACT.md

الخيار (أ) يُعدّل سلوك `AliasMap.register()` — breaking change لمن يستخدم alias names
تتعارض مع ctx attributes. يستلزم تحديث CONTRACT §9 (AliasMap rules).

---

## SF-02 — Middleware return value مُتجاهلة دون كشف

### الكود

```python
# src/titan/middleware.py

async def run(self, ctx: Context, handler: ...) -> None:
    async def build(index: int) -> None:
        if index >= len(self._chain):
            await handler()
            return

        async def next_fn() -> None:
            await build(index + 1)

        await self._chain[index](ctx, next_fn)   # ← return value مُتجاهلة تماماً

    await build(0)
```

### السلوك الفعلي

```python
@bot.middleware
async def guard(ctx, next):
    if not authorized(ctx):
        return True    # ❌ المطور يظن هذا يوقف الـ chain مثل Express.js

    await next()       # ← هذا يوقف الـ chain فعلاً — لا return value
```

`return True` تُتجاهل — الـ chain يتوقف فقط لأن `next()` لم يُستدعَ.
النتيجة: `return True` و `return` يُنتجان **نفس السلوك تماماً**.
لكن المطور القادم من Express/Koa يتوقع أن القيمة المُرجعة لها معنى — لا تحذير.

### سبب الوجود

CONTRACT §10 يُعلن صراحةً: *"Any returned value from middleware is ignored and considered invalid usage."*
هذا قرار تصميم مقصود — middleware في Titan يتحكم في الـ flow عبر `next()` فقط.
لكن الإعلان في CONTRACT لا يُرافقه كشف في runtime.

### التصنيف

**مخالفة CONTRACT غير مُنفَّذة.** القرار موثّق، التنفيذ غائب.
أقرب لـ "soft enforcement gap" منه لـ bug.

### البدائل المعمارية

**أ. `validate_middleware()` تكشف coroutines ذات return annotation:**
```python
# في titan/validation.py — تفحص هل fn ترجع شيئاً غير None
import inspect
hints = typing.get_type_hints(fn)
if hints.get("return") not in (None, type(None), inspect.Parameter.empty):
    raise TitanError("Middleware must not return a value.")
```
✅ مبكر (import time). ⚠️ يصطاد return annotation فقط، لا runtime values.

**ب. كشف runtime بـ `inspect.iscoroutine()`:**
```python
result = await self._chain[index](ctx, next_fn)
if result is not None:
    _log.warning("Middleware returned a non-None value — return values are ignored. ...")
```
✅ يصطاد كل حالة. ⚠️ يُنفَّذ لكل update لكل middleware — overhead.

**ج. توثيق صريح في `validate_middleware()` docstring + CONTRACT — لا تغيير:**
✅ صفر overhead. ⚠️ لا تغذية راجعة للمطور.

### تأثير الإصلاح على CONTRACT.md

الخيار (أ) يضيف قيداً جديداً على return type annotation — قد يكسر middleware موجودة.
الخيار (ب) لا يكسر أي API — يُضيف تحذير runtime. لا تعديل لـ CONTRACT.

---

## SF-03 — bot.commands / bot.handlers / bot.callback_handlers قابلة للكتابة

### الكود

```python
# src/titan/bot.py

def __init__(self, token: str) -> None:
    ...
    self.commands: dict[str, Handler] = {}           # plain instance attribute
    self.handlers: dict[str, list[Handler]] = {}     # plain instance attribute
    self.callback_handlers: dict[str, Handler] = {}  # plain instance attribute
```

### السلوك الفعلي

```python
@bot.command("start")
async def start(ctx): ...

bot.commands = {}   # ← يُعيد الـ dict كاملاً بصمت — /start يختفي
bot.handlers = None # ← يكسر routing الداخلي — bot.run() لاحقاً: AttributeError أو KeyError

# أو بشكل أدق — خطأ شائع:
bot.commands["help"] = my_func  # ← يتجاوز validation/duplicate checks تماماً
```

الكتابة المباشرة تتجاوز:
- فحص التكرار (`TitanError` على duplicate command)
- تسجيل `_command_sources` (المستخدم في رسائل conflict)
- lint/health checks (لا تعلم بالتعديل)

### سبب الوجود

هذه attributes كانت public منذ البداية — قراءتها ضرورية لـ `inspect()` و`health()` و`lint()`.
الحماية من الكتابة لم تُضَف عمداً أو بإهمال — غير محدد.

### التصنيف

**فجوة معمارية.** ليست bug بالمعنى الدقيق — لا يوجد نص في CONTRACT يمنع الكتابة المباشرة.
لكنها تخالف روح Contract Validator (ADR-009): *"التحقق يحدث في أقرب نقطة تسجيل"*.
الكتابة المباشرة تتجاوز نقطة التسجيل كلياً.

### البدائل المعمارية

**أ. `@property` مع getter فقط:**
```python
@property
def commands(self) -> dict[str, Handler]:
    return self._commands

@commands.setter
def commands(self, value) -> None:
    raise TitanError("bot.commands is read-only. Use @bot.command() to register handlers.")
```
✅ يمنع الكتابة المباشرة. ⚠️ كسر لمن يقرأ `bot.commands` ويعدّل القاموس مباشرةً
(مثل `bot.commands["x"] = f` — الـ setter لا يصطاده، الـ getter يُعيد reference للـ dict الداخلي).

**ب. إعادة نوع read-only من getter:**
```python
@property
def commands(self) -> types.MappingProxyType:
    return types.MappingProxyType(self._commands)
```
✅ يمنع `bot.commands["x"] = f` و `bot.commands = {}` معاً.
⚠️ breaking change — كل من يُقارن `bot.commands` بـ dict سيتأثر.

**ج. `__setattr__` guard:**
```python
def __setattr__(self, name, value):
    if name in ("commands", "handlers", "callback_handlers") and hasattr(self, name):
        raise TitanError(f"bot.{name} is read-only after initialization.")
    super().__setattr__(name, value)
```
✅ يمنع إعادة التعيين الكاملة. ⚠️ لا يمنع تعديل القاموس من الداخل.

**د. توثيق فقط — public بوعي:**
CONTRACT يُصرّح: *"تعديل bot.commands مباشرةً غير مدعوم — سلوكه غير معرَّف."*
✅ صفر تغيير. ⚠️ لا تغذية راجعة.

### تأثير الإصلاح على CONTRACT.md

الخيار (ب) breaking change لـ code يعتمد على نوع `dict`. يستلزم تحديث §1 أو إضافة قسم للـ public attributes.
الخيارات (أ/ج) breaking change جزئي. الخيار (د) لا يتطلب تعديلاً.

---

## SF-04 — ctx methods تُعيد None مع تحذير عند chat_id غائب

### الكود

```python
# src/titan/ctx.py — reply(), send(), delete_message(), ban_user(), leave()

chat_id = self.chat_id
if chat_id is None:
    _log.warning("ctx.reply() called with no chat_id in this update — message not sent.")
    return None
```

### التصنيف

**قرار تصميم موثق — ADR-004 "Soft Contract".**

ADR-004 يُصنّف هذا كـ "Soft Contract": مستحيل حالياً (update بدون chat_id نادر جداً)
لكن قد يصبح صحيحاً في حالات مستقبلية — warning مناسب.
CONTRACT §4 يُقرّ بهذا التصنيف.

### ملاحظة

التحذير موجود لكنه يعتمد على أن المطور قد هيَّأ logging.
إذا لم يُهيَّأ `logging.basicConfig()`، التحذير يختفي بصمت.

**هذا ليس bug في Titan** — إنه سلوك logging standard في Python.
لكنه يعني أن "Soft Contract" قد يصبح "Silent Contract" في بيئات بدون logging.

---

## SF-05 — `_register_identity()` exception مُبتلعة

### الكود

```python
# src/titan/ctx.py

try:
    await self._links.register_sent_message(...)
except Exception as exc:
    _log.warning("Message Links: identity registration failed for ...: %s", exc)
```

### التصنيف

**قرار تصميم موثق — best-effort.**

Docstring يُصرّح: *"الفشل غير مميت — الرسالة وصلت، الهوية تُسجَّل best-effort."*
هذا صحيح معمارياً: فشل تسجيل الهوية لا يجب أن يُفشل إرسال الرسالة.

**لا تغيير مطلوب هنا.**

---

## SF-06 — bot startup: get_me() failure مُبتلعة بصمت تام

### الكود

```python
# src/titan/bot.py — run_async()

try:
    me = await self._api.get_me()
    username = me.get("username", "unknown")
    self._log(f"Running as @{username}")
except Exception:
    pass    # ← لا warning، لا log، لا شيء
```

### السلوك الفعلي

إذا فشل `get_me()` (token خاطئ، مشكلة شبكة، timeout):
- البوت يُكمل التشغيل
- لا رسالة في logs
- `_api._me` يبقى `None` → `_register_identity()` تنبّه لاحقاً لكل رسالة مُرسلة
- الـ polling يبدأ — وإذا كان الفشل بسبب token خاطئ سيفشل عند أول `get_updates()`

المطور يرى: ـ لا شيء عند الـ startup، ثم أخطاء Telegram عند أول update.

### سبب الوجود

يبدو أن القصد: "لا تمنع البدء إذا فشل get_me() — قد يكون مؤقتاً."
لكن الصمت التام يجعل تشخيص المشكلة صعباً.

### التصنيف

**فجوة غير موثقة.** السلوك ليس intentional silent كـ SF-04/SF-05، ولا مُعلناً كـ design decision.
أقرب لـ oversight.

### البدائل المعمارية

**أ. تسجيل تحذير بدلاً من الصمت:**
```python
except Exception as exc:
    _log.warning("Could not fetch bot info at startup: %s — continuing.", exc)
```
✅ أقل صمتاً، لا يمنع البدء. ⚠️ قد يُقلق المطور دون داعٍ في حالات timeout عابرة.

**ب. Fail Fast — رفع exception:**
```python
except Exception as exc:
    raise TitanError(f"Failed to connect to Telegram at startup: {exc}") from exc
```
✅ واضح جداً. ⚠️ كسر لمن يتوقع أن البوت يبدأ دائماً ثم يُعيد المحاولة.

**ج. إبقاء الوضع مع توثيق:**
CONTRACT أو ROADMAP يُصرّح: get_me() فشله عند البدء لا يوقف الـ startup — silent by design.
✅ صفر تغيير. ⚠️ لا تغذية للمطور.

---

## ملخص المسارات المقترحة

| # | التوصية | الجهد | تأثير CONTRACT |
|---|---|---|---|
| **SF-01** | Fail Fast في `register()` — فحص تعارض alias مع ctx Class attributes | صغير | تحديث §9 |
| **SF-02** | Warning runtime إذا middleware أعادت `is not None` | صغير | لا تعديل |
| **SF-03** | قرار واعٍ أولاً: public-by-design أم تحمية؟ | متوسط–كبير | تعديل §1 |
| **SF-04** | لا تغيير — موثق في ADR-004 | — | — |
| **SF-05** | لا تغيير — موثق best-effort | — | — |
| **SF-06** | على الأقل: تسجيل warning بدلاً من pass | صغير جداً | لا تعديل |

---

## أسئلة مفتوحة للقرار

**SF-01:** هل يجب أن يفشل `AliasMap.register("text", "reply")` في class-level فقط، أم أي attribute موجودة على ctx instances أيضاً؟

**SF-02:** هل يكفي الـ CONTRACT كـ "documentation enforcement"، أم يجب إضافة runtime guard؟ وإذا أُضيف: في `validate_middleware()` (import time) أم في `MiddlewareChain.run()` (runtime لكل update)؟

**SF-03:** هل `bot.commands` يُقرأ من الخارج فعلاً في مشاريع حقيقية؟ إذا نعم — `MappingProxyType` breaking change حقيقي. إذا لا — الحماية آمنة.

**SF-06:** هل الـ startup يجب أن يكون "try everything first, start if token valid"، أم "start and fail later"؟
