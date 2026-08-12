# FAQ

This document resolves confusion between concepts and explains design decisions that might feel surprising. It does not duplicate content from reference/ or concepts/.

---

## ctx.reply() vs ctx.send() — when does the difference matter?

In private chats, the visual difference is negligible. In groups, `ctx.reply()` quotes the original message, which anchors your response to the correct conversation thread. `ctx.send()` posts a standalone message with no attachment to any prior message.

Use `ctx.reply()` when the context of the reply matters to a reader. Use `ctx.send()` when the message is independent — a notification, a status update, a result that makes sense without seeing what triggered it.

---

## @bot.callback("data") vs @bot.on("callback") — which do I use?

They serve different scopes. `@bot.callback("data")` handles one specific button. `@bot.on("callback")` handles everything else.

If every button in your bot has a distinct `callback_data` and a clear handler, use `@bot.callback` for each. If you have dynamic data (e.g. `"vote_42"`, `"vote_91"`) that you cannot enumerate at registration time, use `@bot.on("callback")` and parse `ctx.callback_data` inside the handler.

The two can coexist. `@bot.callback` handlers take priority. Unmatched callbacks fall through to `@bot.on("callback")`.

---

## ctx.ban_user() vs bot.banned_users — are these the same thing?

No. They operate at different layers and should not be confused.

`ctx.ban_user()` calls Telegram's API. The user is banned from the Telegram chat. This is a network call and requires the bot to have admin permissions.

`bot.banned_users` is a local Python `set[int]`. It never calls Telegram. Titan checks it before middleware runs and writes the result to `ctx.is_banned`. A user in `bot.banned_users` is not banned on Telegram — your middleware decides what that means (ignore the update, send a message, log it).

The two are independent. You can use either, both, or neither.

---

## Why does ctx.edit() raise an error instead of silently doing nothing?

`ctx.edit()` requires a `callback_query` context to know which message to edit. Calling it outside that context is almost always a programming mistake — a handler meant for callbacks was accidentally wired to a message event, or `ctx.edit()` was called in the wrong branch of an `if` statement.

Silently doing nothing would hide that mistake. The error surfaces it immediately, at the point of failure, with a message that names the cause.

→ For the constraint details: [reference/api.md — ctx.edit()](reference/api.md)

---

## Why can't Router register middleware?

Middleware order matters across the entire bot. If routers could each register their own middleware, the execution order would depend on the order routers were included — implicit, hard to trace, and surprising when it breaks.

By restricting middleware to `bot`, there is one registration point and one clear order. Any middleware registered on `bot` runs for every update, regardless of which router ultimately handles it.

---

## Why do I need to call answer_callback() manually?

Titan cannot decide what to show when a button is pressed. `answer_callback()` accepts optional `text` and `show_alert` parameters that change what the user sees. If Titan called it automatically with no text, you would need an immediate second call to show anything.

Two calls for every callback handler is worse than one explicit call. The explicit call also makes it clear when a handler forgot to acknowledge the query — the loading indicator stays active, which is visible feedback that something is missing.

---

## Middleware vs a check inside the handler — where does logic belong?

Use middleware when the logic applies to every update and the decision is binary: continue or stop. Use a handler check when the logic is specific to what that handler does.

A ban check belongs in middleware — it is the same decision for every update. A "does this user have a pending order?" check belongs in the handler — only the `/confirm` command cares about it.

The signal that logic is in the wrong place: middleware that reads `ctx.text` to decide what to do, or a handler that repeats the same guard that five other handlers also have.

→ For the full model: [concepts/middleware.md](concepts/middleware.md)

---

## ctx.raw vs structured properties — which do I use?

Use the structured properties (`ctx.text`, `ctx.user_id`, `ctx.sender`, etc.) whenever they cover what you need. They are typed, stable across Telegram API changes, and their names are part of Titan's contract.

Use `ctx.raw` when you need a field that Titan does not expose — a specific message entity, an uncommon update type, a field added in a recent Telegram API update. `ctx.raw` is the complete, unmodified JSON Telegram sent.

`ctx.raw` is not part of Titan's stable contract. Its structure follows Telegram's API. If Telegram renames a field, `ctx.raw` changes with it.

---

## Why does registering the same command twice raise an error instead of replacing?

Replacing silently would mean the second registration shadows the first with no indication that it happened. In a codebase split across multiple files and routers, this would be nearly impossible to debug — the handler you expected to run simply never runs, and there is no error to trace.

The error makes the conflict explicit and locates it at registration time, before any update is processed.

---

## My ban list disappears every time the bot restarts. How do I fix that?

`bot.banned_users` is a plain Python `set[int]` held in memory. Titan does not persist it — persistence is your application's responsibility.

To survive restarts, save the set before shutdown and load it on startup:

```python
import json, pathlib

BAN_FILE = pathlib.Path("banned.json")

if BAN_FILE.exists():
    bot.banned_users = set(json.loads(BAN_FILE.read_text()))

@bot.command("ban")
async def on_ban(ctx):
    bot.banned_users.add(ctx.user_id)
    BAN_FILE.write_text(json.dumps(list(bot.banned_users)))
```

---

## Telegram is returning rate limit errors. What should I do?

Titan does not retry automatically. Rate limit errors arrive as `TelegramError` and are routed to your error handler.

Handle them there, or use a middleware wrapper for outgoing calls that are likely to burst:

```python
import asyncio
from titan import TelegramError

@bot.error_handler
async def on_error(ctx, exc):
    if isinstance(exc, TelegramError) and "429" in str(exc):
        await asyncio.sleep(1)
    else:
        raise exc
```

Telegram's limits are 30 messages per second globally and 1 message per second per chat. If your bot sends to many chats in a short period, throttle the outgoing calls in your application logic rather than relying on error recovery.

---

## My middleware is not running for bot.telegram calls. Is that expected?

Yes. `bot.telegram` is a direct adapter to Telegram's API. It has no relationship to the update-response cycle — no `ctx`, no middleware chain, no routing.

Middleware runs on incoming updates, not on outgoing API calls. If you need to intercept or wrap outgoing calls, that logic belongs in a utility function your code calls explicitly, not in middleware.

→ For where `bot.telegram` fits: [concepts/mental_model.md](concepts/mental_model.md)
