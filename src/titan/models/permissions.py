"""
models.permissions

تمثيل صلاحيات البوت في شات محدد.

البيانات مصدرها getChatMember — ديناميكية ومرتبطة بالشات الحالي.
لا علاقة لها بقدرات البوت على مستوى الحساب.

يُكشَف هذا النموذج عبر ctx.permissions بعد استدعاء ctx.fetch_permissions().
"""

from __future__ import annotations

from typing import Any


class ChatPermissions:
    """
    صلاحيات البوت في الشات الحالي، مستخرجة من استجابة getChatMember.

    هذه الصلاحيات سياقية — مرتبطة بشات محدد وقابلة للتغيير.
    قيمة كل صلاحية هي False إذا لم يكن البوت مشرفاً أو لم تُمنَح له.

    لا تُنشئ هذا الكائن مباشرةً — استخدم ctx.fetch_permissions().
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    # -------------------------
    # General admin permissions
    # -------------------------

    @property
    def can_manage_chat(self) -> bool:
        """إدارة الشات بشكل عام."""
        return self.raw.get("can_manage_chat", False)

    @property
    def can_delete_messages(self) -> bool:
        """حذف رسائل الأعضاء."""
        return self.raw.get("can_delete_messages", False)

    @property
    def can_manage_video_chats(self) -> bool:
        """إدارة المكالمات المرئية."""
        return self.raw.get("can_manage_video_chats", False)

    @property
    def can_restrict_members(self) -> bool:
        """تقييد صلاحيات الأعضاء."""
        return self.raw.get("can_restrict_members", False)

    @property
    def can_promote_members(self) -> bool:
        """ترقية الأعضاء إلى مشرفين."""
        return self.raw.get("can_promote_members", False)

    @property
    def can_change_info(self) -> bool:
        """تغيير معلومات الشات (الاسم، الصورة، إلخ)."""
        return self.raw.get("can_change_info", False)

    @property
    def can_invite_users(self) -> bool:
        """دعوة مستخدمين جدد."""
        return self.raw.get("can_invite_users", False)

    # -------------------------
    # Group-specific
    # -------------------------

    @property
    def can_pin_messages(self) -> bool:
        """تثبيت الرسائل. متاح في المجموعات فقط."""
        return self.raw.get("can_pin_messages", False)

    @property
    def can_manage_topics(self) -> bool:
        """إدارة المواضيع. متاح في مجموعات Forum فقط."""
        return self.raw.get("can_manage_topics", False)

    # -------------------------
    # Channel-specific
    # -------------------------

    @property
    def can_post_messages(self) -> bool:
        """نشر رسائل في القناة. متاح في القنوات فقط."""
        return self.raw.get("can_post_messages", False)

    @property
    def can_edit_messages(self) -> bool:
        """تعديل رسائل القناة. متاح في القنوات فقط."""
        return self.raw.get("can_edit_messages", False)

    # -------------------------
    # Export
    # -------------------------

    def to_dict(self) -> dict[str, Any]:
        return self.raw
