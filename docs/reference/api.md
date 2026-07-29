# API Reference

Reference for all public surfaces in Titan, organized by responsibility rather than by class.

→ For events and routing priority: [reference/events.md](events.md)
→ For keyboard builder classes: [reference/keyboard.md](keyboard.md)

---

## 1. Core Entry Point

The `Titan` class is the bot instance. It holds configuration, registration tables, and the polling loop.

```python
from titan import Titan

bot = Titan(token="YOUR_TOKEN")
bot.run()
```

### `Titan(token)`

| Parameter | Type | Description |
|---|---|---|
| `token` | `str` | Your Telegram bot token from @BotFather |

### `bot.run(debug=False, offset=0, on_offset=None)`

Starts the polling loop. Blocks until interrupted.

| Parameter | Type | Description |
|---|---|---|
| `debug` | `bool` | If `True`, prints each raw update to stdout |
| `offset` | `int` | Initial update offset (useful for resuming after restart) |
| `on_offset` | `Callable[[int], None] \| None` | Called after each update with the current offset value |

### `bot.run_async(debug=False, offset=0, on_offset=None)`

Awaitable version of `bot.run()`. Use this when you need to control the event loop yourself.

```python
import asyncio
asyncio.run(bot.run_async())
```

### `bot.offset`

`int` — the highest `update_id` that Titan has accepted for processing. Updated immediately after an update is enqueued to its chat worker, before the handler executes.

> **Important:** `bot.offset` does *not* mean "the last update whose handler has completed." It means "the last update for which Titan has taken responsibility." Use it to resume polling after a restart — all updates with an ID greater than `bot.offset` will be re-delivered by Telegram.

```python
# Persist offset across restarts
import json, pathlib

def save_offset(offset):
    pathlib.Path("offset.json").write_text(json.dumps({"offset": offset}))

def load_offset():
    try:
        return json.loads(pathlib.Path("offset.json").read_text())["offset"]
    except FileNotFoundError:
        return 0

bot.run(offset=load_offset(), on_offset=save_offset)
```

### `bot.banned_users`

`set[int]` — a plain Python set of user IDs. Managed entirely by your application. Before any middleware or handler runs, Titan checks whether `ctx.user_id` is in this set and writes the result to `ctx.is_banned`.

```python
bot.banned_users.add(user_id)
bot.banned_users.discard(user_id)
```

This set is held in memory and resets on every restart. Titan does not persist it. If your ban list must survive restarts, serialize it to a file or database on shutdown and reload it on startup.

### `bot.capabilities`

Read-only property. Returns `BotCapabilities | None`.

Exposes what is currently known about the bot's account-level abilities.
Returns `None` when that information is not yet available. Does not fetch
silently and makes no promise about availability — it reflects the current
state of cached information, nothing more.

These capabilities are global and stable: they do not change per-chat or
per-update, and cannot change without a BotFather setting change.

```python
if bot.capabilities and bot.capabilities.can_join_groups:
    ...
```

| Property | Type | Description |
|---|---|---|
| `can_join_groups` | `bool` | Whether the bot can be added to groups |
| `can_read_all_group_messages` | `bool` | Whether privacy mode is disabled |
| `supports_inline_queries` | `bool` | Whether the bot supports inline queries |

### `bot.telegram`

Access point for the Telegram adapter. Use it for operations that fall outside the update-response cycle — sending to arbitrary chats, media, pinning, bot configuration.

→ See [Telegram Adapter](#4-telegram-adapter) below.

### `bot.alias(alias, target)`

Adds an alias for an existing `ctx` method. The original method is unchanged.

| Parameter | Type | Description |
|---|---|---|
| `alias` | `str` | The new name to expose on `ctx` |
| `target` | `str` | An existing `ctx` method name |

Raises `TitanError` if `target` does not exist on `ctx`.

```python
bot.alias("say", "reply")   # ctx.say() now works like ctx.reply()
```

---

## 2. Context

`ctx` is passed to every handler and middleware. It is created per update and discarded after the handler chain completes.

→ For the design reasoning behind `ctx`: [concepts/ctx.md](../concepts/ctx.md)

### Properties

**Update data**

| Property | Type | Description |
|---|---|---|
| `ctx.text` | `str \| None` | Text of the incoming message |
| `ctx.user_id` | `int \| None` | Telegram user ID of the sender |
| `ctx.chat_id` | `int \| None` | Telegram chat ID where the update arrived |
| `ctx.username` | `str \| None` | Sender's username, without `@` |
| `ctx.message_id` | `int \| None` | ID of the incoming message |
| `ctx.callback_data` | `str \| None` | The `callback_data` string from the pressed button |
| `ctx.callback_id` | `str \| None` | Internal callback query ID, required by `answer_callback()` |
| `ctx.new_members` | `list[Sender] \| None` | List of senders who joined; available in `new_member` handlers |
| `ctx.left_member` | `Sender \| None` | The sender who left; available in `left_member` handlers |

**Structured models**

| Property | Type | Description |
|---|---|---|
| `ctx.sender` | `Sender` | Typed object with sender info — `id`, `first_name`, `last_name`, `username`, `is_bot` |
| `ctx.chat` | `Chat` | Typed object with chat info — `id`, `type`, `title`, `username`, `is_group()`, `is_private()` |
| `ctx.message` | `Message` | Typed object for the current message — `id`, `text`, `chat_id` |

**State**

| Property | Type | Description |
|---|---|---|
| `ctx.raw` | `dict` | The complete, unmodified JSON update from Telegram |
| `ctx.is_banned` | `bool` | `True` if `ctx.user_id` is in `bot.banned_users`; set before middleware runs |
| `ctx.permissions` | `ChatPermissions \| None` | `None` until `ctx.fetch_permissions()` is called |

### Actions

**Sending messages**

---

#### `await ctx.reply(text, parse_mode=None, reply_markup=None)`

Sends a message that quotes the incoming message.

| Parameter | Type | Description |
|---|---|---|
| `text` | `str` | Message text |
| `parse_mode` | `str \| None` | `"HTML"` or `"Markdown"` |
| `reply_markup` | `InlineKeyboard \| None` | Keyboard to attach |

---

#### `await ctx.send(text, parse_mode=None, reply_markup=None)`

Sends a standalone message to the current chat, without quoting.

| Parameter | Type | Description |
|---|---|---|
| `text` | `str` | Message text |
| `parse_mode` | `str \| None` | `"HTML"` or `"Markdown"` |
| `reply_markup` | `InlineKeyboard \| None` | Keyboard to attach |

---

#### `await ctx.edit(text, parse_mode=None, reply_markup=None)`

Edits the bot's own message. Only valid inside `@bot.on("callback")` or `@bot.callback("data")` handlers — the message being edited is the one that carried the inline keyboard.

Raises `TitanError` if called outside a callback context.

| Parameter | Type | Description |
|---|---|---|
| `text` | `str` | New message text |
| `parse_mode` | `str \| None` | `"HTML"` or `"Markdown"` |
| `reply_markup` | `InlineKeyboard \| None` | Updated keyboard, or `None` to remove it |

---

#### `await ctx.answer_callback(text=None, show_alert=False)`

Acknowledges a callback query. Must be called in every callback handler to dismiss the loading indicator on the button.

| Parameter | Type | Description |
|---|---|---|
| `text` | `str \| None` | Optional text shown as a notification or alert |
| `show_alert` | `bool` | If `True`, shows a modal alert instead of a toast notification |

---

**Moderation**

#### `await ctx.delete_message()`

Deletes the current message. The bot must have `can_delete_messages` permission in the chat.

---

#### `await ctx.ban_user(user_id=None)`

Bans a user from the current chat via Telegram's API.

| Parameter | Type | Description |
|---|---|---|
| `user_id` | `int \| None` | User to ban. Defaults to `ctx.user_id` if not provided |

---

#### `await ctx.leave()`

Makes the bot leave the current chat.

---

**Permissions**

#### `await ctx.fetch_permissions()`

Fetches the bot's current permissions in the chat from Telegram API and stores
the result in `ctx.permissions`. Returns the `ChatPermissions` object directly.

Raises `TitanError` if the context has no `chat_id`.
Propagates `TelegramError` on API failure — no silent fallback.

```python
await ctx.fetch_permissions()
if ctx.permissions.can_delete_messages:
    await ctx.delete_message()
```

| Property | Type | Description |
|---|---|---|
| `can_manage_chat` | `bool` | General chat management |
| `can_delete_messages` | `bool` | Delete members' messages |
| `can_manage_video_chats` | `bool` | Manage video chats |
| `can_restrict_members` | `bool` | Restrict member permissions |
| `can_promote_members` | `bool` | Promote members to admins |
| `can_change_info` | `bool` | Change chat info |
| `can_invite_users` | `bool` | Invite new users |
| `can_pin_messages` | `bool` | Pin messages (groups only) |
| `can_manage_topics` | `bool` | Manage topics (forum groups only) |
| `can_post_messages` | `bool` | Post messages (channels only) |
| `can_edit_messages` | `bool` | Edit messages (channels only) |

All properties default to `False` when the bot is not an admin or the field is absent.

---

## 3. Routing

Handlers are registered on `bot` directly, or collected in a `Router` and merged with `bot.include()`.

→ For event names and routing priority: [reference/events.md](events.md)
→ For the middleware execution model: [concepts/middleware.md](../concepts/middleware.md)

### Registering on bot

#### `@bot.on(event)`

Registers a handler for a named event. Multiple handlers can be registered for the same event — all run in registration order.

```python
@bot.on("message")
async def on_message(ctx):
    await ctx.reply("Got it.")
```

---

#### `@bot.command(name)`

Registers a handler for a specific command (e.g. `"start"` for `/start`). Commands are matched without the leading `/`.

Raises `TitanError` if the same command is registered twice.

```python
@bot.command("start")
async def on_start(ctx):
    await ctx.reply("Hello!")
```

---

#### `@bot.callback(data)`

Registers a handler for a specific `callback_data` value. Takes priority over `@bot.on("callback")`.

Raises `TitanError` if the same `callback_data` is registered twice.

```python
@bot.callback("confirm_yes")
async def on_yes(ctx):
    await ctx.answer_callback()
    await ctx.edit("Confirmed.")
```

---

#### `@bot.middleware`

Registers a middleware function. Middleware runs before every handler, in registration order.

```python
@bot.middleware
async def guard(ctx, next):
    if ctx.is_banned:
        return
    await next()
```

Middleware cannot be registered on a `Router` — only on `bot`.

---

#### `@bot.error_handler`

Registers a function that is called when any handler, command, callback, or middleware raises an unhandled exception.

```python
@bot.error_handler
async def on_error(ctx, exc):
    await ctx.reply("Something went wrong.")
```

| Parameter | Type | Description |
|---|---|---|
| `ctx` | `Context` | The context at the point of failure |
| `exc` | `Exception` | The exception that was raised |

If no error handler is registered, the exception is printed to stdout and execution continues. If the error handler itself raises, that exception is also printed to stdout and does not propagate.

Only one error handler can be registered per bot instance. Registering a second replaces the first.

---

#### `bot.include(router)`

Merges all handlers, commands, and callbacks from a `Router` into `bot`.

Raises `TitanError` if any command or `callback_data` already exists on `bot`.

`@bot.on()` handlers from the router are appended silently — no duplicate check. Include each router exactly once.

```python
from mybot.users import router as users_router
bot.include(users_router)
```

---

### Router

`Router` collects registrations independently of `bot`. Use it to split handlers across multiple files.

```python
from titan import Router

router = Router()

@router.command("help")
async def on_help(ctx):
    await ctx.reply("Help text here.")
```

`Router` supports `@router.on()`, `@router.command()`, and `@router.callback()` with identical signatures to their `bot` equivalents. It does not support `@router.middleware`.

---

## 4. Telegram Adapter

`bot.telegram` provides direct access to Telegram's Bot API for operations outside the update-response cycle. It does not interact with middleware, aliases, or routing.

All methods require an active session — call `bot.run()` or `bot.run_async()` before using them outside of handler context.

```python
await bot.telegram.send_message(chat_id=123456, text="Hello from outside a handler.")
```

### Messaging

| Method | Description |
|---|---|
| `send_message(chat_id, text, parse_mode=None, reply_markup=None)` | Send a text message |
| `send_photo(chat_id, photo, caption=None, parse_mode=None, reply_markup=None)` | Send a photo by file ID or URL |
| `send_video(chat_id, video, caption=None, parse_mode=None, reply_markup=None)` | Send a video |
| `send_document(chat_id, document, caption=None, parse_mode=None, reply_markup=None)` | Send a file |
| `send_audio(chat_id, audio, caption=None, parse_mode=None)` | Send an audio file |
| `send_sticker(chat_id, sticker)` | Send a sticker by file ID |
| `send_animation(chat_id, animation, caption=None, parse_mode=None)` | Send a GIF or animation |

### Message Management

| Method | Description |
|---|---|
| `forward_message(chat_id, from_chat_id, message_id)` | Forward a message with the forward badge |
| `copy_message(chat_id, from_chat_id, message_id, caption=None)` | Copy a message without the forward badge |
| `pin_message(chat_id, message_id, disable_notification=False)` | Pin a message |
| `unpin_message(chat_id, message_id)` | Unpin a specific message |
| `unpin_all_messages(chat_id)` | Unpin all messages in a chat |

### Chat Info

| Method | Description |
|---|---|
| `get_chat(chat_id)` | Get chat metadata |
| `get_chat_member(chat_id, user_id)` | Get a member's status and permissions |
| `get_chat_member_count(chat_id)` | Get the number of members |

### Bot Configuration

| Method | Description |
|---|---|
| `set_my_commands(commands)` | Set the command list shown in the Telegram UI |
| `get_my_commands()` | Get the current command list |
| `delete_my_commands()` | Remove the command list |

`set_my_commands` expects a list of `{"command": str, "description": str}` dicts.

```python
await bot.telegram.set_my_commands([
    {"command": "start", "description": "Start the bot"},
    {"command": "help",  "description": "Show help"},
])
```

---

## 5. Errors

### `TitanError`

The base exception for all errors raised by Titan. Catch it to handle any Titan-originated error.

```python
from titan import TitanError

try:
    bot.include(router)
except TitanError as e:
    print(e)
```

Titan raises `TitanError` for configuration mistakes: duplicate command registration, duplicate `callback_data`, calling `ctx.edit()` outside a callback context, registering an alias to a non-existent method.

---

### `TelegramError`

Subclass of `TitanError`. Raised when Telegram's API returns a non-OK response, or when the HTTP session is not yet started.

`TelegramError` messages include the method name, Telegram's error description, and the error code.

```python
from titan import TelegramError

try:
    await bot.telegram.send_message(chat_id=0, text="test")
except TelegramError as e:
    print(e)  # "Telegram API error on 'sendMessage': Bad Request (error_code: 400)"
```
