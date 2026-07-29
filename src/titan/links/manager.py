"""
titan.links.manager

LinksManager — الكلاس الرئيسي لـ Message Links Protocol.

هذا ما يشير إليه bot.links.

مسؤوليته:
- تهيئة Identity Layer تلقائياً.
- تسجيل هوية كل رسالة مُرسَلة بنجاح.
- توفير /link handler بالمعلومات اللازمة.
- إدارة Archive Layer عند تفعيلها.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from titan.links.address import TitanMessageAddress
from titan.links.identity import TitanMessageIdentity
from titan.links.store import MessageStore, SqliteMessageStore

if TYPE_CHECKING:
    pass

_log = logging.getLogger("titan.links")

_DEFAULT_DATA_DIR_NAME = ".titan"
_DEFAULT_DB_NAME = "links.db"


class LinksManager:
    """
    المدير الرئيسي لبروتوكول Message Links.

    يُهيَّأ تلقائياً داخل Titan ويُعرَض عبر bot.links.

    الواجهة العامة المضمونة:
        bot.links.enable_archive()          — تفعيل Archive Layer.
        bot.links.set_store(store)          — استبدال backend التخزين.
        bot.links.set_data_dir(path)        — تغيير مسار بيانات SQLite.

    الطبقات الداخلية ليست API مضمون — لا تُنشئها مباشرةً.

    ملاحظة Archive v1:
        Archive Layer تعمل مع SqliteMessageStore فقط.
        دعم custom stores للأرشيف مخطط لإصدار مستقبلي.
    """

    def __init__(self, data_dir: str | None = None) -> None:
        resolved_dir = data_dir or os.path.join(
            os.getcwd(), _DEFAULT_DATA_DIR_NAME
        )
        self._data_dir: str = resolved_dir
        self._db_path: str = os.path.join(resolved_dir, _DEFAULT_DB_NAME)
        self._sqlite_store = SqliteMessageStore(self._db_path)
        self._store: MessageStore = self._sqlite_store
        self._archive_enabled: bool = False

    # -------------------------
    # Public configuration API
    # -------------------------

    def enable_archive(self) -> None:
        """
        تفعيل Archive Layer.

        بعد التفعيل، كل رسالة مُرسَلة يُحفظ نصها ومعلوماتها
        بجوار هويتها في قاعدة البيانات.

        Archive Layer في v1 تعمل مع SqliteMessageStore فقط.
        """
        self._archive_enabled = True
        _log.info("Message Links: Archive Layer enabled.")

    def set_store(self, store: MessageStore) -> None:
        """
        استبدال backend التخزين.

        يُستخدم عند الحاجة لتخزين مختلف عن SQLite الافتراضي.
        ملاحظة: Archive Layer في v1 تتطلب SqliteMessageStore.
        """
        self._store = store

    async def mark_deleted(self, titan_id: int) -> None:
        """
        تعليم رسالة كمحذوفة في Identity Layer.

        لا يحذف الهوية من قاعدة البيانات — titan_id محجوز تاريخياً للأبد
        ولا يُعاد تخصيصه لرسالة أخرى.

        يُستخدم عندما يُحذف محتوى الرسالة من Telegram (مثلاً عبر
        ctx.delete_message()) ويريد المطور تعكس ذلك في Identity Layer.

        لا تأثير إذا كانت الهوية محذوفة مسبقاً أو غير موجودة.
        """
        await self._store.mark_deleted(titan_id)
        _log.debug("Message Links: titan_id=%s marked as deleted.", titan_id)

    def set_data_dir(self, path: str) -> None:
        """
        تغيير مسار مجلد بيانات SQLite.

        يُعيد إنشاء SqliteMessageStore الداخلي بالمسار الجديد.

        إذا كان المطور قد استبدل الـ store بـ set_store()، يبقى الـ store
        المخصص كما هو — set_data_dir لا يُلغي التخصيص.
        يُستخدم فقط لتغيير مسار SqliteMessageStore الافتراضي.
        """
        old_sqlite = self._sqlite_store
        self._data_dir = path
        self._db_path = os.path.join(path, _DEFAULT_DB_NAME)
        new_sqlite = SqliteMessageStore(self._db_path)
        self._sqlite_store = new_sqlite
        # يُحدّث _store فقط إذا كان لا يزال يُشير إلى sqlite_store القديم —
        # أي أن المطور لم يستبدله بـ set_store() مسبقاً.
        if self._store is old_sqlite:
            self._store = new_sqlite

    # -------------------------
    # Core operations
    # -------------------------

    async def register_sent_message(
        self,
        chat_id: int,
        telegram_message_id: int,
        bot_username: str,
        text: str | None = None,
        chat_type: str = "unknown",
    ) -> TitanMessageAddress:
        """
        تسجيل هوية رسالة أُرسلت بنجاح.

        يُستدعى تلقائياً من ctx.reply() وctx.send() بعد نجاح الإرسال.
        المطور لا يستدعي هذا مباشرةً.

        الهوية تُنشأ فقط بعد نجاح إرسال Telegram — الرسائل الفاشلة
        لا تحصل على TitanMessageId.
        """
        identity = await self._store.save_identity(
            bot_username=bot_username,
            chat_id=chat_id,
            telegram_message_id=telegram_message_id,
        )

        address = TitanMessageAddress(
            bot_username=identity.bot_username,
            titan_id=identity.titan_id,
        )

        if self._archive_enabled and isinstance(self._store, SqliteMessageStore):
            try:
                await self._store.save_archive(
                    titan_id=identity.titan_id,
                    text=text,
                    chat_type=chat_type,
                )
            except Exception as exc:
                _log.warning(
                    "Message Links: archive save failed for titan_id=%s: %s",
                    identity.titan_id,
                    exc,
                )

        return address

    async def get_address_for_telegram_id(
        self,
        chat_id: int,
        telegram_message_id: int,
    ) -> TitanMessageAddress | None:
        """
        جلب عنوان Titan لرسالة عبر معرف Telegram ومعرف الشات.

        يُعيد None إذا لم تُسجَّل الرسالة في Identity Layer —
        أي أنها أُرسلت قبل تفعيل بروتوكول الهوية.
        """
        identity = await self._store.get_by_telegram_id(
            chat_id=chat_id,
            telegram_message_id=telegram_message_id,
        )

        if identity is None:
            return None

        return TitanMessageAddress(
            bot_username=identity.bot_username,
            titan_id=identity.titan_id,
        )

    async def get_address_for_titan_id(
        self,
        titan_id: int,
    ) -> TitanMessageAddress | None:
        """
        جلب عنوان Titan بمعرفه التسلسلي.

        يُعيد None إذا لم يوجد titan_id في قاعدة البيانات.
        """
        identity = await self._store.get_by_titan_id(titan_id)

        if identity is None:
            return None

        return TitanMessageAddress(
            bot_username=identity.bot_username,
            titan_id=identity.titan_id,
        )
