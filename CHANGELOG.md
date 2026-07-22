# Changelog

All notable changes to titanx will be documented here.

---

## [Unreleased]

### Open Tracking Items — User Privacy & Erasure Protocol (#11)

*الميزة مكتملة ومغلقة. البندان التاليان توثيق لمتابعات داخلية لا تمنع الاكتمال.*

**DOC-01 — توحيد رسالة خطأ تعارض الأوامر المحجوزة مع ADR-017**

رسالة `TitanError` الصادرة عند محاولة تسجيل `/mydata` أو `/forgetme` تشمل حالياً جملة
`"Use @bot.on('message') if you need multiple handlers for the same input."` — مستعارة من
معالج التعارض العام. هذه الجملة لا تنطبق على الأوامر المحجوزة لأن المطوّر لا يبحث عن
handler بديل لأوامر الخصوصية. ADR-017 يُحدد النص دون هذه الجملة.
**القرار المطلوب:** إزالة الجملة من رسالة الأوامر المحجوزة، أو تحديث ADR-017 إذا اعتُبر النص
الحالي هو المعتمد. لا تغيير في السلوك — توحيد في الصياغة فقط.

**VDT-01 — توثيق سلوك `/forgetme` عند الفشل الجزئي في `erase_user()`**

عند فشل أحد الـ modules داخل `erase_user()` (مع نجاح البقية)، يتصاعد `TitanError` ولا
تصل رسالة تأكيد المحو للمستخدم ولا تُستدعى `on_forgetme_complete`. السلوك متسق مع
ADR-017 ("بعد نجاح المحو") لكن حالة الفشل الجزئي غير موثقة في ADR.
**المطلوب:** إضافة فقرة في ADR-017 تصف سلوك الفشل الجزئي، أو اختبار صريح يُثبّت
الـ semantics — دون تغيير أي سلوك.

---

### Confirmed — Update Lifecycle Semantics (Per-chat Dispatch)

*مراجعة التغيير الذي أُجري في commit "update lifecycle runtime correction".*

`bot.offset` يُحدَّث الآن بعد وضع الـ update في قائمة انتظار الـ chat worker مباشرةً —
قبل اكتمال الـ handler. السيمانتيكس السابقة كانت: offset = بعد اكتمال الـ handler.

**الحكم: تغيير مقصود وصحيح معمارياً.**

مع نظام per-chat queues حيث كل handler يُشغَّل كـ `asyncio.Task` مستقل، انتظار اكتمال
الـ handler كان سيُجمّد الـ offset في حالة `ask()` (handler معلَّق ينتظر رداً) —
ما يُوقف الـ polling بفاعلية. السيمانتيكس الجديدة "offset = ما قُبل للمعالجة" هي
الصحيحة لهذه البنية. الكود والاختبار (`test_offset_updated_after_dispatch`) والـ CONTRACT
(§8 on_offset hook) حُدِّثت جميعاً بالتزامن في نفس الـ commit. جميع الـ 885 اختباراً
ناجحة.

---

### Validation Tasks — معلّقة حتى اختبار runtime حقيقي

*تصنيف: Validation Task — لا يمكن حسمها نظرياً، تحتاج اختباراً في runtime فعلي.*

**UVF-03 — `bot.telegram.pin_message()` قابلة للوصول؟**

`type(bot.telegram)` هو `TelegramAdapter` والدالة مختبرة في `tests/test_adapter.py`. لكن تأكيد Pin فعلي يحتاج Bot Token حقيقياً وشاتاً حياً. **بروتوكول الإغلاق:** أرسل رسالة → استدعِ `bot.telegram.pin_message(...)` → تحقق أن الرسالة ثُبّتت. نجاح → أغلِق UVF-03. فشل → افتح `Code Issue` منفصلة بـ traceback كامل.

---

### Release Engineering — مقرر لإصدار لاحق

- **إضافة `MANIFEST.in`** — استثناء `tests/` من الـ sdist صراحةً (`prune tests`).
- **مراجعة محتويات الـ sdist** — التحقق من أن الـ sdist يحتوي فقط على `src/`، ملفات الجذر الضرورية (`LICENSE`, `README.md`, `pyproject.toml`)، دون مجلدات تطوير داخلية.
- **توثيق سياسة توزيع ملفات المصدر** — تحديد ما يُدرج في wheel وما يُدرج في sdist وما يُستثنى، كمرجع ثابت لكل إصدار قادم.

---

### Fixed

- **Silent failures cleanup** (see `docs/internal/investigations/silent-failures.md`):
  - `AliasMap.register()` now fails fast with `TitanError` when `alias` conflicts with an existing `Context` attribute (SF-01).
  - `MiddlewareChain.run()` logs a runtime warning when a middleware function returns a non-`None` value, since return values are ignored per CONTRACT §10 (SF-02).
  - `CONTRACT.md` §1 documents that direct mutation of `bot.commands` / `bot.handlers` / `bot.callback_handlers` is unsupported and undefined behavior; no runtime enforcement added (SF-03).
  - `bot.run_async()` now logs a warning instead of silently swallowing `get_me()` failures at startup; startup still continues (SF-06).
  - SF-04 (soft-contract `None` returns on missing `chat_id`) and SF-05 (best-effort identity registration) were reviewed and confirmed as intentional, documented behavior — no change.

### Added

- **Titan Light** (`titan.light`) — an architectural knowledge layer that lets developers and tools query *why* Titan is shaped the way it is, built on top of `titan.timeline`. Deterministic, not a chatbot or LLM wrapper.
  - Four public functions: `search()`, `explain()`, `rules()`, `decisions()`.
  - Not exported from the package root — import explicitly via `from titan.light import ...`.
  - See [ADR-014](docs/decisions/014-architect-ai.md).

- **Performance Profiler** (`titan.profiler`) — measures wall time per update in a controlled environment, built on `feed_update()` + `titan.playground`. No Core modifications.
  - `profile_update(bot, fake_command("start"), n=100)` → `ProfilingSession` with `.summary()`.
  - See [ADR-013](docs/decisions/013-performance-profiler.md).

- **Message Links Protocol** — every message the bot sends now has a permanent, addressable identity.
  - `TitanMessageAddress` — a frozen dataclass representing a stable `https://t.me/{bot}/{id}` URL.
  - `TitanMessageIdentity` — mutable record tracking `titan_id`, `chat_id`, `telegram_message_id`, and deletion state.
  - `SqliteMessageStore` — lazy-initialized SQLite store at `.titan/links.db`; AUTOINCREMENT guarantees titan_ids are never reused.
  - `TitanMessageArchive` — optional archive entry (text, chat type, timestamp).
  - `LinksManager` — public API: `get_address_for_telegram_id()`, `get_address_for_titan_id()`, `mark_deleted()`, `enable_archive()`.
  - `/link` command auto-registered by Titan (reserved, not visible in `bot.commands`).
  - Identity registered only after a confirmed successful Telegram send — failures are never recorded.
  - See [ADR-008](docs/decisions/008-message-links-protocol.md).

- **Runtime Contract Validator** — invalid handler registrations now fail at decorator time, not at runtime.
  - `titan.validation` module with three public functions: `validate_handler()`, `validate_middleware()`, `validate_error_handler()`.
  - All registration points (`@bot.command`, `@bot.on`, `@bot.callback`, `@bot.middleware`, `@bot.error_handler`, and their `Router` equivalents) validate immediately.
  - `bot.include()` re-validates defensively to catch handlers injected directly into Router dicts.
  - Callable objects with `async __call__` are supported as first-class citizens.
  - Error messages are developer-oriented: state what is wrong, what was expected, and show the correct signature.
  - Architecture is designed for extension: adding new contract types (`job`, `filter`, `event_hook`) requires one call to the shared `_validate_contract()` internal function.
  - See [ADR-009](docs/decisions/009-runtime-contract-validator.md).

---

## [1.0.0a2] - 2026-07-18

Alpha patch release. No new features or architectural changes.
Fixes documentation and examples that described APIs incorrectly in 1.0.0a1.

### Fixed

- **README (Arabic & English) — Aliases section**: `bot.alias()` was documented but does not exist. Replaced with correct `AliasMap` usage from `titan.extras.alias` — import, register, and attach via `as_middleware()`. The multi-router sharing pattern is now shown explicitly.
- **README (Arabic & English) — Context actions**: `ctx.refresh_permissions()` corrected to `ctx.fetch_permissions()`.
- **`examples/moderation_bot.py`**: `ctx.refresh_permissions()` → `ctx.fetch_permissions()`, `ctx.can_delete` → `ctx.permissions.can_delete_messages`.

---

## [1.0.0a1] - 2026-07-01

First public alpha release.

The public API is stable and contract-frozen. This release is marked alpha
to allow real-world developer feedback before the final v1.0.0 tag.
No breaking changes are expected between this release and v1.0.0.

### Public API

- `Titan` — core bot class
- `Router` — code organization tool for splitting handlers across files
- `InlineKeyboard` / `InlineButton` — inline keyboard builder
- `TitanError` / `TelegramError` — error types

### Bot Methods

- `bot.on(event)` — raw event handler (fan-out, multiple handlers allowed)
- `bot.command(name)` — command handler (`"start"`, not `"/start"`)
- `bot.callback(data)` — inline button handler, keyed by `callback_data`
- `bot.middleware` — pre-handler middleware (linear, call `next()` once)
- `bot.alias(alias, target)` — optional naming layer for ctx methods
- `bot.include(router)` — merge a Router into the bot
- `bot.run()` / `bot.run_async()` — synchronous and async entrypoints
- `bot.telegram` — direct Telegram API adapter
- `bot.banned_users` — public `set[int]` for ban management
- `bot.offset` — current polling offset

### Context (`ctx`)

- Data: `user_id`, `chat_id`, `text`, `callback_data`, `callback_id`,
  `message_id`, `username`, `is_banned`, `new_members`, `left_member`,
  `sender`, `chat`, `message`, `raw`
- Actions: `reply()`, `send()`, `edit()`, `delete_message()`, `ban_user()`,
  `leave()`, `answer_callback()`, `refresh_permissions()`
- Models expose `.raw` and `.to_dict()` on `Message`, `Sender`, `Chat`

### Behaviors

- Long polling with exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s, reset on success
- Callback routing: `bot.callback(data)` takes priority, falls through to `bot.on("callback")`
- Semantic events (`new_member`, `left_member`) take priority over `on("message")`
- Duplicate command or callback_data registration raises `TitanError`
- Middleware is linear — single `next()` call, no return values, no branching
- Router does not support middleware, aliases, or nested include
- Guaranteed execution order per update: parse → is_banned → aliases → middleware → dispatch
- `on_offset` callback is synchronous; must not be a coroutine

### Known Sharp Edges

Two runtime issues are documented and will not be silently fixed in a patch:

- **`bot.include()` partial state** — if a Router contains event handlers and a
  conflicting command, event handlers are added before `TitanError` is raised.
  The mutation is not rolled back. Workaround: verify routing keys before calling
  `include()`.

- **`bot.callback("")` unreachable** — an empty string `callback_data` registers
  successfully but is never matched by the routing logic. Use a non-empty string.

Four missing safeguards are documented in README under "Known Sharp Edges":
calling `next()` twice, command names with a leading slash, duplicate
`error_handler` registration, and `InlineButton` with no action.
