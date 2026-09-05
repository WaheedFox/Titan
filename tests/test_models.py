import pytest
from titan.models.chat import Chat
from titan.models.message import Message
from titan.models.rich_message import RichMessage
from titan.models.sender import Sender


class TestChat:
    def test_properties(self):
        raw = {"id": 100, "type": "supergroup", "title": "MyGroup", "username": "mygroup"}
        c = Chat(raw)
        assert c.id == 100
        assert c.type == "supergroup"
        assert c.title == "MyGroup"
        assert c.username == "mygroup"

    def test_is_group_supergroup(self):
        assert Chat({"type": "supergroup"}).is_group() is True
        assert Chat({"type": "group"}).is_group() is True

    def test_is_group_false(self):
        assert Chat({"type": "private"}).is_group() is False
        assert Chat({"type": "channel"}).is_group() is False

    def test_is_private(self):
        assert Chat({"type": "private"}).is_private() is True
        assert Chat({"type": "group"}).is_private() is False

    def test_to_dict(self):
        raw = {"id": 1, "type": "private"}
        assert Chat(raw).to_dict() == raw

    def test_none_raw(self):
        c = Chat(None)
        assert c.id is None
        assert c.type is None
        assert c.title is None
        assert c.username is None
        assert c.is_group() is False
        assert c.is_private() is False
        assert c.to_dict() == {}

    def test_missing_fields(self):
        c = Chat({"id": 5})
        assert c.type is None
        assert c.title is None
        assert c.username is None


class TestMessage:
    def test_properties(self):
        raw = {
            "message_id": 42,
            "text": "hello",
            "chat": {"id": 99, "type": "private"},
        }
        m = Message(raw)
        assert m.id == 42
        assert m.text == "hello"
        assert m.chat_id == 99

    def test_to_dict(self):
        raw = {"message_id": 1, "text": "test"}
        assert Message(raw).to_dict() == raw

    def test_none_raw(self):
        m = Message(None)
        assert m.id is None
        assert m.text is None
        assert m.chat_id is None
        assert m.to_dict() == {}

    def test_no_chat(self):
        m = Message({"message_id": 1})
        assert m.chat_id is None

    def test_no_text(self):
        m = Message({"message_id": 1, "chat": {"id": 1}})
        assert m.text is None

    def test_rich_message(self):
        raw_rich = {"blocks": [{"future_field": {"enabled": True}}]}
        raw = {
            "message_id": 7,
            "chat": {"id": 9},
            "rich_message": raw_rich,
        }
        message = Message(raw)

        assert isinstance(message.rich_message, RichMessage)
        assert message.rich_message.raw is raw_rich
        assert message.rich_message.mode == "blocks"
        assert message.text is None
        assert message.id == 7
        assert message.chat_id == 9
        assert message.to_dict() is raw

    def test_no_rich_message(self):
        assert Message({"message_id": 1}).rich_message is None

    def test_none_rich_message(self):
        assert Message({"rich_message": None}).rich_message is None


class TestRichMessage:
    def test_raw_mode_and_to_dict(self):
        raw = {
            "blocks": [{"unknown": {"kept": True}}],
            "is_rtl": True,
            "future_field": {"nested": ["value"]},
        }
        message = RichMessage(raw)

        assert message.raw is raw
        assert message.mode == "blocks"
        assert message.raw["is_rtl"] is True
        assert message.raw["future_field"] == {"nested": ["value"]}
        assert message.to_dict() is raw

    def test_outgoing_input_shapes_are_not_inferred_as_incoming_modes(self):
        assert RichMessage({"html": "<b>Hello</b>"}).mode is None
        assert RichMessage({"markdown": "**Hello**"}).mode is None

    def test_unknown_incoming_shape_has_unknown_mode(self):
        assert RichMessage({"future_field": {"value": 1}}).mode is None


class TestSender:
    def test_properties(self):
        raw = {"id": 7, "username": "ali", "first_name": "Ali", "last_name": "Hassan"}
        s = Sender(raw)
        assert s.id == 7
        assert s.username == "ali"
        assert s.first_name == "Ali"
        assert s.last_name == "Hassan"

    def test_to_dict(self):
        raw = {"id": 1, "username": "x"}
        assert Sender(raw).to_dict() == raw

    def test_none_raw(self):
        s = Sender(None)
        assert s.id is None
        assert s.username is None
        assert s.first_name is None
        assert s.last_name is None
        assert s.to_dict() == {}

    def test_partial_fields(self):
        s = Sender({"id": 5, "first_name": "Omar"})
        assert s.id == 5
        assert s.first_name == "Omar"
        assert s.username is None
        assert s.last_name is None
