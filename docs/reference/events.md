# Events Reference

In Titan, an **event** is a named category of incoming update. You register handlers for events using `@bot.on(event)`. When an update arrives, Titan identifies its type and dispatches it to the appropriate handlers.

This document lists all supported events, what triggers each one, and how Titan routes between them.

→ For handler registration syntax: [reference/api.md](api.md)
→ For how routing fits into the execution chain: [concepts/mental_model.md](../concepts/mental_model.md)

---

## Supported Events

### `message`

Triggered by any regular message sent to the bot or group — text, photo, document, sticker, and so on — that does not match a more specific event.

```python
@bot.on("message")
async def on_message(ctx):
    await ctx.reply("Got your message.")
```

Commands that do not match any registered `@bot.command` handler also fall through to `on("message")`.

---

### `callback`

Triggered when a user presses an inline keyboard button that carries a `callback_data` value.

```python
@bot.on("callback")
async def on_callback(ctx):
    await ctx.answer_callback()
```

This is the **fallback** handler for callbacks. If a `@bot.callback("data")` handler is registered and matches the button's `callback_data`, that handler runs instead and `on("callback")` is not called.

→ See [Callback Routing](#callback-routing) below.

---

### `channel`

Triggered by posts sent in a Telegram channel where the bot is an admin.

```python
@bot.on("channel")
async def on_channel(ctx):
    pass
```

Channel posts are routed separately and do not reach `on("message")`.

---

### `new_member`

Triggered when one or more users join a group or are added by another member.

```python
@bot.on("new_member")
async def on_join(ctx):
    for member in ctx.new_members or []:
        await ctx.send(f"Welcome, {member.get('first_name')}!")
```

`ctx.new_members` is a list of raw user dicts for everyone who joined in this update.

This event is routed before `on("message")`. An update that contains new members never reaches a general message handler.

---

### `left_member`

Triggered when a user leaves a group or is removed by an admin.

```python
@bot.on("left_member")
async def on_leave(ctx):
    name = ctx.left_member.get("first_name") if ctx.left_member else "Someone"
    await ctx.send(f"{name} has left.")
```

`ctx.left_member` is a raw user dict for the user who left.

Like `new_member`, this event is routed before `on("message")`.

---

## Callback Routing

When a callback update arrives, Titan applies the following priority:

1. If a `@bot.callback("data")` handler is registered and the button's `callback_data` matches, that handler runs.
2. If no matching `@bot.callback` handler exists, the update falls through to `@bot.on("callback")`.
3. If neither is registered, the update is silently dropped.

```python
@bot.callback("confirm")
async def on_confirm(ctx):
    # runs only when callback_data == "confirm"
    await ctx.answer_callback("Confirmed.")

@bot.on("callback")
async def on_any_callback(ctx):
    # runs for all other callback_data values
    await ctx.answer_callback()
```

`@bot.callback("data")` handlers are exclusive: registering the same `callback_data` twice raises a `TitanError`.

---

## Routing Priority Summary

When an update arrives, Titan routes it in this order:

| Priority | Condition | Routed to |
|---|---|---|
| 1 | Update is a channel post | `on("channel")` |
| 2 | Update is a callback query with a matching `@bot.callback` | that specific handler |
| 3 | Update is a callback query with no matching handler | `on("callback")` |
| 4 | Message contains new members | `on("new_member")` |
| 5 | Message contains a leaving member | `on("left_member")` |
| 6 | Message text starts with `/` and matches a registered command | that command handler |
| 7 | All other messages | `on("message")` |

Each update matches exactly one path. Titan does not fan out a single update to multiple event types.
