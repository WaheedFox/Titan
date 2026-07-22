# Investigation — Runtime Contract Validator (Feature #4)

**الإصدار:** 1  
**الحالة:** تحت المراجعة

---

## المشكلة

Titan يتحقق من **التعارضات** (أمر مكرر، callback مكرر، router مُضمَّن مرتين) عند التسجيل، لكنه لا يتحقق من أن المُسجَّل نفسه صالح كعقد مع الـ framework.

إذا سجَّل المطور دالة `sync` بدلاً من `async`:

```python
@bot.command("start")
def start(ctx):          # ← ليست async
    pass
```

أو دالة بتوقيع خاطئ في middleware:

```python
@bot.middleware
async def guard(ctx):    # ← ينقصها next
    pass
```

أو error handler بتوقيع مختلف:

```python
@bot.error_handler
async def on_error(ctx): # ← ينقصها exc
    pass
```

**في كل الحالات السابقة:** Titan يقبل التسجيل بصمت، ثم عند وصول update يفشل بـ `TypeError` أو `RuntimeWarning` غامض لا يشير للمصدر الحقيقي للمشكلة.

---

## الحالة الراهنة في الكود

### ما هو موجود بالفعل

| نقطة التحقق | الآلية | المكان |
|---|---|---|
| تعارض أسماء الأوامر | `TitanError` عند التسجيل | `bot.command()`, `bot.include()` |
| تعارض callback data | `TitanError` عند التسجيل | `bot.callback()`, `bot.include()` |
| تضمين router مكرر | `TitanError` عند التسجيل | `bot.include()` |
| أمر `/link` محجوز | `TitanError` عند التسجيل | `bot.command()`, `bot.include()` |
| `ctx.edit()` خارج callback | `TitanError` عند الاستدعاء | `ctx.edit()` |
| `ctx.answer_callback()` خارج callback | `TitanError` عند الاستدعاء | `ctx.answer_callback()` |
| بوت بدون handlers | `HealthFinding(ERROR)` | `health/checks.py` |

### ما هو غائب

| العقد المنتهَك | ما يحدث حالياً |
|---|---|
| handler غير async | `RuntimeWarning: coroutine was never awaited` أو تجاهل صامت |
| middleware بدون `next` | `TypeError: guard() takes 1 positional argument but 2 were given` عند runtime |
| error handler بدون `exc` | `TypeError` عند runtime عند أول استثناء |
| handler لا يُعيد coroutine | `TypeError: object NoneType can't be used in await expression` |

كل هذه الأخطاء تصل للمطور في شكل stack trace من داخل Titan لا من كوده — وهو مكان يصعب ربطه بسطر التسجيل الخاطئ.

---

## الأنواع الثلاثة من العقود

### النوع 1 — عقد الـ Handler

```python
# الصحيح
async def handler(ctx: Context) -> None: ...

# الخاطئ
def handler(ctx): ...         # sync
async def handler(): ...      # لا ctx
async def handler(x, y): ... # توقيع خاطئ
```

يُسجَّل عبر: `@bot.command()`, `@bot.on()`, `@bot.callback()`, `@router.command()`, `@router.on()`, `@router.callback()`

### النوع 2 — عقد الـ Middleware

```python
# الصحيح
async def mw(ctx: Context, next: Callable) -> None: ...

# الخاطئ
async def mw(ctx): ...           # ينقصها next
def mw(ctx, next): ...           # sync
```

يُسجَّل عبر: `@bot.middleware`

### النوع 3 — عقد الـ Error Handler

```python
# الصحيح
async def on_error(ctx: Context, exc: Exception) -> None: ...

# الخاطئ
async def on_error(ctx): ...     # ينقصها exc
def on_error(ctx, exc): ...      # sync
```

يُسجَّل عبر: `@bot.error_handler`

---

## المعلومات المتاحة عند التسجيل

في Python يمكن فحص الدالة عند تسجيلها بـ:

```python
import inspect

inspect.iscoroutinefunction(func)   # هل هي async؟
inspect.signature(func).parameters # كم parameter تأخذ؟
```

كلا الفحصين متاحان في وقت التسجيل (قبل أي update) — لا نحتاج تشغيل الدالة.

### حالات خاصة تستحق التفكير

- **`functools.partial`:** ليست coroutine function مباشرةً — `inspect.iscoroutinefunction` قد تُعيد False.
- **`__call__` في class:** object قابل للاستدعاء لكن ليس `iscoroutinefunction`. هل ندعمه؟
- **decorators داخلية:** decorator مثل `@functools.wraps` يحافظ على المعلومات عادةً. decorator مخصص قد لا يفعل.

---

## خيارات التصميم

### خيار A — صارم: TitanError عند التسجيل
إذا لم يكن async أو التوقيع خاطئ → يُرفَض التسجيل فوراً.

```
مزايا: لا يصل خطأ للـ runtime أبداً. المطور يعرف فوراً.
عيوب: قد يمنع أنماطاً مشروعة (callable objects).
```

### خيار B — تحذير: Warning عند التسجيل
يُسجَّل warning إذا رُصد عقد مخالف، لكن التسجيل يكتمل.

```
مزايا: لا يكسر كود قائم. يُنبّه دون إيقاف.
عيوب: قد يُتجاهَل. التحذير يأتي عند بدء التشغيل قبل أي update.
```

### خيار C — هجين: صارم للـ async، متسامح للتوقيع
- `sync function` → `TitanError` فوري (خطأ واضح، لا استثناء صحيح)
- عدد parameters خاطئ → `HealthFinding(WARNING)` في `bot.health()`

```
مزايا: يُعالج الحالة الأكثر شيوعاً (نسيان async) بصرامة،
       ويترك التوقيع لـ health check حيث المطور يرى السياق.
عيوب: سلوك غير متسق بين نوعي الانتهاك.
```

---

## التوافق مع الحالة الراهنة

Titan لا يملك حالياً أي فحص للـ callables المُسجَّلة — أي خيار هو إضافة صافية بدون كسر API.

الإضافة المقترحة تقع في نقاط التسجيل الحالية:
- `bot.command()` / `router.command()`
- `bot.on()` / `router.on()`
- `bot.callback()` / `router.callback()`
- `bot.middleware()`
- `bot.error_handler()`

---

## الأسئلة المفتوحة للمناقشة المعمارية

1. **الصرامة:** TitanError أم Warning أم HealthFinding؟ أم هجين حسب نوع الانتهاك؟
2. **التوقيع:** هل نتحقق من عدد الـ parameters أم الـ async فقط؟
3. **Callable objects:** هل ندعم `class-based handlers` بـ `__call__`؟ أم نقصر على `coroutinefunction`؟
4. **الموقع في الكود:** دالة `validate_handler()` مشتركة في ملف منفصل، أم منطق inline في كل نقطة تسجيل؟
5. **Router مقابل Bot:** هل يتحقق `Router` بنفس المستوى أم يكتفي بـ `Bot` عند `include()`؟
