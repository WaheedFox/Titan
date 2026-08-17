import pytest
from titan.errors import TitanError
from titan.keyboard import InlineButton, InlineKeyboard


class TestInlineButton:
    def test_callback_data_only(self):
        btn = InlineButton("Click", callback_data="yes")
        d = btn.to_dict()
        assert d == {"text": "Click", "callback_data": "yes"}

    def test_url_only(self):
        btn = InlineButton("Link", url="https://example.com")
        d = btn.to_dict()
        assert d == {"text": "Link", "url": "https://example.com"}

    def test_no_action_is_rejected(self):
        with pytest.raises(TitanError, match="exactly one action"):
            InlineButton("Plain")

    def test_both_actions_are_rejected(self):
        with pytest.raises(TitanError, match="exactly one action"):
            InlineButton("Both", callback_data="cb", url="https://x.com")


class TestInlineKeyboard:
    def test_single_row_single_button(self):
        kb = InlineKeyboard().row().button("OK", callback_data="ok")
        d = kb.to_dict()
        assert d == {
            "inline_keyboard": [
                [{"text": "OK", "callback_data": "ok"}]
            ]
        }

    def test_single_row_multiple_buttons(self):
        kb = (
            InlineKeyboard()
            .row()
            .button("Yes", callback_data="yes")
            .button("No", callback_data="no")
        )
        d = kb.to_dict()
        assert len(d["inline_keyboard"]) == 1
        assert len(d["inline_keyboard"][0]) == 2
        assert d["inline_keyboard"][0][0]["callback_data"] == "yes"
        assert d["inline_keyboard"][0][1]["callback_data"] == "no"

    def test_multiple_rows(self):
        kb = (
            InlineKeyboard()
            .row()
            .button("A", callback_data="a")
            .row()
            .button("B", callback_data="b")
        )
        d = kb.to_dict()
        assert len(d["inline_keyboard"]) == 2
        assert d["inline_keyboard"][0][0]["callback_data"] == "a"
        assert d["inline_keyboard"][1][0]["callback_data"] == "b"

    def test_button_without_row_auto_creates_row(self):
        kb = InlineKeyboard().button("X", callback_data="x")
        d = kb.to_dict()
        assert len(d["inline_keyboard"]) == 1
        assert d["inline_keyboard"][0][0]["callback_data"] == "x"

    def test_empty_rows_excluded_from_output(self):
        kb = InlineKeyboard().row().row().button("Z", callback_data="z")
        d = kb.to_dict()
        assert len(d["inline_keyboard"]) == 1

    def test_url_button_in_keyboard(self):
        kb = InlineKeyboard().row().button("Link", url="https://example.com")
        d = kb.to_dict()
        assert d["inline_keyboard"][0][0]["url"] == "https://example.com"

    def test_builder_rejects_button_without_action(self):
        kb = InlineKeyboard()
        with pytest.raises(TitanError, match="exactly one action"):
            kb.button("Broken")
        assert kb.to_dict() == {"inline_keyboard": []}

    def test_builder_rejects_button_with_both_actions(self):
        kb = InlineKeyboard()
        with pytest.raises(TitanError, match="exactly one action"):
            kb.button("Ambiguous", callback_data="cb", url="https://x.com")
        assert kb.to_dict() == {"inline_keyboard": []}

    def test_empty_keyboard(self):
        kb = InlineKeyboard()
        d = kb.to_dict()
        assert d == {"inline_keyboard": []}

    def test_row_returns_self(self):
        kb = InlineKeyboard()
        assert kb.row() is kb

    def test_button_returns_self(self):
        kb = InlineKeyboard().row()
        assert kb.button("X", callback_data="x") is kb
