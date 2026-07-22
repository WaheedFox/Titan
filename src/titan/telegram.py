"""
التعامل المباشر مع Telegram Bot API.

جميع الطلبات إلى Telegram تمر من هذا الملف.
لا يحتوي على أوامر أو فلاتر أو منطق البوت.
"""

from __future__ import annotations

from typing import Any

import aiohttp

from titan.errors import TitanError


class TelegramError(TitanError):
    """خطأ صادر من Telegram API."""
    pass

class Telegram:
    """واجهة بسيطة للتعامل مع Telegram Bot API."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session: aiohttp.ClientSession | None = None
        self._me: dict[str, Any] | None = None

    async def start(self) -> None:
        """إنشاء جلسة HTTP إذا لم تكن موجودة."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        """إغلاق الجلسة عند إيقاف البوت."""
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def request(
        self,
        method: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        إرسال طلب إلى Telegram API.
        """

        if self.session is None:
            raise TelegramError(
                f"Cannot call '{method}': Telegram session is not started. "
                "Call bot.run() to start the bot before making API requests."
            )

        url = f"{self.base_url}/{method}"

        async with self.session.post(url, json=data or {}) as response:
            try:
                result: dict[str, Any] = await response.json()
            except Exception:
                raise TelegramError(
                    f"Telegram returned a non-JSON response for '{method}'. "
                    "This indicates a network error, proxy interference, or an "
                    "unavailable Telegram server. Check your internet connection."
                )

            if not result.get("ok"):
                description = result.get("description", "unknown error")
                error_code = result.get("error_code", "N/A")
                raise TelegramError(
                    f"Telegram API error on '{method}': {description} "
                    f"(error_code: {error_code})"
                )

            return result

    async def get_me(self) -> dict[str, Any]:
        """جلب معلومات البوت. النتيجة محفوظة في الذاكرة بعد أول استدعاء."""

        if self._me is None:
            result = await self.request("getMe")
            self._me = result.get("result", {})

        return self._me

    async def get_updates(
        self,
        offset: int = 0,
        timeout: int = 30,
    ) -> list[dict[str, Any]]:
        """
        جلب التحديثات الجديدة باستخدام Long Polling.
        """

        result = await self.request(
            "getUpdates",
            {
                "offset": offset,
                "timeout": timeout,
            },
        )

        return result.get("result", [])

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
        reply_to_message_id: int | None = None,
    ) -> dict[str, Any]:
        """إرسال رسالة نصية."""

        data: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if parse_mode is not None:
            data["parse_mode"] = parse_mode

        if reply_markup is not None:
            data["reply_markup"] = (
                reply_markup.to_dict()
                if hasattr(reply_markup, "to_dict")
                else reply_markup
            )

        if reply_to_message_id is not None:
            data["reply_parameters"] = {"message_id": reply_to_message_id}

        return await self.request("sendMessage", data)

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
    ) -> dict[str, Any]:
        """تعديل نص رسالة موجودة."""

        data: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }

        if parse_mode is not None:
            data["parse_mode"] = parse_mode

        if reply_markup is not None:
            data["reply_markup"] = (
                reply_markup.to_dict()
                if hasattr(reply_markup, "to_dict")
                else reply_markup
            )

        return await self.request("editMessageText", data)

    async def delete_message(
        self,
        chat_id: int,
        message_id: int,
    ) -> dict[str, Any]:
        """حذف رسالة."""

        return await self.request(
            "deleteMessage",
            {
                "chat_id": chat_id,
                "message_id": message_id,
            },
        )

    async def ban_user(
        self,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """حظر مستخدم."""

        return await self.request(
            "banChatMember",
            {
                "chat_id": chat_id,
                "user_id": user_id,
            },
        )

    async def get_chat_member(
        self,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """جلب معلومات عضو في الشات."""

        return await self.request(
            "getChatMember",
            {
                "chat_id": chat_id,
                "user_id": user_id,
            },
        )

    async def leave_chat(
        self,
        chat_id: int,
    ) -> dict[str, Any]:
        """مغادرة الشات."""

        return await self.request(
            "leaveChat",
            {
                "chat_id": chat_id,
            },
        )

    async def send_chat_action(
        self,
        chat_id: int,
        action: str,
    ) -> dict[str, Any]:
        """إرسال إشارة نشاط للمستخدم (typing, upload_photo, …)."""

        return await self.request(
            "sendChatAction",
            {
                "chat_id": chat_id,
                "action": action,
            },
        )

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> dict[str, Any]:
        """إرسال رد على callback_query لإغلاق حالة التحميل."""

        data: dict[str, Any] = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }

        if text is not None:
            data["text"] = text

        return await self.request("answerCallbackQuery", data)
