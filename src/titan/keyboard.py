"""
titan.keyboard

أدوات بناء لوحات المفاتيح لـ Telegram.

الهدف:
- واجهة row-based واضحة وقابلة للقراءة
- لا يحتاج المستخدم استيراد أي شيء إضافي
- متوافق مع ctx.reply(reply_markup=...)
"""

from __future__ import annotations

from typing import Any


class InlineButton:
    """
    زر واحد داخل InlineKeyboard.

    المعاملات:
    - text: نص الزر
    - callback_data: البيانات التي تُرسل عند الضغط (لـ @bot.callback)
    - url: رابط يُفتح عند الضغط
    """

    def __init__(
        self,
        text: str,
        *,
        callback_data: str | None = None,
        url: str | None = None,
    ) -> None:
        self.text = text
        self.callback_data = callback_data
        self.url = url

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"text": self.text}

        if self.callback_data is not None:
            data["callback_data"] = self.callback_data

        if self.url is not None:
            data["url"] = self.url

        return data


class InlineKeyboard:
    """
    لوحة مفاتيح Inline تُبنى بصفوف واضحة.

    النمط الرسمي:
        `.button()` يضيف زراً للصف الحالي.
        `.row()` يفصل بين صفين — يُستدعى بين الأزرار، لا قبلها.

    مثال:
        kb = (
            InlineKeyboard()
            .button("✅ موافق", callback_data="yes")
            .button("❌ رفض", callback_data="no")
            .row()
            .button("🔗 رابط", url="https://example.com")
        )

        await ctx.reply("اختر:", reply_markup=kb)
    """

    def __init__(self) -> None:
        self._rows: list[list[InlineButton]] = []

    # -------------------------
    # Building
    # -------------------------

    def row(self) -> InlineKeyboard:
        """بدء صف جديد من الأزرار."""

        self._rows.append([])
        return self

    def button(
        self,
        text: str,
        *,
        callback_data: str | None = None,
        url: str | None = None,
    ) -> InlineKeyboard:
        """
        إضافة زر للصف الحالي.

        يجب استدعاء .row() قبل أول .button().

        المعاملات:
        - text: نص الزر
        - callback_data: البيانات التي تُرسل عند الضغط (لـ @bot.callback)
        - url: رابط يُفتح عند الضغط
        """

        if not self._rows:
            self._rows.append([])

        btn = InlineButton(text, callback_data=callback_data, url=url)
        self._rows[-1].append(btn)
        return self

    # -------------------------
    # Export
    # -------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [btn.to_dict() for btn in row]
                for row in self._rows
                if row
            ]
        }
