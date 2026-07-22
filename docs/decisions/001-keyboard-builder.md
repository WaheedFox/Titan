# 001 — Keyboard Builder

**Status:** Rejected

---

## Proposal

Add a `Keyboard` class in `titan.recipes` (or elsewhere) to provide a cleaner, more readable API for building inline keyboards — one that better matches the developer's mental model of "rows of buttons."

The motivation was that the existing `InlineKeyboard` API felt verbose and required thinking in builder state rather than in visual layout.

---

## Investigation

**Step 1 — Diagnose the real friction.**

The first question asked was: what is actually wrong with `InlineKeyboard`?

The investigation found that the documented canonical pattern was:

```python
InlineKeyboard()
.row()                              # always first — no visual meaning
.button("Yes", callback_data="yes")
.button("No", callback_data="no")
.row()
.button("Cancel", callback_data="cancel")
```

The initial `.row()` adds an empty list internally that is immediately filtered out in `to_dict()`. It changes nothing in the output. It is pure syntactic noise — required by the documented convention, not by the implementation.

The separator pattern (`.row()` called *between* buttons, not before them) already worked correctly:

```python
InlineKeyboard()
.button("Yes", callback_data="yes")
.button("No", callback_data="no")
.row()
.button("Cancel", callback_data="cancel")
```

This was confirmed by the existing test `test_button_without_row_auto_creates_row`.

**Step 2 — Identify the remaining gap.**

After the convention fix, one gap remained: the developer thinks in *rows as units* ("put Yes and No on the same row"), while the API builds incrementally (button by button with a separator).

The minimum change to close this gap would be:

```python
InlineKeyboard()
.row(InlineButton("Yes", callback_data="yes"), InlineButton("No", callback_data="no"))
.row(InlineButton("Cancel", callback_data="cancel"))
```

But `InlineButton(...)` is still a concept the developer should not need to hold in mind.

The next reduction would use tuples `("text", "callback_data")`:

```python
InlineKeyboard(
    [("Yes", "yes"), ("No", "no")],
    [("Cancel", "cancel")],
)
```

**Step 3 — Identify the hard limit.**

The tuple shorthand `("text", "callback_data")` is an implicit convention. It breaks at the first URL button:

```python
InlineKeyboard(
    [("Yes", "yes"), ("Open", ???)],   # how does url= fit here?
)
```

There is no clean extension. Mixing tuples with explicit `InlineButton` objects is inconsistent. Moving to dicts is more verbose than the original. Any compact notation for the mixed case introduces implicit rules that cannot be discovered without reading documentation.

The improvement would be partial: it works cleanly for callback-only keyboards, and breaks for anything else.

---

## Decision

**Rejected.**

The only real problem was a misleading documented convention — `.row()` presented as a row starter rather than a row separator. This was fixed in the docstring, reference docs, and all examples.

No new class or API was added. `InlineKeyboard` is unchanged.

The deeper gap (thinking in rows vs. building incrementally) cannot be closed without introducing implicit conventions that either break on edge cases or add syntax purely for aesthetics. Neither satisfies Titan's standard.

---

## Rule

**Fix documentation before adding API.**

When a readability problem is identified, the first question is: is this a problem with the API, or with how the API is documented and presented?

An API added to compensate for a poorly documented existing API is not justified. The documentation fix is cheaper, has no surface cost, and leaves no permanent residue in the project.

A new API is justified only when the limitation is in the implementation itself — not in its explanation.

---

## Alternatives Considered

**`.row(*buttons)` accepting `InlineButton` objects**

```python
InlineKeyboard()
.row(InlineButton("Yes", callback_data="yes"), InlineButton("No", callback_data="no"))
.row(InlineButton("Cancel", callback_data="cancel"))
```

Each `.row()` call becomes a complete unit. The code structure mirrors the layout.

Not chosen because: `InlineButton(...)` is a concept the developer should not need to hold in mind when thinking "put these buttons on a row." The verbosity moved from one place to another without reducing the cognitive distance.

---

**Constructor with tuple rows**

```python
InlineKeyboard(
    [("Yes", "yes"), ("No", "no")],
    [("Cancel", "cancel")],
)
```

Visually closest to the mental picture for callback-only keyboards.

Not chosen because: `("text", "callback_data")` is an implicit convention with no natural extension to URL buttons. A URL button in the same row has no clean representation in this format. The improvement would cover roughly 80% of cases and silently break the rest, which is worse than a consistent but slightly more verbose API.

---

## Consequences

**Gained:**
- No new surface to document, test, or maintain.
- No ambiguity about which builder to use — `InlineKeyboard` is the only one.
- The existing tests remain the full specification for keyboard behavior.

**Accepted constraint:**
- The gap between "thinking in rows" and "building incrementally" remains. A developer writing a multi-row keyboard must still think in terms of `.row()` separators rather than row units. This is a known limitation, consciously accepted over the alternative of an inconsistent shorthand.
