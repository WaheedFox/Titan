"""
اختبارات LinksManager — الكلاس الرئيسي لـ Message Links Protocol.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from titan.links.manager import LinksManager
from titan.links.store import SqliteMessageStore
from titan.links.address import TitanMessageAddress


@pytest.fixture
def manager():
    """LinksManager مع store في الذاكرة."""
    m = LinksManager()
    m._sqlite_store = SqliteMessageStore(":memory:")
    m._store = m._sqlite_store
    return m


class TestRegisterSentMessage:
    @pytest.mark.asyncio
    async def test_returns_address(self, manager):
        addr = await manager.register_sent_message(
            chat_id=100,
            telegram_message_id=50,
            bot_username="MyBot",
        )
        assert isinstance(addr, TitanMessageAddress)
        assert addr.bot_username == "MyBot"
        assert addr.titan_id == 1
        assert str(addr) == "https://t.me/MyBot/1"

    @pytest.mark.asyncio
    async def test_sequential_ids(self, manager):
        a = await manager.register_sent_message(100, 1, "Bot")
        b = await manager.register_sent_message(100, 2, "Bot")
        c = await manager.register_sent_message(100, 3, "Bot")
        assert a.titan_id == 1
        assert b.titan_id == 2
        assert c.titan_id == 3

    @pytest.mark.asyncio
    async def test_text_and_chat_type_ignored_when_archive_disabled(self, manager):
        """بدون تفعيل archive، النص لا يُحفظ ولا يُثير خطأ."""
        addr = await manager.register_sent_message(
            chat_id=100,
            telegram_message_id=10,
            bot_username="Bot",
            text="مرحبا",
            chat_type="private",
        )
        assert addr.titan_id == 1


class TestGetAddressForTelegramId:
    @pytest.mark.asyncio
    async def test_found_after_register(self, manager):
        await manager.register_sent_message(100, 55, "MyBot")
        addr = await manager.get_address_for_telegram_id(
            chat_id=100,
            telegram_message_id=55,
        )
        assert addr is not None
        assert addr.bot_username == "MyBot"
        assert addr.titan_id == 1

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, manager):
        result = await manager.get_address_for_telegram_id(
            chat_id=999,
            telegram_message_id=999,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_not_found_before_registration(self, manager):
        """الرسائل القديمة (قبل التفعيل) لا تملك هوية."""
        result = await manager.get_address_for_telegram_id(
            chat_id=100,
            telegram_message_id=1,
        )
        assert result is None


class TestGetAddressForTitanId:
    @pytest.mark.asyncio
    async def test_found(self, manager):
        await manager.register_sent_message(100, 10, "Bot")
        addr = await manager.get_address_for_titan_id(1)
        assert addr is not None
        assert addr.titan_id == 1

    @pytest.mark.asyncio
    async def test_not_found(self, manager):
        result = await manager.get_address_for_titan_id(9999)
        assert result is None


class TestEnableArchive:
    @pytest.mark.asyncio
    async def test_archive_flag_set(self, manager):
        assert manager._archive_enabled is False
        manager.enable_archive()
        assert manager._archive_enabled is True

    @pytest.mark.asyncio
    async def test_archive_saves_when_enabled(self, manager):
        manager.enable_archive()
        addr = await manager.register_sent_message(
            chat_id=100,
            telegram_message_id=20,
            bot_username="Bot",
            text="نص مهم",
            chat_type="private",
        )
        assert addr.titan_id == 1
        # نتحقق أن الأرشيف حُفظ بالاستعلام المباشر عن الـ store
        store = manager._sqlite_store

        def _check():
            conn = store._get_conn()
            row = conn.execute(
                "SELECT * FROM message_archive WHERE titan_id = 1"
            ).fetchone()
            return row

        import asyncio
        row = await asyncio.to_thread(_check)
        assert row is not None
        assert row["text"] == "نص مهم"
        assert row["chat_type"] == "private"


class TestSetStore:
    @pytest.mark.asyncio
    async def test_custom_store_used(self, manager):
        custom = SqliteMessageStore(":memory:")
        manager.set_store(custom)
        addr = await manager.register_sent_message(100, 1, "Bot")
        assert addr.titan_id == 1
        # التحقق أن الهوية حُفظت في custom store
        found = await custom.get_by_telegram_id(100, 1)
        assert found is not None


class TestMarkDeleted:
    @pytest.mark.asyncio
    async def test_mark_deleted_via_public_api(self, manager):
        """mark_deleted متاحة عبر bot.links مباشرةً."""
        await manager.register_sent_message(100, 10, "Bot")
        await manager.mark_deleted(1)

        # الهوية لا تزال موجودة (محجوزة تاريخياً)
        addr = await manager.get_address_for_titan_id(1)
        assert addr is not None
        assert addr.titan_id == 1

    @pytest.mark.asyncio
    async def test_mark_deleted_sets_deleted_flag(self, manager):
        """بعد mark_deleted الـ deleted flag يُعيَّن في قاعدة البيانات."""
        await manager.register_sent_message(100, 20, "Bot")
        await manager.mark_deleted(1)

        row = await manager._store.get_by_titan_id(1)
        assert row is not None
        assert row.deleted is True

    @pytest.mark.asyncio
    async def test_titan_id_not_reused_after_mark_deleted(self, manager):
        """titan_id لا يُعاد تخصيصه بعد الحذف."""
        await manager.register_sent_message(100, 10, "Bot")
        await manager.mark_deleted(1)
        next_addr = await manager.register_sent_message(100, 11, "Bot")
        assert next_addr.titan_id == 2  # لا يعود لـ 1

    @pytest.mark.asyncio
    async def test_mark_deleted_nonexistent_no_error(self, manager):
        """mark_deleted على titan_id غير موجود لا يُثير استثناء."""
        await manager.mark_deleted(9999)  # صامت، لا خطأ

    @pytest.mark.asyncio
    async def test_mark_deleted_address_still_resolvable(self, manager):
        """العنوان يُحل دائماً حتى بعد الحذف — الهوية تاريخية."""
        await manager.register_sent_message(100, 30, "MyBot")
        await manager.mark_deleted(1)

        addr = await manager.get_address_for_titan_id(1)
        assert str(addr) == "https://t.me/MyBot/1"

        addr2 = await manager.get_address_for_telegram_id(100, 30)
        assert str(addr2) == "https://t.me/MyBot/1"


class TestSetDataDir:
    def test_updates_db_path(self, manager, tmp_path):
        new_dir = str(tmp_path / "mydata")
        manager.set_data_dir(new_dir)
        assert manager._data_dir == new_dir
        assert "links.db" in manager._db_path
        assert new_dir in manager._db_path
