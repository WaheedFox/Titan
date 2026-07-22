"""
اختبارات TitanMessageAddress — وحدة الهوية الأساسية.
"""

import pytest
from titan.links.address import TitanMessageAddress


class TestTitanMessageAddress:
    def test_str_format(self):
        addr = TitanMessageAddress(bot_username="MyBot", titan_id=482)
        assert str(addr) == "https://t.me/MyBot/482"

    def test_str_format_titan_id_one(self):
        addr = TitanMessageAddress(bot_username="AliceBot", titan_id=1)
        assert str(addr) == "https://t.me/AliceBot/1"

    def test_repr(self):
        addr = TitanMessageAddress(bot_username="MyBot", titan_id=482)
        r = repr(addr)
        assert "TitanMessageAddress" in r
        assert "MyBot" in r
        assert "482" in r

    def test_equality(self):
        a = TitanMessageAddress(bot_username="MyBot", titan_id=100)
        b = TitanMessageAddress(bot_username="MyBot", titan_id=100)
        assert a == b

    def test_inequality_different_titan_id(self):
        a = TitanMessageAddress(bot_username="MyBot", titan_id=100)
        b = TitanMessageAddress(bot_username="MyBot", titan_id=101)
        assert a != b

    def test_inequality_different_bot(self):
        a = TitanMessageAddress(bot_username="BotA", titan_id=100)
        b = TitanMessageAddress(bot_username="BotB", titan_id=100)
        assert a != b

    def test_frozen(self):
        """TitanMessageAddress يجب أن يكون immutable."""
        addr = TitanMessageAddress(bot_username="MyBot", titan_id=1)
        with pytest.raises((AttributeError, TypeError)):
            addr.titan_id = 2  # type: ignore

    def test_hashable(self):
        """يمكن استخدامه كمفتاح في dict أو set."""
        addr = TitanMessageAddress(bot_username="MyBot", titan_id=1)
        d = {addr: "value"}
        assert d[addr] == "value"

    def test_fields_accessible(self):
        addr = TitanMessageAddress(bot_username="TestBot", titan_id=7)
        assert addr.bot_username == "TestBot"
        assert addr.titan_id == 7
