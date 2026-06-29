import pytest
from titan.update import Update


RAW_MESSAGE = {
    "update_id": 1,
    "message": {
        "message_id": 10,
        "text": "hello",
        "from": {"id": 99, "username": "ali", "first_name": "Ali"},
        "chat": {"id": 200, "type": "private"},
    },
}

RAW_CHANNEL = {
    "update_id": 2,
    "channel_post": {
        "message_id": 20,
        "text": "channel msg",
        "chat": {"id": 300, "type": "channel"},
    },
}

RAW_CALLBACK = {
    "update_id": 3,
    "callback_query": {
        "id": "cq1",
        "data": "yes",
        "from": {"id": 55, "username": "bob"},
        "message": {
            "message_id": 30,
            "chat": {"id": 400, "type": "group"},
        },
    },
}

RAW_NEW_MEMBER = {
    "update_id": 4,
    "message": {
        "message_id": 40,
        "chat": {"id": 500, "type": "supergroup"},
        "new_chat_members": [{"id": 77, "first_name": "Zaid"}],
    },
}

RAW_LEFT_MEMBER = {
    "update_id": 5,
    "message": {
        "message_id": 50,
        "chat": {"id": 500, "type": "supergroup"},
        "left_chat_member": {"id": 88, "first_name": "Sara"},
    },
}


class TestUpdateMessage:
    def test_is_message(self):
        u = Update(RAW_MESSAGE)
        assert u.is_message() is True
        assert u.is_channel_post() is False
        assert u.is_callback() is False

    def test_get_message_returns_message(self):
        u = Update(RAW_MESSAGE)
        assert u.get_message() == RAW_MESSAGE["message"]

    def test_text(self):
        u = Update(RAW_MESSAGE)
        assert u.text == "hello"

    def test_message_id(self):
        u = Update(RAW_MESSAGE)
        assert u.message_id == 10

    def test_user_id(self):
        u = Update(RAW_MESSAGE)
        assert u.user_id == 99

    def test_username(self):
        u = Update(RAW_MESSAGE)
        assert u.username == "ali"

    def test_chat_id(self):
        u = Update(RAW_MESSAGE)
        assert u.chat_id == 200

    def test_chat_type(self):
        u = Update(RAW_MESSAGE)
        assert u.chat_type == "private"

    def test_has_text(self):
        u = Update(RAW_MESSAGE)
        assert u.has_text() is True

    def test_to_dict(self):
        u = Update(RAW_MESSAGE)
        assert u.to_dict() == RAW_MESSAGE


class TestUpdateChannel:
    def test_is_channel_post(self):
        u = Update(RAW_CHANNEL)
        assert u.is_channel_post() is True
        assert u.is_message() is False
        assert u.is_callback() is False

    def test_get_message_returns_channel_post(self):
        u = Update(RAW_CHANNEL)
        assert u.get_message() == RAW_CHANNEL["channel_post"]

    def test_text(self):
        u = Update(RAW_CHANNEL)
        assert u.text == "channel msg"

    def test_chat_id(self):
        u = Update(RAW_CHANNEL)
        assert u.chat_id == 300

    def test_user_returns_none(self):
        u = Update(RAW_CHANNEL)
        assert u._user() is None
        assert u.user_id is None
        assert u.username is None


class TestUpdateCallback:
    def test_is_callback(self):
        u = Update(RAW_CALLBACK)
        assert u.is_callback() is True
        assert u.is_message() is False
        assert u.is_channel_post() is False

    def test_get_message_returns_callback_message(self):
        u = Update(RAW_CALLBACK)
        assert u.get_message() == RAW_CALLBACK["callback_query"]["message"]

    def test_user_from_callback(self):
        u = Update(RAW_CALLBACK)
        assert u.user_id == 55
        assert u.username == "bob"

    def test_chat_id(self):
        u = Update(RAW_CALLBACK)
        assert u.chat_id == 400

    def test_message_id(self):
        u = Update(RAW_CALLBACK)
        assert u.message_id == 30


class TestUpdateMemberEvents:
    def test_new_member_raw(self):
        u = Update(RAW_NEW_MEMBER)
        msg = u.get_message()
        assert msg.get("new_chat_members") == [{"id": 77, "first_name": "Zaid"}]

    def test_left_member_raw(self):
        u = Update(RAW_LEFT_MEMBER)
        msg = u.get_message()
        assert msg.get("left_chat_member") == {"id": 88, "first_name": "Sara"}


class TestUpdateEmpty:
    def test_empty_update(self):
        u = Update({"update_id": 99})
        assert u.is_message() is False
        assert u.is_channel_post() is False
        assert u.is_callback() is False
        assert u.get_message() is None
        assert u.text is None
        assert u.message_id is None
        assert u.user_id is None
        assert u.username is None
        assert u.chat_id is None
        assert u.chat_type is None
        assert u.has_text() is False

    def test_message_without_text(self):
        raw = {
            "update_id": 10,
            "message": {
                "message_id": 1,
                "chat": {"id": 1, "type": "private"},
            },
        }
        u = Update(raw)
        assert u.text is None
        assert u.has_text() is False
