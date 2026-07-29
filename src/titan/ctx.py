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

import logging
from typing import Any

from titan.errors import TitanError

_log = logging.getLogger("titan")
from titan.telegram import Telegram
from titan.update import Update
from titan.models.sender import Sender
from titan.models.chat import Chat
from titan.models.message import Message
from titan.models.permissions import ChatPermissions

# Import deferred to avoid circular — LinksManager lives in titan.links
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from titan.links.manager import LinksManager


class TypingAction:
    """
    Context manager يُرسل إشارة "typing" في Telegram.

    لا يُستخدم مباشرةً — يُنشأ عبر ctx.typing().

    مثال:
        async with ctx.typing():
            result = await heavy_task()
        await ctx.reply(result)
    """

    def __init__(self, ctx: "Context") -> None:
        self._ctx = ctx

    async def __aenter__(self) -> "TypingAction":
        chat_id = self._ctx.chat_id
        if chat_id is not None:
            await self._ctx._api.send_chat_action(chat_id, "typing")
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        pass


class Context:
    """
    كائن السياق المستخدم داخل كل handler.

    يحتوي على:
    - البيانات المستخرجة من Update
    - أدوات للتفاعل مع Telegram

    ملاحظة: _api هو internal — استخدم دوال ctx مباشرة.
    """

    def __init__(
        self,
        update: Update,
        api: Telegram,
        links: "LinksManager | None" = None,
    ) -> None:
        self._update = update
        self._api = api
        self._links = links

        self.raw: dict = update.raw

        self.sender = Sender(self._update._user())
        self.chat = Chat(self._update._chat())
        self.message = Message(self._update.get_message())

        # None حتى يستدعي المطوّر fetch_permissions() صراحةً
        self.permissions: ChatPermissions | None = None

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
    def reply_to_message_id(self) -> int | None:
        """
        معرف Telegram للرسالة التي يرد عليها المستخدم الحالي.

        None إذا لم يكن هذا الـ update رداً على رسالة.
        """
        return self._update.reply_to_message_id

    @property
    def callback_data(self) -> str | None:
        """
        بيانات الزر المضغوط في callback_query.
        """

        return self._update.callback_data

    @property
    def callback_id(self) -> str | None:
        """
        معرّف الـ callback_query.
        مطلوب لـ answer_callback.
        """

        return self._update.callback_id

    @property
    def new_members(self) -> list[Sender] | None:
        """
        قائمة الأعضاء الجدد في رسائل الانضمام.
        متاح داخل @bot.on("new_member").
        """

        msg = self._update.get_message()
        if not msg:
            return None

        raw_members = msg.get("new_chat_members")
        if not raw_members:
            return None

        return [Sender(m) for m in raw_members]

    @property
    def left_member(self) -> Sender | None:
        """
        العضو الذي غادر الشات.
        متاح داخل @bot.on("left_member").

        مثال:
            @bot.on("left_member")
            async def on_leave(ctx):
                print(ctx.left_member.first_name)
        """

        msg = self._update.get_message()
        if not msg:
            return None

        raw = msg.get("left_chat_member")
        if not raw:
            return None

        return Sender(raw)

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
            _log.warning(
                "ctx.reply() called with no chat_id in this update — message not sent."
            )
            return None

        result = await self._api.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            reply_to_message_id=self.message_id,
        )

        await self._register_identity(result, text)
        return result

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
            _log.warning(
                "ctx.send() called with no chat_id in this update — message not sent."
            )
            return None

        result = await self._api.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

        await self._register_identity(result, text)
        return result

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
            _log.warning(
                "ctx.edit() called with no chat_id or message_id in this callback "
                "context — message not edited."
            )
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

        if chat_id is None:
            _log.warning(
                "ctx.delete_message() called with no chat_id in this update — "
                "message not deleted."
            )
            return None
        if message_id is None:
            _log.warning(
                "ctx.delete_message() called with no message_id in this update — "
                "message not deleted."
            )
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

        if chat_id is None:
            _log.warning(
                "ctx.ban_user() called with no chat_id in this update — ban not executed."
            )
            return None
        if target_user is None:
            _log.warning(
                "ctx.ban_user() called with no resolvable user_id in this update — "
                "ban not executed."
            )
            return None

        return await self._api.ban_user(
            chat_id=chat_id,
            user_id=target_user,
        )

    async def fetch_permissions(self) -> ChatPermissions:
        """
        جلب صلاحيات البوت في الشات الحالي من Telegram API.

        يجب استدعاؤها صراحةً — لا يوجد API call تلقائي.
        النتيجة تُخزن في ctx.permissions وتُعاد أيضاً.

        يرفع TitanError إذا لم يكن هناك chat_id في السياق الحالي.
        يُمرّر TelegramError للمطوّر عند فشل الطلب.

        مثال:
            await ctx.fetch_permissions()
            if ctx.permissions.can_delete_messages:
                await ctx.delete_message()
        """

        chat_id = self.chat_id
        if chat_id is None:
            raise TitanError(
                "ctx.fetch_permissions() requires a chat_id. "
                "This context has no associated chat."
            )

        me = await self._api.get_me()
        member = await self._api.get_chat_member(
            chat_id=chat_id,
            user_id=me["id"],
        )
        result = member.get("result", {})
        self.permissions = ChatPermissions(result)
        return self.permissions

    async def leave(self) -> Any:
        """مغادرة الشات الحالي."""

        chat_id = self.chat_id
        if chat_id is None:
            _log.warning(
                "ctx.leave() called with no chat_id in this update — leave not executed."
            )
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

        if self._update.callback_query is None:
            raise TitanError(
                "ctx.answer_callback() requires an active callback_query context. "
                "It can only be called inside @bot.on('callback') or "
                "@bot.callback('data') handlers."
            )

        callback_id = self.callback_id
        if callback_id is None:
            raise TitanError(
                "ctx.answer_callback() received a callback_query with no 'id' field. "
                "This indicates a malformed update from Telegram — the callback_query "
                "object is present but missing its identifier."
            )

        return await self._api.answer_callback_query(
            callback_query_id=callback_id,
            text=text,
            show_alert=show_alert,
        )

    # -------------------------
    # Message Links Protocol (internal)
    # -------------------------

    async def _register_identity(
        self,
        send_result: Any,
        text: str | None,
    ) -> None:
        """
        تسجيل هوية رسالة أُرسلت بنجاح في Identity Layer.

        يُستدعى داخلياً من reply() وsend() بعد نجاح الإرسال.
        الفشل غير مميت — الرسالة وصلت، الهوية تُسجَّل best-effort.
        """
        if self._links is None or send_result is None:
            return

        chat_id = self.chat_id
        if chat_id is None:
            return

        telegram_msg_id: int | None = (
            send_result.get("result", {}).get("message_id")
        )
        if telegram_msg_id is None:
            return

        bot_me = self._api._me
        bot_username: str | None = bot_me.get("username") if bot_me else None
        if bot_username is None:
            _log.warning(
                "Message Links: identity registration skipped for "
                "telegram_message_id=%s — bot_username unavailable "
                "(api._me not populated yet or missing 'username' field). "
                "Ensure bot.run_async() is used so get_me() runs before updates are processed.",
                telegram_msg_id,
            )
            return

        try:
            await self._links.register_sent_message(
                chat_id=chat_id,
                telegram_message_id=telegram_msg_id,
                bot_username=bot_username,
                text=text,
                chat_type=self._update.chat_type or "unknown",
            )
        except Exception as exc:
            _log.warning(
                "Message Links: identity registration failed for "
                "telegram_message_id=%s: %s",
                telegram_msg_id,
                exc,
            )

    def typing(self) -> TypingAction:
        """
        Context manager يُظهر إشارة "typing…" في Telegram
        طوال فترة تنفيذ الكتلة.

        مثال:
            async with ctx.typing():
                result = await heavy_task()
            await ctx.reply(result)

        الإشارة تُرسل مرة واحدة عند دخول الكتلة.
        لا توجد إعادة إرسال تلقائية للعمليات التي تتجاوز 5 ثوانٍ.
        """

        return TypingAction(self)
