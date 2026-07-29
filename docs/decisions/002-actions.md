# 002 — Actions

**Status:** Accepted

---

## Proposal

Add an Action concept to Titan — a category of ctx-bound operations that signal
something on behalf of the bot, distinct from sending a message or returning data
to the developer.

The first Action (`ctx.typing()`) was implemented to validate the concept.

---

## Investigation

**Step 1 — What problem do Actions solve?**

`ctx` methods today perform operations and return results the developer uses:
`reply()` returns the sent message, `send()` returns the sent message, `ban_user()`
returns the API response.

There is a different kind of operation: something the bot does not for the
developer's code, but for the user's experience or Telegram's representation of
the bot. These operations have no meaningful return value. They are side effects
the developer initiates but does not consume.

Without a clear category, these operations would be added to `ctx` with no
distinguishing structure — just more methods that happen to return nothing.

**Step 2 — What already exists in Core?**

`telegram.py` had no `send_chat_action` method. `ctx` had no way to signal
activity to Telegram at all. This was a genuine gap.

The fix required:
1. `send_chat_action(chat_id, action)` in `telegram.py`
2. `TypingAction` class + `ctx.typing()` method in `ctx.py`

**Step 3 — How does this fit alongside existing ctx methods?**

Existing ctx methods are direct calls: perform an operation, return a result.

The new category is different in character: the developer initiates it not to
get something back, but to signal something. The distinction is conceptual before
it is structural.

---

## Decision

**Accepted.**

Actions are defined as a concept (see below). `ctx.typing()` is the first
Action implemented — its specific form (async context manager) is the appropriate
shape for that particular behavior, not a requirement of the concept itself.

---

## The Action Concept

**An Action is a ctx-bound operation that signals something on behalf of the bot
— to the user, to Telegram, or to the interaction — without returning data the
developer uses.**

Three properties distinguish an Action from other ctx methods:

1. **ctx-bound** — an Action is always a method on `ctx`. It cannot exist without
   a live interaction context (chat_id, api access). It is never a standalone
   utility or an importable class.

2. **Effect without result** — an Action changes how the bot is perceived or what
   it communicates. It does not produce a value the calling code depends on.
   The developer initiates it and moves on.

3. **Not a message** — an Action does not send a message to the chat. Sending a
   message (`reply`, `send`) is a direct call. An Action is something else the
   bot does alongside or instead of speaking.

---

## Implementation Shape

The concept does not prescribe a shape.

Each Action has a behavior. That behavior has a natural expression in code. The
shape follows from the behavior — not from the concept, and not from precedent.

Ask: *what does this Action do in time?*

- Does it hold a state *during* an operation? A context manager expresses that.
- Does it signal something at a single point in time? A direct `await` call expresses that.
- Does it configure something that takes effect immediately? A plain call expresses that.

The right shape for any given Action is the one that makes its behavior legible
at the call site. The fact that `ctx.typing()` uses an async context manager is a
consequence of what typing *is* — a temporary state. It is not a template.

Future Actions must derive their shape from their own behavior, independently of
what came before.

---

## What qualifies as an Action

An operation qualifies as an Action if:
- it is meaningfully expressed through `ctx` (requires chat context),
- it signals something to Telegram or the user rather than returning data,
- and it is not a message.

Operations that send messages (`reply`, `send`) are not Actions — they are direct
calls with results. Operations that return API data the developer uses are not
Actions. Standalone utilities with no chat context are not Actions.

---

## Rule

**An Action is a ctx-bound signal that affects how the bot is perceived or what
it communicates — not a message, not a result, and not a standalone utility.**

The implementation shape (context manager, direct call, or other) follows from
the behavior of the specific Action. It is not part of the definition.

---

## ctx.typing() — A Concrete Implementation

`ctx.typing()` is one Action that has been implemented. Its shape — an async
context manager — follows from its specific behavior: "typing" is a temporary UI
state that exists *during* an operation, and a context manager expresses that
temporal relationship directly. This shape was chosen for `ctx.typing()`. It was
not chosen for Actions in general.

The contract below governs this implementation only. Each future Action documents
its own shape and the reason that shape was chosen.

### Contract

Since `ctx.typing()` is implemented as an async context manager, its specific
behavior is governed by these rules:

1. `__aenter__` sends the signal (`sendChatAction`).
2. `__aexit__` is a no-op — Telegram expires the signal automatically.
3. Exceptions inside the block always propagate — `__aexit__` never returns `True`.
4. If `chat_id` is `None`, no API call is made and no exception is raised.
5. The internal class (`TypingAction`) is not exported — the developer only uses `ctx.typing()`.

These rules belong to this implementation, not to the Action concept itself.

---

## Alternatives Considered

**A standalone `Action` base class for inheritance**

Not chosen. Inheritance would add a visible concept (`Action` base class) that
the developer never needs to see or use. The concept is on `ctx`; the
implementation is internal.

**A single `ctx.action(name)` method**

```python
async with ctx.action("typing"):
    ...
```

Not chosen. The action name becomes a magic string, not discoverable through
autocomplete. `ctx.action("flying")` would fail silently at runtime.
`ctx.typing()` fails at definition time (NameError or AttributeError).

---

## Consequences

**Gained:**
- A clear conceptual boundary for a category of ctx operations that previously
  had no name.
- Implementation shape is determined by behavior, not by category membership.
  Future Actions are not forced into context manager form.
- `ctx` remains the sole surface for the developer — no new imports.

**Accepted constraint:**
- `ctx.typing()` sends the signal once at block entry. Telegram displays it for
  approximately 5 seconds. For operations longer than 5 seconds, the signal
  expires before the work completes. Refreshing the signal would require a loop —
  this is outside the scope of this implementation.
