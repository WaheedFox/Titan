# Guard Middleware

**The architectural mistake this pattern prevents:**
Middleware that owns application behavior.

---

## The Mistake

Middleware in Titan decides whether execution continues. When middleware stops
an update — by returning without calling `next()` — it ends its own
responsibility at that point.

The mistake is allowing middleware to go further: to reply, to log, to record
an audit event, to trigger any application action. Once middleware does any of
these things, it has moved from deciding whether execution continues into
deciding what the application does. Those are different responsibilities, and
they belong to different layers.

```python
# Wrong
@bot.middleware
async def guard(ctx, next):
    if ctx.is_banned:
        await ctx.reply("Access denied.")   # ← application behavior
        return
    await next()
```

---

## Why the Wrong Approach Looks Reasonable

Middleware already has access to `ctx` and runs before any handler. If the
update is going to be stopped anyway, responding immediately feels efficient —
"I'm already here, I'll handle it."

This intuition is reinforced by frameworks where middleware responses are
normal: Flask `before_request`, Express middleware, and others treat
middleware-level responses as a valid and expected pattern. Developers carry
that expectation into Titan.

The wrong approach also works technically. Titan does not prevent `ctx.reply()`
inside middleware — the code compiles and runs without error. The boundary is
architectural, not enforced by the runtime.

---

## The Boundary Titan Enforces

Middleware controls flow: call `next()` or do not call it. That is its complete
responsibility.

This is established in `docs/concepts/middleware.md`:
> "Middleware's role is flow control only: let this update through, or do not."

And in `docs/internal/design_notes.md` as a confirmed design principle:
> "Middleware handles flow control only. It cannot inject behavior into ctx or
> contain business logic."

---

## The Correct Composition

```python
# Middleware: the decision
@bot.middleware
async def guard(ctx, next):
    if ctx.is_banned:
        return
    await next()

# Handler: all application behavior
@bot.command("start")
async def start(ctx):
    await ctx.reply("Hello.")
```

The middleware owns one thing: whether this update proceeds.
The handler owns everything that happens when it does.

The handler has no knowledge of the conditions under which it might not have
been called. The middleware has no knowledge of what the handler will do. Each
layer expresses only its own responsibility.

This separation holds regardless of what the behavior is. Whether the handler
replies, logs an access event, records a database entry, or triggers a
downstream action — that behavior belongs in the handler, not in the middleware
that decided to allow the update through.

---

## When This Pattern Does Not Apply

**The condition is specific to one handler.**
If a check applies only to a single command, it belongs at the top of that
handler — not in middleware that runs before every update.

```python
@bot.command("admin")
async def admin(ctx):
    if ctx.user_id not in ADMIN_IDS:
        return              # handler-level guard, not a middleware concern
    await ctx.reply("Admin panel.")
```

**The check requires async work scoped to the handler.**
If determining whether to proceed requires data that the handler also needs,
fetch it inside the handler. Splitting the fetch between middleware and handler
creates implicit coupling.

---

## What This Pattern Does Not Cover

- How to order multiple middlewares relative to each other.
- How to design authorization or permission systems.
- How `ctx.is_banned` or `bot.banned_users` work.
- What to do when a stopped update requires a response — that is an
  application design question, not a middleware composition question.

→ For how middleware works: [concepts/middleware.md](../concepts/middleware.md)
→ For `bot.banned_users` and `ctx.is_banned`: [reference/api.md](../reference/api.md)
