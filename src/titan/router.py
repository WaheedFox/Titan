"""
titan.router

أداة تنظيم الكود فقط.

مسؤوليته:
- تجميع تسجيلات handlers في ملف منفصل
- نقلها إلى البوت عبر bot.include()

لا يحتوي على أي منطق تنفيذي.
لا middleware، لا nested routers، لا priorities.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from titan.ctx import Context
from titan.errors import TitanError
from titan.validation import validate_handler


Handler = Callable[[Context], Awaitable[Any]]


class Router:
    """
    أداة تنظيم handlers عبر ملفات متعددة.

    الاستخدام:
        router = Router()

        @router.on("message")
        async def handler(ctx): ...

        @router.command("start")
        async def start(ctx): ...

        @router.callback("yes")
        async def on_yes(ctx): ...

        # في الملف الرئيسي:
        bot.include(router)
    """

    def __init__(self) -> None:
        self.commands: dict[str, Handler] = {}
        self.handlers: dict[str, list[Handler]] = {}
        self.callback_handlers: dict[str, Handler] = {}

    def on(self, event: str):
        """تسجيل handler لحدث معين."""

        def decorator(func: Handler):
            validate_handler(func, kind="event handler")
            self.handlers.setdefault(event, []).append(func)
            return func
        return decorator

    def command(self, name: str):
        """
        تسجيل أمر محدد.

        يرمي TitanError إذا كان الأمر مسجلاً مسبقاً في هذا الـ Router.
        """

        def decorator(func: Handler):
            validate_handler(func, kind="command handler")
            if name in self.commands:
                raise TitanError(
                    f"Command '{name}' is already registered in this router. "
                    "Each command can only have one handler."
                )
            self.commands[name] = func
            return func
        return decorator

    def callback(self, data: str):
        """
        تسجيل handler لزر callback محدد.

        يرمي TitanError إذا كانت الـ data مسجلة مسبقاً في هذا الـ Router.
        """

        def decorator(func: Handler):
            validate_handler(func, kind="callback handler")
            if data in self.callback_handlers:
                raise TitanError(
                    f"Callback data '{data}' is already registered in this router. "
                    "Each callback_data value can only have one handler."
                )
            self.callback_handlers[data] = func
            return func
        return decorator
