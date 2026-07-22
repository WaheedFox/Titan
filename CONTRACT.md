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

هذا القسم يحدد سطح الاستيراد الرسمي فقط. ضمانات عامة إضافية — مثل ctx.raw وmodel.raw وmodel.to_dict() — موثَّقة في أقسامها المعنية من هذا الـ CONTRACT.

أي شيء غير موثَّق في هذا الـ CONTRACT هو implementation detail وليس جزءاً من الضمان الرسمي.

### InlineButton

`InlineButton` نوع بيانات عام (public type) يمثل زراً واحداً داخل لوحة المفاتيح.

```python
from titan import InlineButton
```

المسار المُفضَّل لإنشائه هو عبر `InlineKeyboard` builder:

```python
InlineKeyboard().row().button("نعم", callback_data="yes")
```

الإنشاء المباشر مسموح به ومدعوم — مفيد عند type annotation أو بناء لوحة مفاتيح برمجياً:

```python
btn: InlineButton = InlineButton(text="نعم", callback_data="yes")
```

كلا المسارين ينتجان نفس الكائن. لا فرق في السلوك.

---

# 2. Core Principle

- No hidden side effects
- Deterministic execution
- ctx is the only execution point within an update-response cycle. Operations outside the update-response cycle use bot.telegram (see §14).

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
- fetch_permissions() → populates ctx.permissions (ChatPermissions)

Rules:
- لا وصول مباشر لـ Telegram API
- Message / Update / Chat / Sender = data-only

### ctx.raw — Escape Hatch

- ctx.raw يكشف raw JSON الكامل القادم من Telegram على مستوى الـ update
- وجود ctx.raw مضمون وجزء من الـ contract
- ctx.raw intentionally exposes Telegram's native payload. Titan guarantees the existence of this access point, but not the structure of the payload itself, because that structure is defined by Telegram and may evolve independently of Titan.
- استخدمه فقط عند الحاجة لبيانات غير متاحة عبر ctx مباشرة
- لا تبني منطقاً دائماً يعتمد على حقول بعينها داخل ctx.raw

### model.raw — Scoped Escape Hatch

ينطبق على: Message.raw / Sender.raw / Chat.raw

- وجود .raw على كل نموذج مضمون وجزء من الـ contract
- يكشف القاموس الخام المقطوع من الـ update لذلك النموذج تحديداً
- يختلف عن ctx.raw في النطاق: ctx.message.raw يعطيك قاموس الرسالة مباشرة بغض النظر عن بنية الـ update الخارجية
- model.raw intentionally exposes Telegram's native payload scoped to that model. Titan guarantees the existence of this access point on every model, but not the structure of the payload itself, because that structure is defined by Telegram and may evolve independently of Titan.
- لا تبني منطقاً دائماً يعتمد على حقول بعينها داخل model.raw

### model.to_dict() — Serialization Contract

ينطبق على: Message.to_dict() / Sender.to_dict() / Chat.to_dict()

- وجود to_dict() على كل نموذج مضمون وجزء من الـ contract
- الغرض منها: serialization — تحويل النموذج إلى قاموس للتسجيل أو التخزين أو التكامل مع أنظمة خارجية
- تنفيذها اليوم يعكس .raw، لكن قد تتضمن في المستقبل حقولاً محسوبة تُضيفها Titan
- For fields originating from Telegram, the same principle applies: Titan guarantees the method exists, not the structure of what Telegram sends.

---

# 4. Event System

- message
- callback
- channel
- new_member
- left_member

Semantic events must not overlap with message handler.

### Unrouted Updates

Updates that Titan does not recognise as any of its supported event types are silently dropped.

- They are not passed to any handler — including `on("message")`.
- They are not treated as errors and do not invoke the error handler.
- They do not affect polling or the update offset.

This applies equally to update types that are *unsupported* (known to Telegram but not yet routed by Titan) and *unknown* (added by Telegram after this version was built).

---

# 5. Registration Rules

### Routing Key Principle

A routing key is the value Titan uses to select exactly one handler for an incoming update.

Registration types that define a routing key:
- **command name** — selects the handler for `/command` messages
- **callback_data** — selects the handler for callback_query updates

Each routing key must be unique across the entire bot instance, regardless of whether it was registered directly on the bot or via any router.

Attempting to register a second handler for an existing routing key raises `TitanError` at registration time, not at runtime.

### Internal State Rule

`bot.commands`, `bot.handlers`, `bot.callback_handlers` are internal state exposed for inspection only.

Direct assignment (`bot.commands = {}`) or direct mutation (`bot.commands["x"] = fn`) bypasses all registration validation, duplicate detection, and source tracking. This is unsupported — behavior is undefined.

Use `@bot.command()`, `@bot.on()`, `@bot.callback()`, and `bot.include(router)` as the only supported registration paths.

### Fan-Out Registration

`@bot.on(event)` does not define a routing key.

It registers a handler into a fan-out list for that event type. All registered handlers for an event are called in registration order. Multiple handlers for the same event type are expected behavior, not a conflict.

### Router Instance Integrity

Each Router instance may be passed to `bot.include()` exactly once.

Passing the same Router instance twice raises `TitanError`.

This rule is independent of routing-key uniqueness. Two distinct Router instances are not restricted relative to each other — only their routing keys must remain globally unique.

---

# 6. Callback Routing

- @bot.callback(data) has priority over @bot.on("callback")
- If no @bot.callback(data) matches the incoming callback_data, the update falls through to @bot.on("callback") if registered
- Duplicate callback_data registration is governed by §5

---

# 7. Long Polling

- exponential backoff:
  1s → 2s → 4s → 8s → 16s → 30s
- reset on success — success is defined as get_updates() returning without raising an exception, including when the result list is empty. Only an exception triggers backoff.

---

# 8. Offset Handling

- external responsibility
- bot.run(offset=...) — synchronous entrypoint
- bot.run_async(offset=...) — async entrypoint (see §0)
- bot.offset available for persistence
- bot.offset reflects the highest update_id accepted by Titan for processing, not necessarily the last update whose handler has completed. Once an update is enqueued, Titan takes responsibility for executing it — the offset advances regardless of whether the handler has run yet.

### on_offset Hook

- Signature: `Callable[[int], None]`
- Must be synchronous — not a coroutine
- Called once per update, after the update has been dispatched to its chat queue and bot.offset has been updated
- Receives the current offset value as its only argument
- Guaranteed call order per update: update dispatched → bot.offset updated → on_offset(offset)
- Note: dispatch means the update has been accepted and queued for processing; handler completion may follow asynchronously
- If no on_offset is provided, offset management is entirely the developer's responsibility via bot.offset

---

# 9. Alias Layer — titan.extras only

The alias feature is NOT part of core Titan. It is available exclusively through `TitanWithExtras` in `titan.extras`.

See §7 for the full extras contract.

Summary:
- `bot.alias(alias, target)` is a method of `TitanWithExtras`, not `Titan`
- Vanilla `Titan` instances have no `alias()` method and carry no alias machinery
- AliasMap validation, scope, and lifecycle rules apply only when using `TitanWithExtras`

### Alias Lifecycle and Scope (TitanWithExtras only)

- Validation: target is validated against the Context class at registration time, not at runtime
- Scope: aliases are applied per ctx instance — each incoming update receives a fresh ExtrasContext with all registered aliases applied
- Applies to both methods and properties on ctx
- Timing: aliases are applied after ctx is created and is_banned is set, before middleware runs
- bot.alias() may be called before or after bot.run() — it takes effect on the next update processed after the call

---

# 10. Middleware System

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

### Guaranteed Execution Order

For every incoming update, Titan guarantees this sequence:

1. Update is parsed and ctx is built
2. ctx.is_banned is set — False if no user_id, or if user_id is not in bot.banned_users
3. Middleware chain runs, wrapping the dispatch function
4. dispatch() is invoked via next() inside the middleware chain
5. The matched handler executes inside dispatch()

This order is guaranteed and externally observable. Any change to this sequence is a breaking change.

Note: When using `TitanWithExtras` (see §7), step 3 is preceded by alias application to ctx. This is an extras-layer concern and is not part of the core sequence above.

### Stability Rule

Any middleware feature that introduces hidden execution paths or non-linear flow is considered a breaking change.

---

# 11. Error Handling

Errors in Titan must follow these principles:

- Explain what happened
- Explain why it happened
- Provide a fix suggestion when possible
- Never change runtime behavior

---

# 12. Stability Rule

Any change is breaking if it:
- changes output for same input
- adds undocumented behavior
- changes execution order

---

# 13. Stability Principle

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

# 14. Adapter Layer

bot.telegram provides access to Telegram Bot API operations outside the update-response cycle, as selected by Titan.

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

# 15. Router

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
- include() does not modify the router itself
- Multiple routers can be included into the same bot
- Duplicate detection and instance integrity rules are governed by §5

### Forbidden

- Nested routers
- Router middleware
- Priorities or groups
- Any routing tree logic

---

# 7. titan.extras — Opt-in DX Layer

`titan.extras` provides optional developer-experience utilities that are NOT part of the core contract.
Importing `titan` alone carries zero extras machinery — no state, no hooks, no interception.

```python
from titan.extras import AliasMap, AskManager
```

## Design boundary

| Core (`titan.Titan` + `titan.ctx.Context`) | Extras (`titan.extras`) |
|---|---|
| routing, middleware, handler lifecycle | AliasMap, AskManager |
| deterministic execution engine | opt-in utilities wired via middleware |
| zero extras state | state lives in the utility object, not the bot |

Extras integrate exclusively through the standard middleware system.
No subclassing, no hooks, no lifecycle changes.

## AliasMap

Provides method shortcuts on `ctx`. Wired via middleware using the same pattern as `AskManager`.

```python
from titan.extras import AliasMap

aliases = AliasMap()
aliases.register("say", "reply")
bot.middleware(aliases.as_middleware())
```

Rules:
- `alias` must not conflict with an existing attribute of `Context` — otherwise `TitanError` at registration time
- `target` must be an existing attribute of `Context` — otherwise `TitanError` at registration time
- The original method name is never changed or removed
- Aliases are applied per-request; `ctx` instances outside this middleware are unaffected
- Without `as_middleware()` registration, no alias is ever applied
- Dynamic instance attributes set at runtime are not checked — developer responsibility

## AskManager

Sends a question and awaits the next text reply from the same `(chat_id, user_id)`.
Requires one middleware registration per bot instance.

```python
from titan.extras import AskManager

ask = AskManager()
bot.middleware(ask.as_middleware())

@bot.command("start")
async def start(ctx):
    name = await ask(ctx, "What's your name?")   # AskManager is callable directly
    await ctx.reply(f"Hello, {name}!")
```

### ask.as_middleware()

Returns a middleware function that intercepts incoming messages for pending asks.
Must be registered with `bot.middleware(ask.as_middleware())`.

Interception rules:
- Only regular user messages are intercepted (not callbacks, not channel posts)
- Only intercepts when a future is pending for the exact `(chat_id, user_id)` pair
- Consumed messages do not reach any handler or subsequent middleware

### await ask(ctx, text, reply_markup=None) → str

`AskManager` instances are callable — invoke directly as `await ask(ctx, text)`.

Rules:
- Requires both `chat_id` and `user_id` — raises `TitanError` in channel handlers
- Only one pending ask per `(chat_id, user_id)` at a time — raises `TitanError` otherwise
- No persistence — pending asks are lost on bot restart

## Guarantee

Vanilla `Titan` instances have no `alias()`, no `_pending_asks`, and no ask/alias state of any kind.
`AskManager` and `AliasMap` are regular Python objects; they interact with Titan only through
the standard middleware interface (`bot.middleware(...)`).

---

## Actions

Actions are async context managers on `ctx` that represent Telegram UI states
during the execution of a code block.

### The contract

Every Action in Titan satisfies these rules:

1. **ctx-bound** — accessed via `ctx.action_name()`, never imported directly.
2. **State, not result** — represents a Telegram UI signal, not an operation that produces a value.
3. **`__aenter__` sends the signal** — one `sendChatAction` call at block entry.
4. **`__aexit__` is a no-op** — Telegram expires the signal automatically; no cleanup call is needed.
5. **Exceptions propagate** — `__aexit__` never returns `True`.
6. **`chat_id is None` is safe** — no API call is made; no exception is raised.

### Usage

```python
async with ctx.typing():
    result = await heavy_task()
await ctx.reply(result)
```

### What qualifies as an Action

An operation qualifies as an Action if and only if:
- it maps to a Telegram `sendChatAction` value,
- it is meaningfully used as a context manager wrapping work,
- and it produces no return value the developer uses.

Operations that send messages (`reply`, `send`) or return data are not Actions.
They are direct calls.

### Implemented Actions

| Method | Telegram action |
|---|---|
| `ctx.typing()` | `typing` |

### Stability

The Action contract is frozen. Any new Action added to Titan must satisfy all
six rules above. The internal implementation (`TypingAction` class) is not part
of the public API and is not exported.

→ Full reasoning: [docs/decisions/002-actions.md](docs/decisions/002-actions.md)

---

## titan.recipes — Official Patterns

### What Recipes are

Recipes are curated, tested patterns for using Titan's Core correctly.
They live in `titan.recipes` and are entirely optional. Importing a Recipe adds no state
to the bot and changes no runtime behavior. A bot that uses no Recipes is identical to
one that does — except in the handlers where a Recipe is explicitly called.

### What Recipes are not

Recipes are not a second API layer. They do not introduce new abstractions,
new models, or new capabilities. Everything a Recipe does can be done using
only `bot`, `ctx`, and `bot.telegram` — the Recipe is the documented,
readable form of that usage, nothing more.

### The Core/Recipe boundary

The direction of influence between Core and Recipes is strictly one-way:

```
Core defines what is available.
Recipes use what is available.
```

Recipes may not define Core structure. A Recipe that requires a Core change
in order to be clean is not a reason to make that Core change.

The permitted exception: if Recipe work surfaces a genuine inconsistency
in the Core — one that would affect any developer using that API, with or
without Recipes — that inconsistency may be corrected in Core.

**The test:** *Would this Core change be justified even if no Recipe existed?*

- Yes → fix Core, then write the Recipe cleanly.
- No → accept the limitation; document it; do not modify Core to serve the Recipe.

### Stability

Recipes follow the same stability rules as the rest of Titan. A Recipe's
public interface (`__init__` signature, callable contract) is frozen once
released. Internal implementation may change; the usage contract may not.

### What Recipes may use

| Allowed | Not allowed |
|---|---|
| `@bot.on()`, `@bot.command()`, `@bot.callback()` | New decorators or hooks not in Core |
| `ctx.*` properties and actions | Custom ctx properties introduced for a Recipe |
| `bot.middleware()` | Automatic middleware registration |
| `bot.telegram.*` | New telegram methods introduced for a Recipe |
| Existing models (`Sender`, `Chat`, `Message`) | New models introduced for a Recipe |
