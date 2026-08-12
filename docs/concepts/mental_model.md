# Mental Model

**Primary question this document answers: how should you think inside Titan?**

This document explains the structure behind Titan — not what the API does, but how the pieces relate to each other and where your code fits.

---

## The Update-Response Cycle

Every interaction begins with an **update**: a payload Telegram sends to your bot when something happens — a message arrives, a button is pressed, a user joins a group.

Titan processes each update in a fixed sequence:

```
Telegram → update arrives
         → middleware runs (can stop here)
         → handler executes
         → your code runs
```

Your code always lives at the end of this chain. Everything before it is infrastructure.

---

## Three Surfaces

Titan exposes three surfaces. Each has a single, distinct role.

### bot — the organizer

`bot` is where you configure Titan before it runs: registering handlers, adding middleware, defining aliases, including routers.

```python
bot = Titan(token)

@bot.command("start")
async def start(ctx):
    ...

bot.run()
```

`bot` does not handle updates directly. It sets up the structure that handles them.

### ctx — the handler surface

Every handler receives `ctx`. This is your primary interface during the update-response cycle.

`ctx` carries two things:

- **Data** — what arrived: `ctx.text`, `ctx.user_id`, `ctx.chat_id`, `ctx.sender`, and so on.
- **Actions** — what you can do: `ctx.reply()`, `ctx.edit()`, `ctx.ban_user()`, and so on.

The reason both live on the same object: a handler always operates on exactly one update. Bundling the update's data and the actions that respond to it into a single object means you never need to track which update you are responding to — `ctx` already knows. Your handler receives one `ctx`, does its work, and exits.

For the large majority of bots, `ctx` is all you need inside a handler.

→ For how `ctx` is designed and why it works the way it does: [concepts/ctx.md](ctx.md)
→ For how data models work in Titan and what they may and may not represent: [concepts/models.md](models.md)

### bot.telegram — the direct API

`bot.telegram` calls Telegram's API directly. It bypasses `ctx`, bypasses middleware, and is not tied to any update.

The reason it exists separately from `ctx`: not every API operation belongs to the current update. Sending a scheduled notification, pinning a message from two days ago, or fetching a chat's member count have no relationship to the update your handler is processing. If those operations lived on `ctx`, `ctx` would be responsible for things it has no context for. `bot.telegram` handles the parts of the API that fall outside the update-response cycle.

Use it for operations that happen outside the update-response cycle: proactive messages, pinning, scheduled notifications, fetching metadata.

```python
await bot.telegram.send_photo(chat_id=123, photo="file_id")
await bot.telegram.pin_message(chat_id=123, message_id=456)
```

Reaching for `bot.telegram` inside a handler is a signal worth noticing: either the operation genuinely exceeds the update-response cycle, or `ctx` is missing something it should expose.

→ For the full adapter reference: [reference/api.md](../reference/api.md)

---

## The Depth Gradient

The three surfaces form a gradient — from the most immediate to the most explicit:

```
ctx.reply()        ← immediate, inside the update cycle, through middleware
ctx.raw            ← raw Telegram JSON, non-frozen, last resort within ctx
bot.telegram.*     ← full Telegram API, outside the cycle, no middleware
```

You do not need to use all three. A simple bot lives entirely on `ctx`. A more complex one might reach deeper when needed. The gradient exists so that you start at the simplest surface and only go further when you have a reason to.

---

## Middleware

Middleware runs before every handler. It receives `ctx` and a `next` function. Calling `next()` continues execution. Returning without calling `next()` stops it.

```python
@bot.middleware
async def guard(ctx, next):
    if ctx.is_banned:
        return
    await next()
```

Middleware's role is flow control only: let this update through, or do not.

The reason the boundary is strict: if middleware could modify `ctx` or inject behavior, the state of `ctx` arriving at a handler would depend on which middlewares happened to run — and in what order. Handlers would become difficult to reason about in isolation. By limiting middleware to flow control, `ctx` always arrives at a handler in a predictable state.

→ For the full middleware model, patterns, and constraints: [concepts/middleware.md](middleware.md)

---

## Router

For small bots, all handlers live in one file. As a project grows, `Router` lets you split handler definitions across files and merge them into the bot at startup.

```python
# admin.py
router = Router()

@router.command("ban")
async def ban(ctx):
    ...
```

```python
# main.py
bot.include(router)
```

Router is a code organization tool. It has no runtime behavior of its own — `bot.include()` transfers its registrations to the bot before the first update arrives. Once included, a router is indistinguishable from handlers registered directly on the bot.

→ For the Router API: [reference/api.md](../reference/api.md)

---

## What Titan Does Not Cover

Titan does not provide state management, webhook support, session handling, or conversation flows.

This is intentional. Titan's surface is kept minimal so that what it does cover remains stable and predictable. When you need something outside that surface, `bot.telegram` provides direct access to the full Telegram Bot API — without requiring Titan to have an opinion about how that capability should work.

→ For the reasoning behind specific omissions: [faq.md](../faq.md)
