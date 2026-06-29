"""  
titan.update  

تحويل بيانات Telegram Update الخام إلى شكل مبسط  
يمكن لبقية Titan استخدامه بسهولة.  

هذا الملف لا يحتوي على أي منطق للبوت.  
فقط استخراج بيانات.  
"""  

from __future__ import annotations  

from typing import Any  


class Update:  
    """  
    تمثيل مبسط لرسالة Telegram Update.  

    الهدف:  
    إزالة التعقيد من بنية JSON القادمة من Telegram  
    وتحويلها إلى واجهة واضحة وسهلة الاستخدام.  
    """  

    def __init__(self, raw: dict[str, Any]) -> None:  
        self.raw = raw  

        self.message = raw.get("message")  
        self.channel_post = raw.get("channel_post")  
        self.callback_query = raw.get("callback_query")  

    # -------------------------
    # Message resolution
    # -------------------------

    def get_message(self) -> dict[str, Any] | None:
        if self.message:
            return self.message
        if self.channel_post:
            return self.channel_post
        if self.callback_query:
            return self.callback_query.get("message")
        return None

    def _user(self) -> dict[str, Any] | None:
        if self.callback_query:
            return self.callback_query.get("from")

        msg = self.get_message()
        if msg:
            return msg.get("from")

        return None

    def _chat(self) -> dict[str, Any] | None:
        msg = self.get_message()  
        if msg:  
            return msg.get("chat")  

        if self.callback_query:  
            return self.callback_query.get("message", {}).get("chat")  

        return None  

    # -------------------------  
    # Message data  
    # -------------------------  

    @property
    def text(self) -> str | None:
        msg = self.get_message()
        return msg.get("text") if msg else None

    @property
    def message_id(self) -> int | None:
        msg = self.get_message()
        return msg.get("message_id") if msg else None

    # -------------------------  
    # User data  
    # -------------------------  

    @property  
    def user_id(self) -> int | None:  
        user = self._user()  
        return user.get("id") if user else None  

    @property  
    def username(self) -> str | None:  
        user = self._user()  
        return user.get("username") if user else None  

    # -------------------------  
    # Chat data  
    # -------------------------  

    @property  
    def chat_id(self) -> int | None:  
        chat = self._chat()  
        return chat.get("id") if chat else None  

    @property  
    def chat_type(self) -> str | None:  
        chat = self._chat()  
        return chat.get("type") if chat else None  

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
    # Export  
    # -------------------------  

    def to_dict(self) -> dict[str, Any]:  
        return self.raw