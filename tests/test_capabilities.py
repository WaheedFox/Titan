import pytest
from unittest.mock import MagicMock
from titan.bot import Titan
from titan.models.capabilities import BotCapabilities


def make_bot_with_me(me: dict) -> Titan:
    bot = Titan("fake-token")
    bot._api._me = me
    return bot


class TestBotCapabilitiesBeforeStart:
    def test_capabilities_none_before_get_me(self):
        bot = Titan("fake-token")
        assert bot.capabilities is None


class TestBotCapabilitiesAfterStart:
    def test_capabilities_returns_bot_capabilities(self):
        bot = make_bot_with_me({"id": 1, "is_bot": True})
        assert isinstance(bot.capabilities, BotCapabilities)

    def test_capabilities_is_read_only(self):
        bot = Titan("fake-token")
        with pytest.raises(AttributeError):
            bot.capabilities = BotCapabilities({})

    def test_capabilities_reflects_cached_me(self):
        me = {
            "id": 1,
            "can_join_groups": True,
            "can_read_all_group_messages": False,
            "supports_inline_queries": True,
        }
        bot = make_bot_with_me(me)
        assert bot.capabilities.can_join_groups is True
        assert bot.capabilities.can_read_all_group_messages is False
        assert bot.capabilities.supports_inline_queries is True


class TestBotCapabilitiesModel:
    def test_can_join_groups_true(self):
        caps = BotCapabilities({"can_join_groups": True})
        assert caps.can_join_groups is True

    def test_can_join_groups_false(self):
        caps = BotCapabilities({"can_join_groups": False})
        assert caps.can_join_groups is False

    def test_can_join_groups_default_false(self):
        caps = BotCapabilities({})
        assert caps.can_join_groups is False

    def test_can_read_all_group_messages_true(self):
        caps = BotCapabilities({"can_read_all_group_messages": True})
        assert caps.can_read_all_group_messages is True

    def test_can_read_all_group_messages_default_false(self):
        caps = BotCapabilities({})
        assert caps.can_read_all_group_messages is False

    def test_supports_inline_queries_true(self):
        caps = BotCapabilities({"supports_inline_queries": True})
        assert caps.supports_inline_queries is True

    def test_supports_inline_queries_default_false(self):
        caps = BotCapabilities({})
        assert caps.supports_inline_queries is False

    def test_raw_preserved(self):
        raw = {"can_join_groups": True, "custom_field": "x"}
        caps = BotCapabilities(raw)
        assert caps.raw is raw

    def test_to_dict_returns_raw(self):
        raw = {"can_join_groups": True}
        caps = BotCapabilities(raw)
        assert caps.to_dict() == raw
