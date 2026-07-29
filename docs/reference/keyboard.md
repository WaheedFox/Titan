# Keyboard Reference

Reference for `InlineKeyboard` and `InlineButton` — Titan's two classes for building Telegram inline keyboards.

→ For handling button presses: [reference/events.md](events.md)
→ For attaching keyboards to messages: [reference/api.md](api.md)

---

## InlineKeyboard

A row-based builder for inline keyboards. All methods return `self`, so calls can be chained.

```python
from titan import InlineKeyboard
```

### `.row()`

Separates two groups of buttons into different rows. Returns `self`.

Call `.row()` **between** buttons, not before the first one. Buttons added before any `.row()` call automatically go on the first row.

### `.button(text, *, callback_data=None, url=None)`

Adds a button to the current row. Returns `self`.

| Parameter | Type | Description |
|---|---|---|
| `text` | `str` | Label displayed on the button |
| `callback_data` | `str \| None` | Payload sent to your bot when the button is pressed |
| `url` | `str \| None` | URL opened in the browser when the button is pressed |

A button should have either `callback_data` or `url`, not both. Telegram defines them as mutually exclusive — if both are provided, behaviour is determined by Telegram, not Titan.

### `.to_dict()`

Returns the keyboard as a `dict` in Telegram's `inline_keyboard` format. Empty rows are excluded from the output.

This method is called automatically when you pass the keyboard to `ctx.reply()` or `ctx.send()`. You do not need to call it manually.

---

## InlineButton

A single button. Normally created through `InlineKeyboard.button()` rather than directly.

```python
from titan import InlineButton
```

### `InlineButton(text, *, callback_data=None, url=None)`

| Parameter | Type | Description |
|---|---|---|
| `text` | `str` | Label displayed on the button |
| `callback_data` | `str \| None` | Payload sent to your bot when pressed |
| `url` | `str \| None` | URL opened when pressed |

### `.to_dict()`

Returns the button as a `dict`. Only keys with non-`None` values are included.

---

## Usage

Pass an `InlineKeyboard` instance to the `reply_markup` parameter of any send method.

```python
kb = (
    InlineKeyboard()
    .button("Yes", callback_data="confirm_yes")
    .button("No", callback_data="confirm_no")
    .row()
    .button("Documentation", url="https://example.com/docs")
)

await ctx.reply("Confirm?", reply_markup=kb)
```

`.row()` separates rows. It goes **between** groups of buttons, not before the first one.

---

## Patterns

**Single row of buttons**

```python
kb = InlineKeyboard().button("OK", callback_data="ok")
```

**Multiple rows**

```python
kb = (
    InlineKeyboard()
    .button("Option A", callback_data="a")
    .button("Option B", callback_data="b")
    .row()
    .button("Cancel", callback_data="cancel")
)
```

**URL button alongside a callback button**

```python
kb = (
    InlineKeyboard()
    .button("Open link", url="https://example.com")
    .button("Confirm", callback_data="confirm")
)
```
