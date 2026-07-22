"""
titan.links

Message Links Protocol — بروتوكول هوية الرسائل في Titan.

كل رسالة يرسلها البوت عبر ctx.reply() أو ctx.send() تحصل تلقائياً
على TitanMessageAddress فريد. لا opt-in، لا تهيئة.

الواجهة العامة:
    bot.links                    — LinksManager (يُهيَّأ تلقائياً)
    bot.links.enable_archive()   — تفعيل Archive Layer
    bot.links.set_store(store)   — استبدال backend التخزين
    bot.links.set_data_dir(path) — تغيير مسار بيانات SQLite

النماذج:
    TitanMessageAddress    — وحدة الهوية الكاملة
    TitanMessageIdentity   — البيانات الأساسية المُخزَّنة
    TitanMessageArchive    — بيانات الأرشيف (عند التفعيل)

التخزين:
    MessageStore           — واجهة مجردة
    SqliteMessageStore     — التطبيق الافتراضي

الفصل بين الكود والبيانات:
    titan/links/           — كود وبنية البروتوكول
    .titan/links.db        — بيانات تشغيلية (في مشروع المطور)
"""

from titan.links.address import TitanMessageAddress
from titan.links.archive import TitanMessageArchive
from titan.links.identity import TitanMessageIdentity
from titan.links.manager import LinksManager
from titan.links.store import MessageStore, SqliteMessageStore

__all__ = [
    "TitanMessageAddress",
    "TitanMessageArchive",
    "TitanMessageIdentity",
    "LinksManager",
    "MessageStore",
    "SqliteMessageStore",
]
