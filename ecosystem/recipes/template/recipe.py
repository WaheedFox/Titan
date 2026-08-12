"""
titan_recipe_<name>

استبدل ExampleRecipe بالاسم الفعلي لوصفتك، و<name> في اسم الحزمة.

مثال على الاستخدام:
    from titan_recipe_<name> import ExampleRecipe

    handler = ExampleRecipe()

    @bot.on("message")
    async def handle(ctx):
        await handler(ctx)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from titan.ctx import Context

__all__ = ["ExampleRecipe"]


class ExampleRecipe:
    """
    وصف مختصر لما تفعله الوصفة.

    Args:
        أضف معاملات التهيئة هنا.
    """

    def __init__(self) -> None:
        # احفظ المعاملات فقط. لا سلوك هنا.
        pass

    async def __call__(self, ctx: "Context") -> None:
        # المنطق الرئيسي للوصفة.
        # استخدم ctx.reply() أو ctx.send() أو ctx.answer_callback() إلخ.
        pass
