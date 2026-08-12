# 003 — Capabilities

**Status:** Accepted

---

## Proposal

Add a Capabilities system to Titan — a way for the developer to explicitly
discover what the bot is able to do, at both the account level and the per-chat
level.

---

## Investigation

**Step 1 — What problem does this solve?**

Titan exposed one capability: `ctx.can_delete`, populated by `ctx.refresh_permissions()`.
The implementation had three problems:

1. `getChatMember` returns ~11 permission flags. Only `can_delete_messages` was
   extracted. The rest were silently discarded.

2. `refresh_permissions()` swallowed all exceptions and returned `False`.
   `ctx.can_delete = False` was ambiguous: it could mean the bot lacked the
   permission, the API call failed, or the bot was not an admin. The developer
   could not distinguish these cases.

3. Bot-level capabilities from `getMe` (`can_join_groups`,
   `can_read_all_group_messages`, `supports_inline_queries`) were never exposed
   despite being already cached in `Telegram._me` after startup.

**Step 2 — What is a Capability?**

A Capability is a discoverable property of the bot that describes what it is
able to do. Three conditions must hold simultaneously:

- It concerns the bot itself — not the user, not the chat, not the developer.
- It describes an ability — not identity, not runtime state, not configuration.
- It is discovered from an external source — Telegram API or a real constraint
  it reflects, not a developer decision.

**Step 3 — How many categories of Capabilities exist?**

Two categories, differing on two axes:

| | Stable | Dynamic |
|---|---|---|
| **Global (bot-level)** | `can_join_groups`, `supports_inline_queries` | — |
| **Contextual (per-chat)** | — | `can_delete_messages`, `can_pin_messages`, … |

Global capabilities: from `getMe`, stable, independent of any update or chat.
Contextual capabilities: from `getChatMember`, dynamic, per-chat, require an
explicit discovery step.

**Step 4 — Where does each category belong?**

The decisive question: does this capability have any relationship to the current
update?

Global capabilities: no. `supports_inline_queries` is the same regardless of
which message triggered the handler, which chat it came from, or which user sent
it. It belongs on `bot`, not `ctx`.

Contextual capabilities: yes. They depend on which chat the update came from.
They belong on `ctx`.

`docs/concepts/ctx.md` already establishes this boundary explicitly:
> "ctx covers what belongs to the update-response cycle. It does not cover
> operations that have no relationship to the current update."

---

## Decision

**Accepted.**

Two surfaces. One concept. Ownership follows scope.

**`bot.capabilities`** exposes what is currently known about the bot's account-level
abilities. It returns a typed model when that information is available, and `None`
when it is not. It never fetches silently and it makes no promise about availability.
The property is lazy: it reflects the current state of cached information, nothing
more. Whether that cache was populated a moment ago or has never been populated is
not the property's concern.

**`ctx.permissions`** starts as `None` and represents per-chat permission information
scoped to the current update's chat. Populating it requires an explicit discovery
step initiated by the developer. That step must raise on failure — missing `chat_id`
raises `TitanError`; API failure propagates `TelegramError`. No silent swallowing.

The current method name (`fetch_permissions`) is an implementation detail. The
architectural requirement is: discovery is explicit, initiated by the developer,
and failure is never hidden. The method name may change. The requirement does not.

---

## The Constraint

Capabilities are read-only, query-oriented, and non-interactive.

- A Capability is never something you "refresh for correctness."
- A Capability is never something that changes behavior inside a handler.
- A Capability is never a trigger for side effects.
- A Capability is only something you inspect to make decisions.

**`ChatPermissions` is a model, not a service.**

Its responsibility is to represent discovered permissions. It holds data. It does
not perform discovery. Discovery belongs to `ctx`. If a future feature requires
re-discovery, the method that triggers it belongs on `ctx`, not on
`ChatPermissions`.

---

## Rule

**Ownership follows scope.**

If a capability is global (independent of the current update or chat), it belongs
on `bot`. If a capability is contextual (depends on the current chat or update),
it belongs on `ctx`.

The scope axis of the two-axis model (scope × stability) is the direct
determinant of ownership. The stability axis determines discovery cost and caching
strategy, not ownership.

**The two surfaces are intentionally asymmetric.**

`bot.capabilities` and `ctx.permissions` are different concepts. They have
different lifecycles, different discovery costs, and different relationships to the
current update. Forcing them to mirror each other — same API shape, same naming
convention, same access pattern — would produce artificial symmetry. Different
concepts are allowed to have different APIs.

---

## Philosophy

Feature #4 is not about exposing every Telegram permission field. It is about
exposing discovered capabilities through proper models while preserving ownership
boundaries.

The architecture is the primary deliverable. The implementation demonstrates the
architecture. The specific set of exposed fields is a consequence of the models
chosen, not an objective in itself.

---

## Alternatives Considered

**Always-present objects with internal discovery state**

Make `bot.capabilities` and `ctx.permissions` always return an object, never
`None`. Represent whether discovery has occurred inside the model — via a
`loaded: bool` property, `bool | None` per-property types, or an exception raised
on access before discovery.

The only tangible benefit is a cleaner call site:
`bot.capabilities.can_join_groups` instead of
`bot.capabilities and bot.capabilities.can_join_groups`.

Not chosen. The benefit does not survive contact with the three concrete forms:

| Form | `can_join_groups` before discovery | Problem |
|---|---|---|
| Per-property `bool \| None` | `None` | Every property becomes Optional — `None` now appears at two levels simultaneously |
| Per-property default `False` | `False` | Silent lie — indistinguishable from "the bot genuinely cannot join groups"; this is the same flaw that made `ctx.can_delete` broken |
| Raise on access | Exception | The same guard is still required; the developer catches an exception instead of checking `None` — a less idiomatic and less obvious form of the same signal |

In every form, the question "is this information available?" must still be answered
before using the value. The always-present object does not eliminate this question;
it only moves it inside the model.

The deeper reason is Titan's core modeling rule:

> A model represents known facts. It does not represent the absence of facts.
> If the required information has not been discovered yet, the model itself
> should not exist.

→ [concepts/models.md](../concepts/models.md)

`bot.capabilities` and `ctx.permissions` return `None` — not an empty
`BotCapabilities()` or an unloaded `ChatPermissions()` — because the
appropriate signal for "this fact is not yet known" is the absence of the
object, not an object that confesses its own incompleteness. The Optional lives
at the boundary (`bot`, `ctx`), not inside the model.

**Flat expansion on ctx**

Add `ctx.can_pin`, `ctx.can_ban`, etc. as direct fields alongside `ctx.can_delete`.

Not chosen. Ten-plus `None` fields on `ctx` until a single method is called
creates a large dead zone on a surface designed to be direct and ready-to-use.
Permission fields mixed with message data fields on the same object also blurs
the responsibility of `ctx`.

**ctx as unified access point for all capabilities**

Surface global capabilities via `ctx` (lazily, from cached `getMe`) alongside
contextual permissions, so the developer only needs one access point.

Not chosen. It violates the documented boundary of `ctx`: global capabilities
have no relationship to the current update. Placing them on `ctx` would make
`ctx` a general-purpose query object rather than an update-response scope object.
It also makes global capabilities unavailable outside handler context (e.g., at
startup or in background tasks).

---

## Consequences

**Gained:**
- All 11 per-chat permission flags exposed, not just one.
- Bot-level capabilities exposed through the appropriate surface (`bot`).
- Failures in the permissions discovery step propagate explicitly — no ambiguous `False`.
- Two new typed models consistent with the existing `Sender`, `Chat`, `Message` pattern.
- `ChatPermissions` constrained to representation; discovery responsibility stays on `ctx`.

**Removed:**
- `ctx.can_delete` — replaced by `ctx.permissions.can_delete_messages`.
- `ctx.refresh_permissions()` — replaced by an explicit discovery step on `ctx`.

**Accepted constraints:**
- `ctx.permissions` is `None` until the developer explicitly discovers it. The
  developer must initiate discovery when per-chat permission information is needed.
- `bot.capabilities` reflects current knowledge only. It returns `None` when no
  information is available, without fetching or promising that information will appear.
- The name of the permissions discovery method is not locked. The architectural
  requirement (explicit, developer-initiated, never-silent) is locked.
