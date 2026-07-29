"""
اختبارات TitanMessageIdentity — نموذج بيانات هوية الرسالة.
"""

from titan.links.identity import TitanMessageIdentity


class TestTitanMessageIdentity:
    def test_basic_construction(self):
        ident = TitanMessageIdentity(
            titan_id=1,
            bot_username="MyBot",
            telegram_message_id=100,
            chat_id=200,
        )
        assert ident.titan_id == 1
        assert ident.bot_username == "MyBot"
        assert ident.telegram_message_id == 100
        assert ident.chat_id == 200
        assert ident.deleted is False

    def test_deleted_default_false(self):
        ident = TitanMessageIdentity(
            titan_id=5,
            bot_username="Bot",
            telegram_message_id=50,
            chat_id=99,
        )
        assert ident.deleted is False

    def test_deleted_explicit_true(self):
        ident = TitanMessageIdentity(
            titan_id=5,
            bot_username="Bot",
            telegram_message_id=50,
            chat_id=99,
            deleted=True,
        )
        assert ident.deleted is True

    def test_mutable(self):
        """TitanMessageIdentity قابل للتعديل — deleted يتغير عند الحذف."""
        ident = TitanMessageIdentity(
            titan_id=1,
            bot_username="Bot",
            telegram_message_id=10,
            chat_id=20,
        )
        ident.deleted = True
        assert ident.deleted is True
