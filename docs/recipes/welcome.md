# Recipe: Welcome

**Primary question this document answers: what is the recommended pattern for greeting new group members?**

---

## The Pattern

```python
from titan import Titan
from titan.recipes import Welcome

bot = Titan("YOUR_TOKEN")
welcome = Welcome("Welcome to the group, {name}!")

@bot.on("new_member")
async def on_join(ctx):
    await welcome(ctx)

bot.run()
```

---

## What This Pattern Uses

This recipe composes three things from the Titan Core:

**`@bot.on("new_member")`** — the event that fires when one or more users join a group. This is the correct hook for any welcome logic.

**`ctx.new_members`** — the list of users who joined in this update. Available on `ctx` inside any `new_member` handler.

**`ctx.send()`** — sends a standalone message to the group. A welcome message is an announcement — it belongs to the group conversation, not to any specific message. This is why the recipe uses `ctx.send()` and not `ctx.reply()`.

---

## Template Variables

| Variable | Value |
|---|---|
| `{name}` | Member's first name, or `"there"` if unavailable |

```python
Welcome("Welcome, {name}!")             # default
Welcome("Glad you're here, {name}!")    # custom
Welcome("A new member has joined!")     # no {name} — valid
```

---

## When to Go Beyond the Recipe

The recipe covers the standard case. When you need more, use the same Core directly:

```python
@bot.on("new_member")
async def on_join(ctx):
    await welcome(ctx)
    await ctx.send("Please read the rules: t.me/your_rules_link")
```

Or skip the recipe entirely and write the handler yourself using `ctx.new_members` and `ctx.send()`.

→ For `ctx.new_members` and `ctx.send()` reference: [reference/api.md](../reference/api.md)
→ For the `new_member` event: [reference/events.md](../reference/events.md)
