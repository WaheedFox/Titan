# ﷽
# Licensed under W.A.S.L v1.0 — github.com/WaheedFox/Titan
"""
titan.validation

التحقق من صحة العقود البرمجية (contracts) عند تسجيل الـ handlers.

المسؤولية:
- التحقق من أن كل callable مُسجَّل يطابق عقد Titan
  (async + عدد المعاملات الصحيح).
- الرفع بـ TitanError الفوري عند أي انتهاك.

لا يُنفَّذ هنا أي منطق تشغيلي — فحص فقط.

---

البنية القابلة للتوسع
---------------------
لإضافة نوع validator جديد (job، filter، event_hook، ...):

    def validate_job(func: Callable[..., Any]) -> None:
        _validate_contract(func, label="job", expected_params=1, signature_hint="(ctx)")

    def validate_filter(func: Callable[..., Any]) -> None:
        _validate_contract(func, label="filter", expected_params=2, signature_hint="(ctx, update)")

لا تكرار في منطق الفحص — فقط تعريف العقد.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

from titan.errors import TitanError


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _callable_name(func: Callable[..., Any]) -> str:
    """اسم الـ callable للاستخدام في رسائل الخطأ."""
    return getattr(func, "__name__", repr(func))


def _is_async(func: Callable[..., Any]) -> bool:
    """
    هل الـ callable دالة async؟

    يدعم:
    - coroutine functions عادية
    - callable objects ذات __call__ async
    """
    if inspect.iscoroutinefunction(func):
        return True
    call = getattr(func, "__call__", None)
    if call is not None and not inspect.isfunction(func) and not inspect.ismethod(func):
        return inspect.iscoroutinefunction(call)
    return False


def _positional_param_count(func: Callable[..., Any]) -> int:
    """
    عدد الـ parameters من نوع POSITIONAL_ONLY أو POSITIONAL_OR_KEYWORD.

    يستثني:
    - self (في callable objects)
    - *args (VAR_POSITIONAL)
    - **kwargs (VAR_KEYWORD)
    - keyword-only parameters

    يرمي TitanError إذا تعذَّر الحصول على التوقيع (C extension مثلاً).
    """
    target = func
    is_callable_object = (
        not inspect.isfunction(func)
        and not inspect.ismethod(func)
        and callable(func)
        and hasattr(func, "__call__")
    )
    if is_callable_object:
        target = func.__call__

    try:
        sig = inspect.signature(target)
    except (ValueError, TypeError):
        raise TitanError(
            f"Cannot inspect the signature of '{_callable_name(func)}'. "
            "Titan requires introspectable callables to enforce the handler contract."
        )

    _POSITIONAL_KINDS = (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )
    return sum(
        1
        for name, p in sig.parameters.items()
        if p.kind in _POSITIONAL_KINDS and name != "self"
    )


def _validate_contract(
    func: Callable[..., Any],
    *,
    label: str,
    expected_params: int,
    signature_hint: str,
) -> None:
    """
    الدالة الداخلية التي تُنفّذ الفحص الفعلي وتُنتج رسائل خطأ موحدة.

    المعاملات:
        label           — وصف نوع التسجيل، مثلاً "command handler" أو "middleware"
        expected_params — عدد الـ parameters المطلوب
        signature_hint  — التوقيع الصحيح، مثلاً "(ctx)" أو "(ctx, next)"

    رسالة الخطأ الناتجة:
        Invalid command handler 'start':
          not async — did you forget 'async def'?
          expected: async def start(ctx): ...
    """
    name = _callable_name(func)
    expected_sig = f"async def {name}{signature_hint}: ..."

    if not _is_async(func):
        raise TitanError(
            f"Invalid {label} '{name}':\n"
            f"  not async — did you forget 'async def'?\n"
            f"  expected: {expected_sig}"
        )

    count = _positional_param_count(func)
    if count != expected_params:
        raise TitanError(
            f"Invalid {label} '{name}':\n"
            f"  wrong number of parameters (got {count}, expected {expected_params})\n"
            f"  expected: {expected_sig}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_handler(func: Callable[..., Any], *, kind: str = "handler") -> None:
    """
    يتحقق من أن الـ callable صالح كـ handler.

    العقد: async، معامل واحد (ctx).

    المعامل الاختياري ``kind`` يُخصّص وصف الخطأ حسب السياق:
        validate_handler(func, kind="command handler")
        validate_handler(func, kind="event handler")
        validate_handler(func, kind="callback handler")

    يرمي TitanError فوراً عند أي انتهاك.
    """
    _validate_contract(func, label=kind, expected_params=1, signature_hint="(ctx)")


def validate_middleware(func: Callable[..., Any]) -> None:
    """
    يتحقق من أن الـ callable صالح كـ middleware.

    العقد: async، معاملان (ctx, next).

    يرمي TitanError فوراً عند أي انتهاك.
    """
    _validate_contract(func, label="middleware", expected_params=2, signature_hint="(ctx, next)")


def validate_error_handler(func: Callable[..., Any]) -> None:
    """
    يتحقق من أن الـ callable صالح كـ error handler.

    العقد: async، معاملان (ctx, exc).

    يرمي TitanError فوراً عند أي انتهاك.
    """
    _validate_contract(func, label="error handler", expected_params=2, signature_hint="(ctx, exc)")
