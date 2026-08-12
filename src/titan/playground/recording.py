"""
titan.playground.recording

RecordingTelegram — بديل لـ Telegram يُستخدم داخل Playground فقط.

يسجل كل استدعاء API بدل تنفيذه فعلياً عبر الشبكة. لا يحاول محاكاة
Telegram Bot API بالكامل — فقط الطرق التي يستدعيها Context فعلياً
اليوم. أي method غير مدعومة تفشل بوضوح (AttributeError) بدلاً من إعطاء
سلوك وهمي.

راجع docs/decisions/011-playground.md — القرار #3.
"""

from __future__ import annotations

from typing import Any


class RecordingTelegram:
    """
    بديل duck-typed لـ Telegram، معزول بالكامل داخل titan.playground.

    لا اتصال شبكة فعلي. كل استدعاء يُسجَّل في self.calls ويُعاد رد
    مصطنع متسق (message_id تسلسلي، ok: True).

    مثال:
        api = RecordingTelegram()
        bot = Titan("dummy-token")
        bot._api = api
        ...
        print(api.calls)  # [{"method": "send_message", "chat_id": 1, ...}]
    """

    def __init__(self, bot_username: str = "playground_bot") -> None:
        self.calls: list[dict[str, Any]] = []
        self._next_message_id = 1
        self._me: dict[str, Any] | None = {
            "id": 0,
            "is_bot": True,
            "first_name": "Playground",
            "username": bot_username,
        }

    def _record(self, method: str, **kwargs: Any) -> None:
        self.calls.append({"method": method, **kwargs})

    def _next_id(self) -> int:
        message_id = self._next_message_id
        self._next_message_id += 1
        return message_id

    # -------------------------
    # Identity
    # -------------------------
    async def get_me(self) -> dict[str, Any]:
        self._record("get_me")
        return self._me or {}

    # -------------------------
    # Messaging
    # -------------------------
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
        reply_to_message_id: int | None = None,
    ) -> dict[str, Any]:
        self._record(
            "send_message",
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id,
        )
        message_id = self._next_id()
        return {"ok": True, "result": {"message_id": message_id, "chat": {"id": chat_id}, "text": text}}

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: Any | None = None,
    ) -> dict[str, Any]:
        self._record(
            "edit_message_text",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return {"ok": True, "result": {"message_id": message_id, "chat": {"id": chat_id}, "text": text}}

    async def delete_message(self, chat_id: int, message_id: int) -> dict[str, Any]:
        self._record("delete_message", chat_id=chat_id, message_id=message_id)
        return {"ok": True, "result": True}

    async def send_chat_action(self, chat_id: int, action: str) -> dict[str, Any]:
        self._record("send_chat_action", chat_id=chat_id, action=action)
        return {"ok": True, "result": True}

    # -------------------------
    # Chat / Members
    # -------------------------
    async def ban_user(self, chat_id: int, user_id: int) -> dict[str, Any]:
        self._record("ban_user", chat_id=chat_id, user_id=user_id)
        return {"ok": True, "result": True}

    async def get_chat_member(self, chat_id: int, user_id: int) -> dict[str, Any]:
        self._record("get_chat_member", chat_id=chat_id, user_id=user_id)
        return {
            "ok": True,
            "result": {
                "status": "member",
                "user": {"id": user_id, "is_bot": False},
            },
        }

    async def leave_chat(self, chat_id: int) -> dict[str, Any]:
        self._record("leave_chat", chat_id=chat_id)
        return {"ok": True, "result": True}

    # -------------------------
    # Callback queries
    # -------------------------
    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> dict[str, Any]:
        self._record(
            "answer_callback_query",
            callback_query_id=callback_query_id,
            text=text,
            show_alert=show_alert,
        )
        return {"ok": True, "result": True}
