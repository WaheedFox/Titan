# Models

**Primary question this document answers: what is a Model in Titan?**

---

## What a Model Is

A model in Titan:

- Represents a piece of reality that has already been discovered.
- Owns properties only — typed accessors over the underlying data.
- Does not manage lifecycle.
- Does not fetch, load, cache, or refresh data.
- Does not decide when or whether its own data is discovered.
- Does not store discovery state.

`Sender`, `Chat`, `Message`, `BotCapabilities`, `ChatPermissions` — each of
these wraps information that arrived from an authoritative source before the
model was constructed. The model's job begins after discovery ends.

---

## The Core Rule

**A model represents known facts.**
**Models describe reality. They do not manage discovery, loading, caching, fetching, or lifecycle.**

Once a model is created, it should be trustworthy. Every property exposed by
the model should already represent a known fact.

This is the reason for every constraint that follows. There is no `loaded` flag
because a trustworthy model cannot be partially loaded. There is no `fetch()`
because a trustworthy model does not hold data it has not yet retrieved. There
is no `None` inside a model's properties unless `None` is itself a known fact
about the data — not a gap in the discovery process. There is no "this value
might become correct later."

If a model cannot be trusted the moment it is constructed, it should not exist yet.

It does not represent the absence of facts.
If the required information has not been discovered yet, the model itself should not exist.

---

## What This Looks Like in Practice

When you hold a model, you hold a fact.

```python
# When ctx.sender exists, these are facts — unconditionally:
ctx.sender.id
ctx.sender.username
ctx.sender.is_bot

# When ctx.permissions exists, these are facts — unconditionally:
ctx.permissions.can_delete_messages
ctx.permissions.can_pin_messages
```

The absence of a fact is represented by the absence of the model, not by an
object that confesses its own incompleteness.

```python
# Correct signal for "we don't know yet":
ctx.permissions is None

# Not a model — a placeholder that borrowed a model's shape:
ctx.permissions.loaded == False
ctx.permissions.can_delete_messages == None   # unknown? or not fetched?
```

The future growth this rule prevents:

```python
# None of these belong on a model:
permissions.load()
sender.refresh()
chat.fetch()
message.resolve()
```

If a method like this appears on a model, the boundary is in the wrong place.
The method belongs on the surface that owns the context for discovery — `ctx`,
`bot`, or a service layer — not on the model.

---

## Where the Optional Lives

In Titan, the Optional lives at the boundary — on the surface that exposes the
model, not inside the model.

```python
ctx.sender: Sender | None              # boundary on ctx
ctx.chat: Chat | None                  # boundary on ctx
ctx.permissions: ChatPermissions | None  # boundary on ctx
bot.capabilities: BotCapabilities | None # boundary on bot
```

When the boundary is crossed — when the caller receives a model — all
uncertainty ends. The model carries no "loaded" flag. It carries facts.

This is why `sender.username` is `str | None` only when a username genuinely
may not exist for a given Telegram user — not because the field might not have
been fetched. An Optional inside a model reflects a real optionality in the
data. It never reflects a gap in the discovery process.

---

## Applying This Rule to Future Models

Before adding any new model, check:

1. **When does this object exist?** If the answer is "always, even before we
   have data," the discovery is incomplete. The model should not exist yet.

2. **Can every property be read unconditionally?** If any property needs a
   guard — `if loaded`, `if fetched`, `try/except` — the model is carrying
   undiscovered state and the boundary is in the wrong place.

3. **Who performs discovery?** The model receives already-discovered data. If
   the model needs to fetch or load anything to initialize itself, the
   responsibility belongs elsewhere.

If all three checks pass, the model is ready.

---

## See Also

- [concepts/ctx.md](ctx.md) — how `ctx` decides what to expose and when
- [decisions/003-capabilities.md](../decisions/003-capabilities.md) — the
  decision that formalized this rule through the Capabilities and Permissions
  models
