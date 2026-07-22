"""
titan.update

تحويل بيانات Telegram Update الخام إلى شكل مبسط
يمكن لبقية Titan استخدامه بسهولة.

هذا الملف لا يحتوي على أي منطق للبوت.
فقط استخراج بيانات.

Update نفسها غلاف رقيق فوق نتيجة الترجمة. كل معرفة بشكل JSON الخام
الصادر من Telegram Bot API تعيش في BotApiTranslator أدناه — لا مكان
آخر في Titan يقرأ ذلك الشكل مباشرة.
"""

from __future__ import annotations

from typing import Any, NamedTuple


class ParsedBotApiUpdate(NamedTuple):
    """
    نتيجة ترجمة update خام من Bot API إلى حقول مسطّحة.

    هذا هو الشكل الوحيد الذي تعتمد عليه Update — لا وصول لـ JSON
    الخام بعد هذه النقطة.
    """

    text: str | None
    message_id: int | None
    user_id: int | None
    username: str | None
    chat_id: int | None
    chat_type: str | None
    reply_to_message_id: int | None
    reply_to_sender_is_bot: bool
    callback_data: str | None
    callback_id: str | None


class BotApiTranslator:
    """
    يعرف شكل JSON الخام الصادر من Telegram Bot API تحديداً.

    مسؤوليته الوحيدة: تحديد الرسالة/المستخدم/الشات الفعليين ضمن
    الأشكال المختلفة لـ update (message / channel_post / callback_query)،
    وتحويل ذلك إلى ParsedBotApiUpdate.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

        self.message = raw.get("message")
        self.channel_post = raw.get("channel_post")
        self.callback_query = raw.get("callback_query")

    def get_message(self) -> dict[str, Any] | None:
        if self.message:
            return self.message
        if self.channel_post:
            return self.channel_post
        if self.callback_query:
            return self.callback_query.get("message")
        return None

    def user(self) -> dict[str, Any] | None:
        if self.callback_query:
            return self.callback_query.get("from")

        msg = self.get_message()
        if msg:
            return msg.get("from")

        return None

    def chat(self) -> dict[str, Any] | None:
        msg = self.get_message()
        if msg:
            return msg.get("chat")

        if self.callback_query:
            return self.callback_query.get("message", {}).get("chat")

        return None

    def translate(self) -> ParsedBotApiUpdate:
        msg = self.get_message()
        user = self.user()
        chat = self.chat()

        reply = msg.get("reply_to_message") if msg else None
        reply_sender = reply.get("from", {}) if reply else {}

        return ParsedBotApiUpdate(
            text=msg.get("text") if msg else None,
            message_id=msg.get("message_id") if msg else None,
            user_id=user.get("id") if user else None,
            username=user.get("username") if user else None,
            chat_id=chat.get("id") if chat else None,
            chat_type=chat.get("type") if chat else None,
            reply_to_message_id=reply.get("message_id") if reply else None,
            reply_to_sender_is_bot=(
                bool(reply_sender.get("is_bot", False)) if reply else False
            ),
            callback_data=(
                self.callback_query.get("data") if self.callback_query else None
            ),
            callback_id=(
                self.callback_query.get("id") if self.callback_query else None
            ),
        )


class Update:
    """
    تمثيل مبسط لرسالة Telegram Update.

    الهدف:
    إزالة التعقيد من بنية JSON القادمة من Telegram
    وتحويلها إلى واجهة واضحة وسهلة الاستخدام.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

        translator = BotApiTranslator(raw)
        self.message = translator.message
        self.channel_post = translator.channel_post
        self.callback_query = translator.callback_query

        self._translator = translator
        self._parsed = translator.translate()

    # -------------------------
    # Message resolution
    # -------------------------

    def get_message(self) -> dict[str, Any] | None:
        return self._translator.get_message()

    def _user(self) -> dict[str, Any] | None:
        return self._translator.user()

    def _chat(self) -> dict[str, Any] | None:
        return self._translator.chat()

    # -------------------------
    # Message data
    # -------------------------

    @property
    def text(self) -> str | None:
        return self._parsed.text

    @property
    def message_id(self) -> int | None:
        return self._parsed.message_id

    # -------------------------
    # User data
    # -------------------------

    @property
    def user_id(self) -> int | None:
        return self._parsed.user_id

    @property
    def username(self) -> str | None:
        return self._parsed.username

    # -------------------------
    # Chat data
    # -------------------------

    @property
    def chat_id(self) -> int | None:
        return self._parsed.chat_id

    @property
    def chat_type(self) -> str | None:
        return self._parsed.chat_type

    # -------------------------
    # Callback data
    #
    # (سابقاً: Context كانت تقرأ callback_query.get("data"/"id") مباشرة
    # من raw. أُصلح ضمن Phase 2 — الآن يعبر Update كبقية الحقول.)
    # -------------------------

    @property
    def callback_data(self) -> str | None:
        return self._parsed.callback_data

    @property
    def callback_id(self) -> str | None:
        return self._parsed.callback_id

    # -------------------------
    # Helpers
    # -------------------------

    def is_message(self) -> bool:
        return self.message is not None

    def is_channel_post(self) -> bool:
        return self.channel_post is not None

    def is_callback(self) -> bool:
        return self.callback_query is not None

    def has_text(self) -> bool:
        return self.text is not None

    # -------------------------
    # Reply-to data
    # -------------------------

    @property
    def reply_to_message_id(self) -> int | None:
        """
        معرف Telegram للرسالة التي يرد عليها المستخدم.

        None إذا لم يكن الـ update رداً على رسالة.
        يُستخدم بواسطة /link handler في Message Links Protocol.
        """
        return self._parsed.reply_to_message_id

    @property
    def reply_to_sender_is_bot(self) -> bool:
        """
        هل الرسالة المَردود عليها صادرة من بوت؟

        يُستخدم بواسطة /link handler للتمييز بين رسائل البوت
        ورسائل المستخدمين.
        """
        return self._parsed.reply_to_sender_is_bot

    # -------------------------
    # Export
    # -------------------------

    def to_dict(self) -> dict[str, Any]:
        return self.raw
