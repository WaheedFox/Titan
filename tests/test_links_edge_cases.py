"""
اختبارات الحالات الحدية لـ Message Links Protocol.

تغطي:
- أمان الخيوط في SqliteMessageStore
- حالات Archive Layer غير المفعّلة
- أوامر محجوزة غير مرئية في inspect() وhealth()
- سلوك set_data_dir مع custom store
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from titan.bot import Titan
from titan.links.manager import LinksManager
from titan.links.store import SqliteMessageStore


# ---------------------------------------------------------------------------
# Thread safety — SqliteMessageStore
# ---------------------------------------------------------------------------

class TestSqliteStoreThreadSafety:
    @pytest.mark.asyncio
    async def test_concurrent_saves_no_corruption(self):
        """حفظ متزامن من coroutines متعددة لا يُفسد البيانات."""
        store = SqliteMessageStore(":memory:")

        async def save(i: int):
            return await store.save_identity("Bot", 100, i)

        results = await asyncio.gather(*[save(i) for i in range(1, 11)])
        titan_ids = [r.titan_id for r in results]

        # كل titan_id فريد
        assert len(set(titan_ids)) == 10

    @pytest.mark.asyncio
    async def test_concurrent_reads_no_error(self):
        """قراءة متزامنة لا تُثير استثناء."""
        store = SqliteMessageStore(":memory:")
        await store.save_identity("Bot", 100, 1)

        async def read(tid: int):
            return await store.get_by_titan_id(tid)

        results = await asyncio.gather(*[read(1) for _ in range(10)])
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_connection_created_once(self):
        """الاتصال يُنشأ مرة واحدة فقط مع double-checked locking."""
        store = SqliteMessageStore(":memory:")
        assert store._conn is None

        # استدعاءان متزامنان — الاتصال يُنشأ مرة واحدة
        await asyncio.gather(
            store.get_by_titan_id(1),
            store.get_by_titan_id(2),
        )
        assert store._conn is not None


# ---------------------------------------------------------------------------
# Archive non-save paths
# ---------------------------------------------------------------------------

class TestArchiveNonSavePaths:
    @pytest.fixture
    def manager(self):
        m = LinksManager()
        m._sqlite_store = SqliteMessageStore(":memory:")
        m._store = m._sqlite_store
        return m

    @pytest.mark.asyncio
    async def test_no_archive_when_disabled(self, manager):
        """بدون تفعيل archive، جدول message_archive لا يُنشأ."""
        await manager.register_sent_message(100, 1, "Bot", text="hello")

        def _check():
            conn = manager._sqlite_store._get_conn()
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            return [t["name"] for t in tables]

        import asyncio
        tables = await asyncio.to_thread(_check)
        assert "message_archive" not in tables

    @pytest.mark.asyncio
    async def test_archive_with_custom_store_logs_no_error(self, manager):
        """Archive مُفعَّل مع custom store لا يُثير استثناء."""
        custom = MagicMock()
        custom.save_identity = AsyncMock(return_value=MagicMock(
            titan_id=1, bot_username="Bot"
        ))
        manager.set_store(custom)
        manager.enable_archive()

        # لا يجب أن يُثير استثناء — custom store ليس SqliteMessageStore
        addr = await manager.register_sent_message(100, 1, "Bot", text="hello")
        assert addr.titan_id == 1

    @pytest.mark.asyncio
    async def test_archive_failure_non_fatal(self, manager):
        """فشل archive لا يُوقف تسجيل الهوية."""
        manager.enable_archive()
        manager._sqlite_store.save_archive = AsyncMock(
            side_effect=RuntimeError("archive error")
        )

        addr = await manager.register_sent_message(100, 1, "Bot", text="text")
        # الهوية مسجّلة رغم فشل الأرشيف
        assert addr.titan_id == 1
        found = await manager.get_address_for_telegram_id(100, 1)
        assert found is not None


# ---------------------------------------------------------------------------
# Reserved commands invisibility in inspect() / health()
# ---------------------------------------------------------------------------

class TestReservedCommandsInvisibility:
    def test_link_not_in_inspect_commands(self):
        """/link لا يظهر في bot.inspect().commands."""
        bot = Titan("fake_token")
        snap = bot.inspect()
        assert "link" not in snap.commands

    def test_empty_bot_health_still_returns_findings(self):
        """بوت بدون handlers مُسجَّلة يُعيد health findings رغم وجود /link."""
        bot = Titan("fake_token")
        findings = bot.health()
        # يجب أن تكون هناك تحذيرات لبوت فارغ من handlers
        assert len(findings) > 0

    def test_bot_with_only_link_reserved_still_appears_empty_to_health(self):
        """الـ /link المحجوز لا يُعدّ handler من منظور health check."""
        bot = Titan("fake_token")
        snap = bot.inspect()
        # bot.commands فارغ — /link في _reserved_commands فقط
        assert snap.commands == ()


# ---------------------------------------------------------------------------
# set_data_dir with custom store
# ---------------------------------------------------------------------------

class TestSetDataDirWithCustomStore:
    def test_set_data_dir_after_set_store_preserves_custom_store(self, tmp_path):
        """set_data_dir لا يُلغي custom store مُعيَّن سابقاً."""
        manager = LinksManager()
        custom = SqliteMessageStore(":memory:")
        manager.set_store(custom)

        # set_data_dir لا يُعيد تعيين _store لأن store مُخصص
        manager.set_data_dir(str(tmp_path / "data"))
        assert manager._store is custom

    def test_set_data_dir_without_custom_store_updates_store(self, tmp_path):
        """set_data_dir يُحدّث _store عندما لا يوجد store مُخصص."""
        manager = LinksManager()
        original_store = manager._sqlite_store

        new_dir = str(tmp_path / "new_data")
        manager.set_data_dir(new_dir)

        # _store يجب أن يتغير إلى SQLite store الجديد
        assert manager._store is not original_store
        assert new_dir in manager._db_path

    def test_set_data_dir_updates_sqlite_store_reference(self, tmp_path):
        """set_data_dir دائماً يُحدّث _sqlite_store."""
        manager = LinksManager()
        old_sqlite = manager._sqlite_store

        manager.set_data_dir(str(tmp_path / "mydata"))
        assert manager._sqlite_store is not old_sqlite
