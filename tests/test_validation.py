# ﷽
"""
اختبارات validate_handler / validate_middleware / validate_error_handler

تغطي:
- الحالات الصحيحة (لا استثناء)
- sync بدون async
- عدد parameters خاطئ
- callable objects (async __call__)
- التكامل مع bot.command / bot.on / bot.callback /
  bot.middleware / bot.error_handler / router.command /
  router.on / router.callback
"""

import pytest

from titan.errors import TitanError
from titan.validation import (
    validate_handler,
    validate_middleware,
    validate_error_handler,
)
from titan.bot import Titan
from titan.router import Router


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def bot(monkeypatch):
    """Titan instance بدون اتصال حقيقي."""
    monkeypatch.setenv("TITAN_TEST", "1")
    return Titan("fake:token")


@pytest.fixture()
def router():
    return Router()


# ===========================================================================
# validate_handler — الحالات الصحيحة
# ===========================================================================

class TestValidateHandlerValid:
    def test_simple_async_one_param(self):
        async def handler(ctx): ...
        validate_handler(handler)

    def test_positional_only(self):
        # Python 3.8+ positional-only syntax
        exec(
            "async def h(ctx, /): pass\nvalidate_handler(h)",
            {"validate_handler": validate_handler},
        )

    def test_one_positional_plus_kwargs(self):
        async def handler(ctx, **kwargs): ...
        validate_handler(handler)

    def test_callable_object_async_call(self):
        class H:
            async def __call__(self, ctx): ...

        validate_handler(H())

    def test_callable_object_extra_kwargs_allowed(self):
        class H:
            async def __call__(self, ctx, **kw): ...

        validate_handler(H())


# ===========================================================================
# validate_handler — sync
# ===========================================================================

class TestValidateHandlerSync:
    def test_plain_sync(self):
        def handler(ctx): ...
        with pytest.raises(TitanError, match="async"):
            validate_handler(handler)

    def test_sync_no_params(self):
        def handler(): ...
        with pytest.raises(TitanError, match="async"):
            validate_handler(handler)

    def test_callable_object_sync_call(self):
        class H:
            def __call__(self, ctx): ...

        with pytest.raises(TitanError, match="async"):
            validate_handler(H())


# ===========================================================================
# validate_handler — parameter count
# ===========================================================================

class TestValidateHandlerParamCount:
    def test_zero_params(self):
        async def handler(): ...
        with pytest.raises(TitanError, match="expected 1"):
            validate_handler(handler)

    def test_two_params(self):
        async def handler(ctx, extra): ...
        with pytest.raises(TitanError, match="expected 1"):
            validate_handler(handler)

    def test_three_params(self):
        async def handler(a, b, c): ...
        with pytest.raises(TitanError, match="expected 1"):
            validate_handler(handler)

    def test_callable_object_zero_positional_after_self(self):
        class H:
            async def __call__(self): ...

        with pytest.raises(TitanError, match="expected 1"):
            validate_handler(H())

    def test_callable_object_two_positional_after_self(self):
        class H:
            async def __call__(self, ctx, extra): ...

        with pytest.raises(TitanError, match="expected 1"):
            validate_handler(H())


# ===========================================================================
# validate_middleware — الحالات الصحيحة
# ===========================================================================

class TestValidateMiddlewareValid:
    def test_simple_async_two_params(self):
        async def mw(ctx, next): ...
        validate_middleware(mw)

    def test_two_positional_plus_kwargs(self):
        async def mw(ctx, next, **kw): ...
        validate_middleware(mw)

    def test_callable_object(self):
        class M:
            async def __call__(self, ctx, next): ...

        validate_middleware(M())


# ===========================================================================
# validate_middleware — sync
# ===========================================================================

class TestValidateMiddlewareSync:
    def test_plain_sync(self):
        def mw(ctx, next): ...
        with pytest.raises(TitanError, match="async"):
            validate_middleware(mw)

    def test_callable_object_sync(self):
        class M:
            def __call__(self, ctx, next): ...

        with pytest.raises(TitanError, match="async"):
            validate_middleware(M())


# ===========================================================================
# validate_middleware — parameter count
# ===========================================================================

class TestValidateMiddlewareParamCount:
    def test_one_param(self):
        async def mw(ctx): ...
        with pytest.raises(TitanError, match="expected 2"):
            validate_middleware(mw)

    def test_zero_params(self):
        async def mw(): ...
        with pytest.raises(TitanError, match="expected 2"):
            validate_middleware(mw)

    def test_three_params(self):
        async def mw(ctx, next, extra): ...
        with pytest.raises(TitanError, match="expected 2"):
            validate_middleware(mw)

    def test_callable_object_one_param_after_self(self):
        class M:
            async def __call__(self, ctx): ...

        with pytest.raises(TitanError, match="expected 2"):
            validate_middleware(M())


# ===========================================================================
# validate_error_handler — الحالات الصحيحة
# ===========================================================================

class TestValidateErrorHandlerValid:
    def test_simple_async_two_params(self):
        async def on_error(ctx, exc): ...
        validate_error_handler(on_error)

    def test_two_positional_plus_kwargs(self):
        async def on_error(ctx, exc, **kw): ...
        validate_error_handler(on_error)

    def test_callable_object(self):
        class E:
            async def __call__(self, ctx, exc): ...

        validate_error_handler(E())


# ===========================================================================
# validate_error_handler — sync
# ===========================================================================

class TestValidateErrorHandlerSync:
    def test_plain_sync(self):
        def on_error(ctx, exc): ...
        with pytest.raises(TitanError, match="async"):
            validate_error_handler(on_error)


# ===========================================================================
# validate_error_handler — parameter count
# ===========================================================================

class TestValidateErrorHandlerParamCount:
    def test_one_param(self):
        async def on_error(ctx): ...
        with pytest.raises(TitanError, match="expected 2"):
            validate_error_handler(on_error)

    def test_three_params(self):
        async def on_error(ctx, exc, extra): ...
        with pytest.raises(TitanError, match="expected 2"):
            validate_error_handler(on_error)


# ===========================================================================
# Error messages — تحتوي اسم الدالة
# ===========================================================================

class TestErrorMessages:
    def test_handler_error_contains_function_name(self):
        def my_special_handler(ctx): ...
        with pytest.raises(TitanError, match="my_special_handler"):
            validate_handler(my_special_handler)

    def test_middleware_error_contains_function_name(self):
        def my_special_middleware(ctx): ...
        with pytest.raises(TitanError, match="my_special_middleware"):
            validate_middleware(my_special_middleware)

    def test_error_handler_error_contains_function_name(self):
        def my_special_error_handler(ctx): ...
        with pytest.raises(TitanError, match="my_special_error_handler"):
            validate_error_handler(my_special_error_handler)


# ===========================================================================
# Integration — Bot decorators يرفضون الـ callables غير الصالحة
# ===========================================================================

class TestBotIntegrationRejects:
    def test_command_rejects_sync(self, bot):
        with pytest.raises(TitanError, match="async"):
            @bot.command("start")
            def start(ctx): ...

    def test_command_rejects_wrong_params(self, bot):
        with pytest.raises(TitanError, match="expected 1"):
            @bot.command("start")
            async def start(ctx, extra): ...

    def test_on_rejects_sync(self, bot):
        with pytest.raises(TitanError, match="async"):
            @bot.on("message")
            def handler(ctx): ...

    def test_on_rejects_wrong_params(self, bot):
        with pytest.raises(TitanError, match="expected 1"):
            @bot.on("message")
            async def handler(): ...

    def test_callback_rejects_sync(self, bot):
        with pytest.raises(TitanError, match="async"):
            @bot.callback("yes")
            def on_yes(ctx): ...

    def test_callback_rejects_wrong_params(self, bot):
        with pytest.raises(TitanError, match="expected 1"):
            @bot.callback("yes")
            async def on_yes(ctx, extra): ...

    def test_middleware_rejects_sync(self, bot):
        with pytest.raises(TitanError, match="async"):
            @bot.middleware
            def guard(ctx, next): ...

    def test_middleware_rejects_one_param(self, bot):
        with pytest.raises(TitanError, match="expected 2"):
            @bot.middleware
            async def guard(ctx): ...

    def test_error_handler_rejects_sync(self, bot):
        with pytest.raises(TitanError, match="async"):
            @bot.error_handler
            def on_error(ctx, exc): ...

    def test_error_handler_rejects_one_param(self, bot):
        with pytest.raises(TitanError, match="expected 2"):
            @bot.error_handler
            async def on_error(ctx): ...


# ===========================================================================
# Integration — Bot decorators يقبلون الـ callables الصالحة
# ===========================================================================

class TestBotIntegrationAccepts:
    def test_command_accepts_valid(self, bot):
        @bot.command("start")
        async def start(ctx): ...
        assert "start" in bot.commands

    def test_on_accepts_valid(self, bot):
        @bot.on("message")
        async def handler(ctx): ...
        assert "message" in bot.handlers

    def test_callback_accepts_valid(self, bot):
        @bot.callback("yes")
        async def on_yes(ctx): ...
        assert "yes" in bot.callback_handlers

    def test_middleware_accepts_valid(self, bot):
        @bot.middleware
        async def guard(ctx, next): ...
        assert bot.middleware_chain.count == 1

    def test_error_handler_accepts_valid(self, bot):
        @bot.error_handler
        async def on_error(ctx, exc): ...
        assert bot._error_handler is not None

    def test_command_accepts_callable_object(self, bot):
        class StartHandler:
            async def __call__(self, ctx): ...

        bot.command("start")(StartHandler())
        assert "start" in bot.commands

    def test_middleware_accepts_callable_object(self, bot):
        class GuardMiddleware:
            async def __call__(self, ctx, next): ...

        bot.middleware(GuardMiddleware())
        assert bot.middleware_chain.count == 1


# ===========================================================================
# Integration — Router decorators يرفضون الـ callables غير الصالحة
# ===========================================================================

class TestRouterIntegrationRejects:
    def test_command_rejects_sync(self, router):
        with pytest.raises(TitanError, match="async"):
            @router.command("start")
            def start(ctx): ...

    def test_command_rejects_wrong_params(self, router):
        with pytest.raises(TitanError, match="expected 1"):
            @router.command("start")
            async def start(): ...

    def test_on_rejects_sync(self, router):
        with pytest.raises(TitanError, match="async"):
            @router.on("message")
            def handler(ctx): ...

    def test_on_rejects_wrong_params(self, router):
        with pytest.raises(TitanError, match="expected 1"):
            @router.on("message")
            async def handler(ctx, extra): ...

    def test_callback_rejects_sync(self, router):
        with pytest.raises(TitanError, match="async"):
            @router.callback("yes")
            def on_yes(ctx): ...

    def test_callback_rejects_wrong_params(self, router):
        with pytest.raises(TitanError, match="expected 1"):
            @router.callback("yes")
            async def on_yes(ctx, extra): ...


# ===========================================================================
# Integration — Router decorators يقبلون الـ callables الصالحة
# ===========================================================================

class TestRouterIntegrationAccepts:
    def test_command_accepts_valid(self, router):
        @router.command("start")
        async def start(ctx): ...
        assert "start" in router.commands

    def test_on_accepts_valid(self, router):
        @router.on("message")
        async def handler(ctx): ...
        assert "message" in router.handlers

    def test_callback_accepts_valid(self, router):
        @router.callback("yes")
        async def on_yes(ctx): ...
        assert "yes" in router.callback_handlers

    def test_callable_object_on_router_command(self, router):
        class StartHandler:
            async def __call__(self, ctx): ...

        router.command("start")(StartHandler())
        assert "start" in router.commands


# ===========================================================================
# Fail at import time — التحقق يحدث عند تنفيذ الـ decorator لا عند run()
# ===========================================================================

class TestFailAtDecoratorTime:
    """يتأكد أن الخطأ يُرفع في لحظة التسجيل وليس لاحقاً."""

    def test_command_fails_immediately_not_at_run(self, bot):
        raised = False
        try:
            @bot.command("bad")
            def bad_handler(ctx): ...
        except TitanError:
            raised = True

        assert raised, "يجب أن يُرفع TitanError عند تنفيذ الـ decorator"
        # الأمر لم يُسجَّل
        assert "bad" not in bot.commands

    def test_middleware_fails_immediately(self, bot):
        raised = False
        try:
            @bot.middleware
            def bad_mw(ctx, next): ...
        except TitanError:
            raised = True

        assert raised
        assert bot.middleware_chain.count == 0


# ===========================================================================
# Validation أسبق من التحقق من التعارض
# ===========================================================================

class TestValidationBeforeConflict:
    """إذا كان الـ handler غير صالح وهناك تعارض، الخطأ يجب أن يكون عن العقد لا التعارض."""

    def test_invalid_handler_registered_first_then_conflict(self, bot):
        @bot.command("start")
        async def start(ctx): ...

        # محاولة تسجيل handler sync على أمر موجود
        # الخطأ يجب أن يكون عن async لا عن التعارض
        with pytest.raises(TitanError, match="async"):
            @bot.command("start")
            def start_sync(ctx): ...


# ===========================================================================
# Error message — kind يظهر بوضوح في رسالة الخطأ
# ===========================================================================

class TestErrorMessageKind:
    """يتحقق أن نوع التسجيل (kind) يظهر في الرسالة ليعرف المطور أين الخطأ بالضبط."""

    def test_command_handler_kind_in_message(self, bot):
        with pytest.raises(TitanError, match="command handler"):
            @bot.command("start")
            def start(ctx): ...

    def test_event_handler_kind_in_message(self, bot):
        with pytest.raises(TitanError, match="event handler"):
            @bot.on("message")
            def handler(ctx): ...

    def test_callback_handler_kind_in_message(self, bot):
        with pytest.raises(TitanError, match="callback handler"):
            @bot.callback("yes")
            def on_yes(ctx): ...

    def test_middleware_kind_in_message(self, bot):
        with pytest.raises(TitanError, match="middleware"):
            @bot.middleware
            def guard(ctx, next): ...

    def test_error_handler_kind_in_message(self, bot):
        with pytest.raises(TitanError, match="error handler"):
            @bot.error_handler
            def on_error(ctx, exc): ...

    def test_router_command_kind_in_message(self, router):
        with pytest.raises(TitanError, match="command handler"):
            @router.command("start")
            def start(ctx): ...

    def test_router_event_kind_in_message(self, router):
        with pytest.raises(TitanError, match="event handler"):
            @router.on("message")
            def handler(ctx): ...

    def test_router_callback_kind_in_message(self, router):
        with pytest.raises(TitanError, match="callback handler"):
            @router.callback("yes")
            def on_yes(ctx): ...

    def test_custom_kind_propagates(self):
        """validate_handler يقبل kind مخصصاً للاستخدامات المستقبلية."""
        async def hook(ctx): ...
        # يجب أن لا يرمي — الـ callable صالح
        validate_handler(hook, kind="plugin hook")

    def test_custom_kind_appears_in_error(self):
        def bad_hook(ctx): ...
        with pytest.raises(TitanError, match="plugin hook"):
            validate_handler(bad_hook, kind="plugin hook")

    def test_expected_signature_hint_in_message(self):
        """رسالة الخطأ تحتوي التوقيع الصحيح كـ hint."""
        async def handler(ctx, extra): ...
        with pytest.raises(TitanError) as exc_info:
            validate_handler(handler)
        assert "async def handler(ctx): ..." in str(exc_info.value)

    def test_middleware_hint_in_message(self):
        async def guard(ctx): ...
        with pytest.raises(TitanError) as exc_info:
            validate_middleware(guard)
        assert "async def guard(ctx, next): ..." in str(exc_info.value)

    def test_error_handler_hint_in_message(self):
        async def on_error(ctx): ...
        with pytest.raises(TitanError) as exc_info:
            validate_error_handler(on_error)
        assert "async def on_error(ctx, exc): ..." in str(exc_info.value)


# ===========================================================================
# Error message — f-string interpolation صحيح
# ===========================================================================

class TestErrorMessageInterpolation:
    """يتحقق أن اسم الدالة يظهر في رسالة الخطأ المتوقعة وليس {name} حرفياً."""

    def test_handler_expected_signature_contains_real_name(self):
        async def my_handler(): ...
        with pytest.raises(TitanError) as exc_info:
            validate_handler(my_handler)
        msg = str(exc_info.value)
        assert "{name}" not in msg, "رسالة الخطأ تحتوي {name} حرفياً بدلاً من اسم الدالة"
        assert "my_handler" in msg

    def test_middleware_expected_signature_contains_real_name(self):
        async def my_mw(ctx): ...
        with pytest.raises(TitanError) as exc_info:
            validate_middleware(my_mw)
        msg = str(exc_info.value)
        assert "{name}" not in msg
        assert "my_mw" in msg

    def test_error_handler_expected_signature_contains_real_name(self):
        async def my_err(ctx): ...
        with pytest.raises(TitanError) as exc_info:
            validate_error_handler(my_err)
        msg = str(exc_info.value)
        assert "{name}" not in msg
        assert "my_err" in msg


# ===========================================================================
# bot.include() — يتحقق دفاعياً من handlers المُضافة مباشرةً للـ dict
# ===========================================================================

class TestIncludeDefensiveValidation:
    """
    يُغطي حالة تجاوز التحقق بحقن handler مباشرة في router dict
    ثم تمرير الـ router لـ bot.include().
    """

    def test_include_rejects_sync_handler_in_router_commands(self, bot, router):
        def bad_command(ctx): ...
        # حقن مباشر في dict بتجاوز decorator
        router.commands["bad"] = bad_command

        with pytest.raises(TitanError, match="async"):
            bot.include(router)

    def test_include_rejects_sync_handler_in_router_on(self, bot, router):
        def bad_event(ctx): ...
        router.handlers["message"] = [bad_event]

        with pytest.raises(TitanError, match="async"):
            bot.include(router)

    def test_include_rejects_sync_handler_in_router_callback(self, bot, router):
        def bad_cb(ctx): ...
        router.callback_handlers["yes"] = bad_cb

        with pytest.raises(TitanError, match="async"):
            bot.include(router)
