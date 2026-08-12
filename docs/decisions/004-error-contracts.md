# 004 — Error Contracts

**Status:** Accepted

---

## Proposal

Define a consistent philosophy for how Titan surfaces failures to the developer.
Establish a classification for all methods that currently fail silently, and derive
a rule that governs any new error added to Titan in the future.

---

## Investigation

**Step 1 — What problem does this solve?**

Titan has two categories of failure that are not handled consistently:

1. **Silent primary actions.** Seven methods in `ctx` return `None` without
   executing when a precondition is absent (`chat_id is None`,
   `callback_id is None`, etc.). A developer who calls `ctx.reply("hello")` in a
   context where `chat_id` is absent gets no message sent and no indication that
   anything went wrong. The return value is `None` in both the success and no-op
   paths, making them indistinguishable.

2. **Inconsistent context enforcement.** `ctx.edit()` raises `TitanError` when
   called outside a callback context. `ctx.answer_callback()`, which has the
   identical context requirement, returns `None` silently. The rule is applied in
   one place and ignored in another.

**Step 2 — What is the real problem?**

The problem is not that failures happen. The problem is that **silent return
corrupts the developer's model of what occurred.**

When `ctx.reply()` silently returns `None`, the developer's reasonable assumption
— that calling `ctx.reply()` sends a message — is false, and there is no signal
to correct it. This violates Titan's Principle 3 (explicit over implicit): the
framework acted without the developer's knowledge.

**Step 3 — Can all silent failures be resolved by raising?**

No. The classification requires distinguishing three fundamentally different
situations:

**A — Hard Contract violation.**
The developer called a method that is semantically bound to a single context, in a
context where it can never be correct. There is no legitimate path through Titan's
API that leads to this call being valid.

Example: calling `ctx.answer_callback()` outside a callback handler. A developer
registers `@bot.callback("data")` or `@bot.on("callback")` — both of which
guarantee a callback context. Reaching `ctx.answer_callback()` with
`callback_id is None` requires either a programming error or deliberate misuse.

Correct behavior: **raise `TitanError` immediately** with a message that names the
violated context requirement and, where one exists, the correct alternative.

**B — Soft Contract failure.**
The method is general — it works across multiple context types — and the missing
precondition is impossible in Titan's *current* update model but may become
legitimate as Titan grows.

Example: `ctx.reply()` requires `chat_id`. Today, every update type that reaches
a registered handler has a chat_id. This condition cannot fail in any current
Titan bot. However, if Titan adds support for inline queries, poll answers, or
other non-chat update types in the future, a developer may legitimately call
`ctx.reply()` from a shared handler that handles both chat and non-chat updates.

Raising here would break future-compatible code. Staying silent violates the
explicit-over-implicit principle. The correct behavior: **log a warning** that
identifies the method and the missing precondition, then return without executing.
The warning is visible during development, disappears when the developer guards
the call, and does not crash code that may be valid in a future update context.

**C — Best-effort side effect.**
The method produces a cosmetic or supplementary effect that does not change the
user-facing outcome of the bot. The developer does not build logic on whether the
call succeeded.

Example: `ctx.typing()`. Whether or not the typing indicator appears, the bot's
response is identical. No message is lost. No action is skipped.

Correct behavior: **silent no-op.** No log, no warning, no exception.

**Step 4 — How is the classification determined?**

Three questions, applied in order:

**Q1. Can the developer reach this condition through correct use of the API?**

If NO — the call is always wrong. → Hard Contract → raise.
If YES (or possibly yes in future Titan versions) → continue to Q2.

**Q2. Does failure change the user-facing outcome?**

If YES — a message was not sent, an action was not taken, the user experienced
something different from what the developer intended. → Soft Contract → warn.
If NO — failure has no user-facing consequence. → Best-Effort → silent.

**Q3 (verification). Is this a primary action or a side effect?**

Primary actions (reply, send, delete, ban, leave) must answer YES to Q2. If they
answer NO, the classification is wrong.
Side effects (typing, future: status updates, analytics pings) may answer NO.

---

## Decision

### Classification of all currently silent ctx methods

| Method | Failing condition | Classification | Behavior |
|--------|------------------|----------------|----------|
| `ctx.answer_callback()` | `callback_id is None` | Hard Contract | raise `TitanError` |
| `ctx.edit()` | no `callback_query` | Hard Contract | raise `TitanError` ✓ already correct |
| `ctx.reply()` | `chat_id is None` | Soft Contract | log warning, return `None` |
| `ctx.send()` | `chat_id is None` | Soft Contract | log warning, return `None` |
| `ctx.delete_message()` | `chat_id` or `message_id` is `None` | Soft Contract | log warning, return `None` |
| `ctx.ban_user()` | resolved `target_user` is `None` | Soft Contract | log warning, return `None` |
| `ctx.leave()` | `chat_id is None` | Soft Contract | log warning, return `None` |
| `ctx.typing()` | `chat_id is None` | Best-Effort | silent no-op ✓ already correct |

### Contract for TitanError

`TitanError` is raised when the developer violates the API contract of Titan
itself. The violation is always a programming error — not a network issue, not a
Telegram restriction, not a runtime edge case.

Every `TitanError` message must answer three things:

1. **What the developer did** — the method called and the condition that was
   violated. Named explicitly: `ctx.answer_callback()`, `Command 'start'`, etc.
2. **The rule that was violated** — stated as a constraint, not an apology.
   "This method requires an active callback_query context."
3. **The alternative, if and only if one exists and is specific.** A vague
   alternative ("try something else") is worse than no alternative. An alternative
   is included only when Titan can name it precisely.

`TitanError` does **not** carry structured attributes beyond the message string
(no `.code`, no `.method` field). The error is a diagnostic for a human reading a
traceback, not a value to be processed by application logic.

### Contract for TelegramError

`TelegramError` is raised when Telegram's API rejects a request or when the
network makes communication impossible.

`TelegramError` is a subclass of `TitanError`. A developer who catches
`TitanError` catches both. A developer who wants to handle only Telegram-level
failures catches `TelegramError`.

Every `TelegramError` message must carry:
- The API method that was called (`sendMessage`, `editMessageText`, etc.)
- Telegram's `description` field verbatim
- Telegram's `error_code`

`TelegramError` does **not** invent subclasses per error code or per error string.
The error hierarchy stops at two levels: `TitanError` → `TelegramError`. Adding
a class per Telegram error string (Pyrogram's approach) multiplies API surface
without reducing debugging effort.

---

## Rule

> **Titan declares contract violations at a level proportional to how impossible
> the violation is.**
>
> - A violation that is **always wrong** → Exception.
> - A violation that is **currently impossible but may become valid** → Warning.
> - An absence that is **expected and inconsequential** → Silent.
>
> Every new error in Titan is classified by three questions:
> 1. Can the developer reach this condition through correct use of the API?
> 2. Does the failure change the user-facing outcome?
> 3. Is this a primary action or a side effect?

---

## Alternatives Considered

**Raise everywhere — any `None` precondition raises `TitanError`.**

Rejected. A handler that registers for multiple update types (e.g. both chat
messages and inline queries in a future Titan version) would crash at runtime on
any update type that lacks `chat_id`. Raising is appropriate when the call is
always wrong; it is too strong when the precondition might legitimately be absent.

**Remain silent everywhere — status quo.**

Rejected. Silent return from primary actions (`ctx.reply()`, `ctx.send()`, etc.)
corrupts the developer's model of what occurred. A message not sent without notice
is a framework lying to the developer.

**Subclass TelegramError per HTTP status code (PTB approach).**

Partially adopted. PTB's insight — that 401 Unauthorized and 429 Too Many
Requests deserve different handling than 400 Bad Request — is valid. However,
Titan does not add subclasses at this time. The error_code is already present in
the message string, which is sufficient for a developer reading a traceback. If
Titan later adds rate-limit handling or retry logic, a `RetryAfterError` subclass
with a `.retry_after` attribute would be warranted at that point.

---

## Consequences

**Gained:**
- Every primary action that does not execute produces a visible signal.
- `ctx.answer_callback()` behavior becomes consistent with `ctx.edit()`.
- Future contributors have a classification rule, not a case-by-case judgment.

**Constraints accepted:**
- Soft Contract warnings require a logger. Titan uses `logging.getLogger("titan")`
  already. No new logging infrastructure is introduced.
- The two-level exception hierarchy (`TitanError` → `TelegramError`) is frozen.
  New subclasses require a separate ADR.

---

## Scope of Feature #5

### In scope

1. `ctx.answer_callback()` — convert from silent `None` to Hard Contract raise,
   matching the existing behavior of `ctx.edit()`.

2. Soft Contract warning in all primary ctx action methods when their precondition
   is absent: `ctx.reply()`, `ctx.send()`, `ctx.delete_message()`,
   `ctx.ban_user()`, `ctx.leave()`.

3. Improve two existing error messages that are currently misleading:
   - Non-JSON response in `telegram.py` — remove the incorrect "invalid bot token"
     suggestion (a bad token returns valid JSON; a non-JSON response is always a
     network issue).
   - Command/callback conflict during `bot.include()` — identify whether the
     original registration came from a direct `@bot.command()` call or a
     previously included router.

4. Write tests for every new raise and warning.

### Deferred

- `TelegramError` subclassing per HTTP status code. No current use case requires
  programmatic differentiation.
- Changes to the polling error loop in `bot.run()` (401 Unauthorized retry
  behavior). Real but out of scope for this ADR. Candidate for a future
  operational-behavior ADR.
- Any expansion of the logging infrastructure beyond `logging.getLogger("titan")`.
- Changes to `TelegramError` message format. Current format (method + description
  + error_code) is sufficient. Enhancement is warranted only when a specific
  diagnosed pain case requires it.
