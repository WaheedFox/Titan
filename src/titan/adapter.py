"""
titan.adapter

طبقة الوصول الكاملة لـ Telegram Bot API.

منفصلة تماماً عن Titan Core — لا تغير سلوك البوت ولا routing ولا middleware.
تُستخدم حصراً عبر: bot.telegram.method(...)

تتطلب جلسة نشطة (bot.run() أو bot.run_async()).
"""

from __future__ import annotations

from typing import Any

from titan.telegram import Telegram


class TelegramAdapter:
    """
    وصول مباشر لـ Telegram Bot API من خارج نطاق ctx.

    يُستخدم لعمليات لا تنتمي إلى سياق رسالة واحدة:
    - إرسال وسائط (صور، فيديو، ملفات)
    - تثبيت الرسائل وإعادة توجيهها
    - إعدادات البوت
    - معلومات الشات

    لا يتفاعل مع middleware أو alias أو routing.
    """

    def __init__(self, api: Telegram) -> None:
        self._api = api

    # -------------------------
    # Messaging
    # -------------------------

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
    ) -> dict[str, Any]:
        """إرسال رسالة نصية لأي شات."""

        return await self._api.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

    async def get_chat_member(
        self,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """جلب معلومات عضو في الشات."""

        return await self._api.get_chat_member(
            chat_id=chat_id,
            user_id=user_id,
        )

    # -------------------------
    # Media
    # -------------------------

    async def send_photo(
        self,
        chat_id: int,
        photo: str,
        caption: str | None = None,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
    ) -> dict[str, Any]:
        """إرسال صورة."""

        data: dict[str, Any] = {"chat_id": chat_id, "photo": photo}
        if caption is not None:
            data["caption"] = caption
        if parse_mode is not None:
            data["parse_mode"] = parse_mode
        if reply_markup is not None:
            data["reply_markup"] = (
                reply_markup.to_dict()
                if hasattr(reply_markup, "to_dict")
                else reply_markup
            )
        return await self._api.request("sendPhoto", data)

    async def send_video(
        self,
        chat_id: int,
        video: str,
        caption: str | None = None,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
    ) -> dict[str, Any]:
        """إرسال فيديو."""

        data: dict[str, Any] = {"chat_id": chat_id, "video": video}
        if caption is not None:
            data["caption"] = caption
        if parse_mode is not None:
            data["parse_mode"] = parse_mode
        if reply_markup is not None:
            data["reply_markup"] = (
                reply_markup.to_dict()
                if hasattr(reply_markup, "to_dict")
                else reply_markup
            )
        return await self._api.request("sendVideo", data)

    async def send_document(
        self,
        chat_id: int,
        document: str,
        caption: str | None = None,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
    ) -> dict[str, Any]:
        """إرسال ملف."""

        data: dict[str, Any] = {"chat_id": chat_id, "document": document}
        if caption is not None:
            data["caption"] = caption
        if parse_mode is not None:
            data["parse_mode"] = parse_mode
        if reply_markup is not None:
            data["reply_markup"] = (
                reply_markup.to_dict()
                if hasattr(reply_markup, "to_dict")
                else reply_markup
            )
        return await self._api.request("sendDocument", data)

    async def send_audio(
        self,
        chat_id: int,
        audio: str,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        """إرسال ملف صوتي."""

        data: dict[str, Any] = {"chat_id": chat_id, "audio": audio}
        if caption is not None:
            data["caption"] = caption
        if parse_mode is not None:
            data["parse_mode"] = parse_mode
        return await self._api.request("sendAudio", data)

    async def send_sticker(
        self,
        chat_id: int,
        sticker: str,
    ) -> dict[str, Any]:
        """إرسال ملصق."""

        return await self._api.request("sendSticker", {
            "chat_id": chat_id,
            "sticker": sticker,
        })

    async def send_animation(
        self,
        chat_id: int,
        animation: str,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        """إرسال صورة متحركة (GIF)."""

        data: dict[str, Any] = {"chat_id": chat_id, "animation": animation}
        if caption is not None:
            data["caption"] = caption
        if parse_mode is not None:
            data["parse_mode"] = parse_mode
        return await self._api.request("sendAnimation", data)

    # -------------------------
    # Message Management
    # -------------------------

    async def forward_message(
        self,
        chat_id: int,
        from_chat_id: int,
        message_id: int,
    ) -> dict[str, Any]:
        """إعادة توجيه رسالة من شات إلى آخر."""

        return await self._api.request("forwardMessage", {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
        })

    async def copy_message(
        self,
        chat_id: int,
        from_chat_id: int,
        message_id: int,
        caption: str | None = None,
    ) -> dict[str, Any]:
        """نسخ رسالة بدون forward badge."""

        data: dict[str, Any] = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
        }
        if caption is not None:
            data["caption"] = caption
        return await self._api.request("copyMessage", data)

    async def pin_message(
        self,
        chat_id: int,
        message_id: int,
        disable_notification: bool = False,
    ) -> dict[str, Any]:
        """تثبيت رسالة في الشات."""

        return await self._api.request("pinChatMessage", {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": disable_notification,
        })

    async def unpin_message(
        self,
        chat_id: int,
        message_id: int,
    ) -> dict[str, Any]:
        """إلغاء تثبيت رسالة محددة."""

        return await self._api.request("unpinChatMessage", {
            "chat_id": chat_id,
            "message_id": message_id,
        })

    async def unpin_all_messages(
        self,
        chat_id: int,
    ) -> dict[str, Any]:
        """إلغاء تثبيت جميع الرسائل في الشات."""

        return await self._api.request("unpinAllChatMessages", {
            "chat_id": chat_id,
        })

    # -------------------------
    # Chat Info
    # -------------------------

    async def get_chat(self, chat_id: int) -> dict[str, Any]:
        """جلب معلومات الشات."""

        return await self._api.request("getChat", {"chat_id": chat_id})

    async def get_chat_member_count(self, chat_id: int) -> dict[str, Any]:
        """جلب عدد أعضاء الشات."""

        return await self._api.request("getChatMemberCount", {"chat_id": chat_id})

    # -------------------------
    # Bot Configuration
    # -------------------------

    async def set_my_commands(
        self,
        commands: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        تعيين قائمة أوامر البوت التي تظهر في Telegram.

        مثال:
            await bot.telegram.set_my_commands([
                {"command": "start", "description": "بدء البوت"},
                {"command": "help",  "description": "المساعدة"},
            ])
        """

        return await self._api.request("setMyCommands", {"commands": commands})

    async def delete_my_commands(self) -> dict[str, Any]:
        """حذف قائمة أوامر البوت."""

        return await self._api.request("deleteMyCommands", {})

    async def get_my_commands(self) -> dict[str, Any]:
        """جلب قائمة أوامر البوت الحالية."""

        return await self._api.request("getMyCommands", {})
