# Understanding Context

**Primary question this document answers: why is `ctx` designed the way it is?**

This document does not list `ctx` methods or their parameters.

→ For the complete method reference: [reference/api.md](../reference/api.md)
→ For where `ctx` fits in the overall structure: [concepts/mental_model.md](mental_model.md)

---

## What ctx Represents

`ctx` represents a single update — one moment of interaction between a user and your bot.

It is not a long-lived object. It is not shared between handlers. It is created for one update, passed to one handler chain, and discarded.

This scope is deliberate. A handler's job is to respond to what just happened. Keeping `ctx` tied to a single update means a handler never needs to ask "which update am I responding to?" — the answer is always: the one that produced this `ctx`.

---

## Why Data and Actions Live Together

`ctx` carries both data (what arrived) and actions (what you can do). This is not accidental.

An action like `ctx.reply()` is meaningful only in the context of a specific update — it replies to the chat that sent that update. Separating data and actions would mean passing the update context into every action call manually. Instead, `ctx` holds the context once and makes it available to every action implicitly.

The result: your handler receives one object, does its work, and exits. No threading the update through function arguments.

---

## Structured Data vs Raw Data

`ctx` exposes update data at two levels.

**Structured properties** — `ctx.text`, `ctx.user_id`, `ctx.sender`, `ctx.chat` — give you normalized, typed access to the most commonly needed fields. `ctx.sender` is a `Sender` object. `ctx.chat` is a `Chat` object. These exist because working with typed properties is more readable and less error-prone than navigating raw dicts.

**`ctx.raw`** gives you the complete, unmodified JSON that Telegram sent. Use it when `ctx` does not expose a field you need.

`ctx.raw` is intentionally not part of Titan's stable contract. Its structure follows Telegram's API, not Titan's. If Telegram changes a field name, `ctx.raw` changes with it. The structured properties insulate you from that — `ctx.raw` does not.

---

## Explicit Over Automatic

Some things `ctx` could do automatically, but does not.

`ctx.can_delete` tells you whether the bot has permission to delete messages in the current chat. But `ctx` does not check this automatically on every update — that would mean an API call on every handler, even when you have no intention of deleting anything.

Instead, you call `ctx.refresh_permissions()` explicitly when you need that information. The result is stored in `ctx.can_delete` for the duration of the handler.

The pattern applies broadly: `ctx` signals state when it has it, but does not make API calls unless you ask.

---

## Where ctx Ends

`ctx` covers what belongs to the update-response cycle. It does not cover operations that have no relationship to the current update.

When you need to send a message to a different chat, pin a message, or call a Telegram method that `ctx` does not expose, you step outside `ctx` and use `bot.telegram`.

This is not a limitation — it is a boundary. `ctx` is not designed to be a complete wrapper around Telegram's API. It is designed to make responding to an update as straightforward as possible. `bot.telegram` handles everything else.

→ For how `bot.telegram` relates to `ctx`: [concepts/mental_model.md](mental_model.md)
