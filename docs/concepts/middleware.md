# Middleware

**Primary question this document answers: what is middleware for, and why does it have strict boundaries?**

This document explains the middleware model conceptually.

→ For the `bot.middleware` registration syntax: [reference/api.md](../reference/api.md)
→ For where middleware fits in the execution chain: [concepts/mental_model.md](mental_model.md)

---

## What Middleware Is

Middleware is a function that runs before your handler on every update. It receives `ctx` and a `next` function. Its only decision is whether to pass the update forward.

```python
@bot.middleware
async def logger(ctx, next):
    print(f"update from {ctx.user_id}")
    await next()
```

Calling `await next()` continues execution toward the handler. Returning without calling `next()` stops the update there. No other outcome is possible.

---

## Why the Boundary Is Strict

Middleware cannot modify `ctx`, inject new methods, or return values that affect handler behavior. This is a deliberate constraint.

The reason: if middleware could change the state of `ctx`, a handler's behavior would depend on which middlewares happened to run before it — and in what order. You could no longer look at a handler in isolation and understand what it does. You would need to trace the entire middleware chain first.

By limiting middleware to flow control only, `ctx` always arrives at a handler in a known state. Handlers remain self-contained and predictable regardless of how many middlewares are registered.

---

## Execution Order

Middleware runs in the order it was registered. The first registered middleware is the outermost layer.

```python
@bot.middleware
async def first(ctx, next):
    print("before — first")
    await next()
    print("after — first")

@bot.middleware
async def second(ctx, next):
    print("before — second")
    await next()
    print("after — second")
```

Output when an update arrives:

```
before — first
before — second
after — second
after — first
```

Each middleware wraps the next. The handler runs at the innermost point.

---

## What Middleware Is For

Middleware is appropriate for logic that applies uniformly across all updates, independent of what the handler will do.

**Logging** — record every incoming update before the handler sees it.

```python
@bot.middleware
async def log_updates(ctx, next):
    print(f"[{ctx.chat_id}] {ctx.text or '<no text>'}")
    await next()
```

**Authorization** — stop updates from users who are not allowed through.

```python
@bot.middleware
async def guard(ctx, next):
    if ctx.is_banned:
        return
    await next()
```

**Rate limiting** — track request frequency and stop updates that exceed a threshold.

These patterns share a structure: inspect `ctx`, decide whether to call `next()`.

---

## What Middleware Is Not For

Middleware should not contain logic that belongs in a specific handler.

If only one command needs a permission check, that check belongs in the command handler — not in middleware where it runs for every update. Middleware that applies conditionally based on the update's content is a handler wearing the wrong clothes.

Middleware is also not for:
- Modifying what a handler will do
- Storing state between updates
- Communicating results back to the caller

If you need any of those, the logic belongs in the handler or in external state managed by your application.

---

## The Ban System

The ban system is the built-in example of the middleware pattern.

`bot.banned_users` is a plain `set[int]` managed entirely by your application. Before any middleware or handler runs, Titan checks whether `ctx.user_id` is in that set and writes the result to `ctx.is_banned`.

Titan does not act on `ctx.is_banned` automatically. Your middleware decides what to do with it:

```python
@bot.middleware
async def guard(ctx, next):
    if ctx.is_banned:
        return
    await next()
```

This separation is intentional. Titan signals the state (`ctx.is_banned = True`). Your middleware decides the behavior (ignore the update, notify the user, log it). The framework does not make that decision for you.

→ For `bot.banned_users` and `ctx.is_banned` reference: [reference/api.md](../reference/api.md)
