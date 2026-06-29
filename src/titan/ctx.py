"""
titan.ctx

يمثل Context الخاص بكل Update.

هذا الكائن هو ما يتعامل معه المطور داخل handlers.

هدفه:
- تبسيط الوصول لبيانات الرسالة
- توفير أدوات جاهزة (reply, ban, delete)
- إخفاء تفاصيل Telegram API بالكامل
"""

from __future__ import annotations

from typing import Any

from titan.errors import TitanError
from titan.telegram import Telegram
from titan.update import Update
from titan.models.sender import Sender
from titan.models.chat import Chat
from titan.models.message import Message


class Context:
    """
    كائن السياق المستخدم داخل كل handler.

    يحتوي على:
    - البيانات المستخرجة من Update
    - أدوات للتفاعل مع Telegram

    ملاحظة: _api هو internal — استخدم دوال ctx مباشرة.
    """

    def __init__(self, update: Update, api: Telegram) -> None:
        self._update = update
        self._api = api

        self.raw: dict = update.raw

        self.sender = Sender(self._update._user())
        self.chat = Chat(self._update._chat())
        self.message = Message(self._update.get_message())

        # لا يوجد API call هنا — يتطلب refresh_permissions() صريح
        self.can_delete: bool | None = None

        # يُعيَّن من bot قبل تنفيذ أي middleware أو handler
        self.is_banned: bool = False

    # -------------------------
    # Message data
    # -------------------------

    @property
    def text(self) -> str | None:
        return self._update.text

    @property
    def user_id(self) -> int | None:
        return self._update.user_id

    @property
    def chat_id(self) -> int | None:
        return self._update.chat_id

    @property
    def username(self) -> str | None:
        return self._update.username

    @property
    def message_id(self) -> int | None:
        return self._update.message_id

    @property
    def callback_data(self) -> str | None:
        """
        بيانات الزر المضغوط في callback_query.
        """

        cb = self._update.callback_query
        if not cb:
            return None

        return cb.get("data")

    @property
    def callback_id(self) -> str | None:
        """
        معرّف الـ callback_query.
        مطلوب لـ answer_callback.
        """

        cb = self._update.callback_query
        if not cb:
            return None

        return cb.get("id")

    @property
    def new_members(self) -> list[dict] | None:
        """
        قائمة الأعضاء الجدد في رسائل الانضمام.
        متاح داخل @bot.on("new_member").
        """

        msg = self._update.get_message()
        if not msg:
            return None

        return msg.get("new_chat_members") or None

    @property
    def left_member(self) -> dict | None:
        """
        بيانات العضو الذي غادر الشات.
        متاح داخل @bot.on("left_member").

        مثال:
            @bot.on("left_member")
            async def on_leave(ctx):
                print(ctx.left_member)  # {"id": 99, "first_name": "Ali", ...}
        """

        msg = self._update.get_message()
        if not msg:
            return None

        return msg.get("left_chat_member") or None

    # -------------------------
    # Actions
    # -------------------------

    async def reply(
        self,
        text: str,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
    ) -> Any:
        """
        رد حقيقي على رسالة المستخدم (reply_to_message_id).

        المعاملات:
        - text: نص الرسالة
        - parse_mode: "HTML" أو "Markdown" (اختياري)
        - reply_markup: InlineKeyboard أو أي markup آخر (اختياري)

        مثال:
            await ctx.reply("مرحباً!")
            await ctx.reply("اختر:", reply_markup=kb)
        """

        chat_id = self.chat_id
        if chat_id is None:
            return None

        return await self._api.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            reply_to_message_id=self.message_id,
        )

    async def send(
        self,
        text: str,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
    ) -> Any:
        """
        إرسال رسالة جديدة في الشات بدون ربطها برسالة المستخدم.

        استخدم هذا عندما لا تريد رداً مباشراً، مثل إرسال إشعار
        أو رسالة مستقلة.

        مثال:
            await ctx.send("تم تسجيلك ✅")
        """

        chat_id = self.chat_id
        if chat_id is None:
            return None

        return await self._api.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

    async def edit(
        self,
        text: str,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
    ) -> Any:
        """
        تعديل نص رسالة البوت في callback handler.

        تعمل فقط داخل @bot.on("callback") أو @bot.callback("data")
        لأن message_id في هذا السياق يشير لرسالة البوت نفسه.

        لتحرير رسالة أرسلها البوت في سياقات أخرى، استخدم
        return value من ctx.send() — سيُدعم في نسخة قادمة.
        """

        if self._update.callback_query is None:
            raise TitanError(
                "ctx.edit() requires an active callback_query context. "
                "It can only be called inside @bot.on('callback') or @bot.callback('data') handlers. "
                "To send a new message instead, use ctx.reply() or ctx.send()."
            )

        chat_id = self.chat_id
        message_id = self.message_id

        if chat_id is None or message_id is None:
            return None

        return await self._api.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

    async def delete_message(self) -> Any:
        """
        حذف الرسالة الحالية.
        """

        chat_id = self.chat_id
        message_id = self.message_id

        if chat_id is None or message_id is None:
            return None

        return await self._api.delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )

    async def ban_user(self, user_id: int | None = None) -> Any:
        """
        حظر مستخدم من الشات.

        إذا لم يتم تمرير user_id سيتم حظر صاحب الرسالة.
        """

        chat_id = self.chat_id
        target_user = user_id if user_id is not None else self.user_id

        if chat_id is None or target_user is None:
            return None

        return await self._api.ban_user(
            chat_id=chat_id,
            user_id=target_user,
        )

    async def refresh_permissions(self) -> None:
        """
        تحديث صلاحيات البوت في الشات الحالي.

        يجب استدعاؤها صراحةً — لا يوجد API call تلقائي.
        النتيجة تُخزن في ctx.can_delete.
        """

        chat_id = self.chat_id
        if chat_id is None:
            self.can_delete = False
            return

        try:
            me = await self._api.get_me()
            member = await self._api.get_chat_member(
                chat_id=chat_id,
                user_id=me["id"],
            )
            result = member.get("result", {})
            self.can_delete = result.get("can_delete_messages", False)
        except Exception:
            self.can_delete = False

    async def leave(self) -> Any:
        """مغادرة الشات الحالي."""

        chat_id = self.chat_id
        if chat_id is None:
            return None

        return await self._api.leave_chat(chat_id=chat_id)

    async def answer_callback(
        self,
        text: str | None = None,
        show_alert: bool = False,
    ) -> Any:
        """
        إغلاق حالة التحميل الخاصة بأزرار callback.
        """

        callback_id = self.callback_id
        if callback_id is None:
            return None

        return await self._api.answer_callback_query(
            callback_query_id=callback_id,
            text=text,
            show_alert=show_alert,
        )
