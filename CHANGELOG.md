# Changelog

All notable changes to titanx will be documented here.

---

## [1.0.0] - 2026-06-24

Initial public release.

### Public API

- `Titan` — core bot class
- `Router` — code organization tool for splitting handlers across files
- `InlineKeyboard` — inline keyboard builder
- `TitanError` / `TelegramError` — error types

### Bot Methods

- `bot.on(event)` — raw event handler
- `bot.command(name)` — command handler
- `bot.callback(data)` — inline button handler
- `bot.middleware` — pre-handler middleware
- `bot.alias(alias, target)` — optional naming layer for ctx methods
- `bot.include(router)` — merge a Router into the bot
- `bot.run()` / `bot.run_async()` — synchronous and async entrypoints
- `bot.telegram` — direct Telegram API adapter
- `bot.banned_users` — public set for ban management
- `bot.offset` — current polling offset

### Context (`ctx`)

- Data: `user_id`, `chat_id`, `text`, `callback_data`, `is_banned`, `sender`, `chat`, `message`
- Actions: `reply()`, `send()`, `edit()`, `delete_message()`, `ban_user()`, `leave()`, `answer_callback()`, `refresh_permissions()`
- Escape hatch: `ctx.raw` (not part of frozen contract)

### Behaviors

- Long polling with exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s, reset on success
- Callback routing: `bot.callback(data)` takes priority, falls through to `bot.on("callback")`
- Duplicate command or callback registration raises `TitanError`
- Middleware is linear — no branching, no return values
- Router does not support middleware, aliases, or nested include
