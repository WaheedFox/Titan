# Titan Framework Contract (v1)

هذا الملف يحدد السلوك الرسمي لمكتبة Titan.

أي تغيير في السلوك الظاهر للمطور يعتبر breaking change إلا إذا تم تحديث هذا الملف.

---

# 0. Core Philosophy — Dual Entry (Hands Model)

Titan allows multiple entrypoints for the same capability.

Each entrypoint is valid, supported, and official.

### Principle

- Multiple ways to access the same behavior are allowed.
- No difference in runtime behavior between entrypoints.
- Entrypoints differ only in usage style, not in system logic.

### Example

run() and run_async() are both valid entrypoints to the same execution engine.

- run() → synchronous convenience entrypoint
- run_async() → native async entrypoint

Both execute the same internal logic.

### Alias Consistency Rule

If multiple names exist for the same operation:

- All aliases must map to the same underlying implementation
- No alias is allowed to introduce new behavior
- No alias is allowed to bypass system rules

### Design Rule

Titan prioritizes:

- Developer choice of expression
- Consistent internal behavior
- Zero duplication of logic paths

NOT:

- Multiple implementations for the same feature
- Hidden behavioral differences between entrypoints

---

# 1. Public API

الاستيراد الرسمي المضمون في v1:

```python
from titan import Titan
from titan import Router
from titan import InlineKeyboard
from titan import TitanError
from titan import TelegramError
```

أي شيء غير مذكور هنا هو implementation detail وليس جزءاً من الـ contract.

`InlineButton` هي implementation detail داخلية تستخدمها `InlineKeyboard` لتنظيم البيانات. لا تظهر في الـ public API ولا يحتاجها المطور مباشرة.

---

# 2. Core Principle

- No hidden side effects
- Deterministic execution
- ctx هو نقطة التنفيذ الوحيدة

---

# 3. Context (ctx)

Allowed actions:
- reply()
- send()
- edit() (callback only)
- delete_message()
- ban_user()
- leave()
- answer_callback()
- refresh_permissions()

Rules:
- لا وصول مباشر لـ Telegram API
- Message / Update / Chat / Sender = data-only

### ctx.raw — Escape Hatch

- ctx.raw يكشف raw JSON الكامل القادم من Telegram
- ليس جزءاً من frozen contract — بنيته قد تتغير
- استخدمه فقط عند الحاجة لبيانات غير متاحة عبر ctx مباشرة
- لا تبني منطقاً دائماً يعتمد على ctx.raw

---

# 4. Event System

- message
- callback
- channel
- new_member
- left_member

Semantic events must not overlap with message handler.

---

# 5. Callback Routing

- @bot.callback(data) has priority
- fallback → @bot.on("callback")
- duplicate registration = TitanError

---

# 6. Long Polling

- exponential backoff:
  1s → 2s → 4s → 8s → 16s → 30s
- reset on success

---

# 7. Offset Handling

- external responsibility
- bot.run(offset=...) — synchronous entrypoint
- bot.run_async(offset=...) — async entrypoint (see §0)
- bot.offset available for persistence
- on_offset optional hook

---

# 8. Alias Layer (Optional)

- bot.alias(alias, target) تعرّف اسمًا بديلاً لـ method موجودة في Context
- المطور هو من يحدد كل alias بالكامل — لا توجد aliases جاهزة في المكتبة
- الاسم الأصلي يبقى ثابتًا ومتاحًا بدون أي تغيير
- alias لا يستبدل الاسم الأصلي ولا يعطّله
- إذا كان الاسم الهدف غير موجود في Context → TitanError
- الميزة اختيارية بالكامل — مشروع لا يستخدمها لا يتأثر بأي شكل
- لا تغيير في أي سلوك أساسي — naming layer فقط

---

# 9. Middleware System

### Core Principle
Middleware exists ONLY to control request flow before reaching handlers.

### Rules

- Middleware must be linear (no branching execution graphs)
- Middleware receives (ctx, next)
- next() is the ONLY way to continue execution
- Middleware must not return values.
- Use `await next()` to continue execution.
- Use `return` (without value) to stop execution.
- Any returned value from middleware is ignored and considered invalid usage.
- No side-effect APIs are introduced via middleware
- Middleware must NOT contain business logic that belongs to handlers

### Allowed usage

- Authentication / authorization checks
- Logging
- Rate limiting
- Request preprocessing (e.g. normalization)

### Forbidden usage

- Plugin systems
- Behavior injection into ctx
- Overriding handler routing logic
- Dynamic execution modification beyond next()

### Ban System

- bot.banned_users — public set[int], managed entirely by the developer
- ctx.is_banned — bool, set by bot before middleware runs
- ctx.is_banned is True only when ctx.user_id is in bot.banned_users
- middleware reads ctx.is_banned — it does not write to it

### Stability Rule

Any middleware feature that introduces hidden execution paths or non-linear flow is considered a breaking change.

---

# 10. Error Handling

Errors in Titan must follow these principles:

- Explain what happened
- Explain why it happened
- Provide a fix suggestion when possible
- Never change runtime behavior

---

# 11. Stability Rule

Any change is breaking if it:
- changes output for same input
- adds undocumented behavior
- changes execution order

---

# 12. Stability Principle

Titan is not designed as a feature-driven framework.

Titan is designed as a stability-driven system.

### Core Rule

The public API is considered frozen.

New features do not automatically justify API changes or additions.

### Version Philosophy

- Updates do not imply new features
- Features are added only if they preserve full backward compatibility
- Stability is prioritized over market trends or external library behavior

### Design Intent

Titan does not participate in feature race with other frameworks.

Instead, Titan focuses on:

- Consistency
- Predictability
- Long-term developer trust

---

# 13. Adapter Layer

bot.telegram provides direct access to the full Telegram Bot API.

### Architecture

- bot.telegram is a TelegramAdapter instance attached to every Titan bot
- It operates on the same session as the core (no separate connection)
- It is independent of ctx, middleware, routing, and alias

### Principle

- Adapter exists for capabilities outside the update-response cycle
- Adapter methods do not go through middleware
- Adapter does not modify core behavior

### Stability Rule

bot.telegram is a stable public entrypoint. Its presence is guaranteed. Individual method signatures follow Telegram Bot API conventions.

---

# 14. Router

### Purpose

Router is a code organization tool only. It has no runtime behavior of its own.

### API

```python
router = Router()

@router.on("message")
@router.command("start")
@router.callback("yes")

bot.include(router)
```

### Rules

- Router supports: on(), command(), callback()
- Router does NOT support: middleware(), alias(), nested include()
- bot.include(router) transfers all registrations to the bot
- Duplicate command or callback_data across router and bot → TitanError
- include() does not modify the router itself
- Multiple routers can be included into the same bot
- Each router must be included exactly once. Calling bot.include(router) twice silently doubles all on() handlers. commands and callbacks are protected by duplicate checks; on() handlers are not.

### Forbidden

- Nested routers
- Router middleware
- Priorities or groups
- Any routing tree logic
