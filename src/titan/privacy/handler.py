"""
titan.privacy.handler

Handlers للأوامر المحجوزة /mydata و/forgetme.

ADR-017: Reserved Privacy Commands
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Awaitable, Callable


def _deep_freeze(obj: Any) -> Any:
    """
    تجميد عميق recursive — يمنع أي تعديل على أي مستوى من التقرير.

    dict  → MappingProxyType  (لا يمكن إضافة/حذف/تعديل مفاتيح)
    list  → tuple             (لا يمكن إضافة/حذف/تعديل عناصر)
    غير ذلك → كما هو          (int, str, bool, None — immutable بطبيعتها)

    مثال:
        {"ask": {"questions": ["ما اسمك؟"]}}
        → MappingProxyType({"ask": MappingProxyType({"questions": ("ما اسمك؟",)})})
    """
    if isinstance(obj, dict):
        return MappingProxyType({k: _deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_deep_freeze(item) for item in obj)
    return obj


# -------------------------
# /mydata
# -------------------------

async def handle_mydata_command(
    ctx: Any,
    registry: Any,
    format_hook: Callable[[Any, MappingProxyType], Awaitable[str]] | None = None,
) -> None:
    """
    Handler لأمر /mydata المحجوز.

    1. يجمع البيانات من كل module مُسجَّل عبر registry.data_held_for()
    2. يُجمّد التقرير تجميداً عميقاً (_deep_freeze) — لا تعديل على أي مستوى
    3. يُمرّر للـ format_hook (إن وجد) لتنسيق العرض فقط
    4. يُرسل الرسالة للمستخدم

    المطوّر يتحكم في كيف يُعرض التقرير — لا في ماذا يحتوي.

    التجميد عميق: dict داخلي → MappingProxyType، list داخلية → tuple.
    أي محاولة تعديل على أي مستوى تُثير TypeError من Python مباشرةً.
    """
    if ctx.user_id is None:
        # channel posts ليس لها user_id — الأمر لا معنى له هنا
        return

    raw_data = await registry.data_held_for(ctx.user_id)

    # تجميد عميق — يشمل كل مستويات التقرير
    frozen_report = _deep_freeze(raw_data)

    if format_hook is not None:
        text = await format_hook(ctx, frozen_report)
    else:
        text = _default_mydata_format(raw_data)

    await ctx.reply(text)


def _default_mydata_format(data: dict) -> str:
    """تنسيق افتراضي لتقرير /mydata — يعمل بدون format_hook."""
    if not data:
        return "لا توجد بيانات محفوظة عنك في هذا البوت."

    lines = ["معلوماتك المحفوظة في هذا البوت:\n"]
    for module_name, info in data.items():
        description = info.get("description", module_name)
        count = info.get("count")
        if count is not None:
            lines.append(f"• {description}: {count}")
        else:
            lines.append(f"• {description}")
    return "\n".join(lines)


# -------------------------
# /forgetme
# -------------------------

async def handle_forgetme_command(
    ctx: Any,
    registry: Any,
    complete_hook: Callable[[Any], Awaitable[None]] | None = None,
) -> None:
    """
    Handler لأمر /forgetme المحجوز.

    الترتيب مُثبَّت بالكود — لا يمكن تغييره:

    1. erase_user() — يُنفَّذ أولاً وبالكامل، لا يمكن تخطيه
    2. on_forgetme_complete hook — بعد اكتمال المحو فقط
    3. رسالة تأكيد للمستخدم

    لا on_forgetme_before. لا on_forgetme_condition.
    الغياب قصد — لا سهو.
    """
    if ctx.user_id is None:
        return

    # الخطوة 1: المحو الكامل — لا يمكن لأي hook منعه أو تخطيه
    await registry.erase_user(ctx.user_id)

    # الخطوة 2: hook ما بعد المحو — بعد الاكتمال فقط
    if complete_hook is not None:
        await complete_hook(ctx)

    # الخطوة 3: تأكيد للمستخدم
    await ctx.reply(
        "✓ تم حذف بياناتك المحفوظة في هذا البوت.\n\n"
        "ملاحظة: لا يشمل هذا البيانات التي قد يخزّنها البوت "
        "في أنظمة خارجة عن نطاق Titan."
    )
