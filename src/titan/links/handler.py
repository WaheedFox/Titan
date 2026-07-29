"""
titan.links.handler

معالج أمر /link.

يُسجَّل تلقائياً في Titan عند تهيئة البوت.
المطور لا يكتب handler ولا يضيف منطقاً.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from titan.ctx import Context
    from titan.links.manager import LinksManager

_log = logging.getLogger("titan.links")

_MSG_NO_REPLY = (
    "أرسل هذا الأمر كرداً على رسالة البوت للحصول على عنوانها."
)
_MSG_NOT_BOT_MESSAGE = (
    "Message Links Protocol يعمل فقط مع رسائل البوت."
)
_MSG_NO_IDENTITY = (
    "هذه الرسالة أُرسلت قبل تفعيل Message Links Protocol. "
    "لا تملك هوية Titan."
)


async def handle_link_command(ctx: "Context", links: "LinksManager") -> None:
    """
    معالجة أمر /link.

    السيناريوهات:
    - /link بدون رد → يطلب من المستخدم الرد على رسالة البوت.
    - /link رداً على رسالة مستخدم → رسالة غير مدعومة.
    - /link رداً على رسالة بوت قديمة → لا هوية Titan.
    - /link رداً على رسالة بوت مسجّلة → يُعيد TitanMessageAddress.
    """

    reply_id = ctx._update.reply_to_message_id

    if reply_id is None:
        await ctx.reply(_MSG_NO_REPLY)
        return

    if not ctx._update.reply_to_sender_is_bot:
        await ctx.reply(_MSG_NOT_BOT_MESSAGE)
        return

    chat_id = ctx.chat_id
    if chat_id is None:
        _log.warning("handle_link_command: no chat_id in context — skipping.")
        return

    try:
        address = await links.get_address_for_telegram_id(
            chat_id=chat_id,
            telegram_message_id=reply_id,
        )
    except Exception as exc:
        _log.warning("handle_link_command: store lookup failed: %s", exc)
        await ctx.reply("حدث خطأ أثناء البحث عن هوية الرسالة.")
        return

    if address is None:
        await ctx.reply(_MSG_NO_IDENTITY)
        return

    await ctx.reply(str(address))
