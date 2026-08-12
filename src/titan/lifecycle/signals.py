"""
titan.lifecycle.signals

تسجيل وإلغاء معالجات إشارات نظام التشغيل لإغلاق البوت بشكل نظيف.

عند استقبال SIGTERM أو SIGINT، يُلغى الـ task الجاري (run_async)،
فتُشغَّل كتلة finally — نفس مسار الإغلاق الذي تُنشّطه KeyboardInterrupt.

No-op على:
- Windows (لا يدعم loop.add_signal_handler).
- بيئات لا تدعم إضافة signal handlers (subinterpreters، non-main threads).

داخلية — تُستخدم حصراً من titan.bot.Titan.run_async().

ADR-019: Lifecycle Management Layer
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

_log = logging.getLogger("titan")


def install(loop: asyncio.AbstractEventLoop, task: asyncio.Task) -> None:
    """
    تُثبّت معالجات SIGTERM وSIGINT تُلغي *task* عند استقبال الإشارة.

    الإلغاء يُشغّل كتلة finally في run_async() — نفس مسار
    الإغلاق النظيف الذي تُنشّطه KeyboardInterrupt.

    الاستدعاء آمن دائماً: أي بيئة لا تدعم signal handlers تُتجاهل
    الطلب بصمت دون خطأ.
    """
    if sys.platform == "win32":
        return

    def _handle(sig: int) -> None:
        _log.info(
            "Signal %s received — initiating graceful shutdown.",
            signal.Signals(sig).name,
        )
        task.cancel()

    try:
        loop.add_signal_handler(signal.SIGTERM, _handle, signal.SIGTERM)
        loop.add_signal_handler(signal.SIGINT, _handle, signal.SIGINT)
    except (NotImplementedError, RuntimeError):
        # Subinterpreters أو non-main-thread loops لا تدعم signal handlers.
        pass


def uninstall(loop: asyncio.AbstractEventLoop) -> None:
    """
    تُزيل معالجات SIGTERM وSIGINT المُثبَّتة بواسطة install().

    آمنة للاستدعاء حتى لو لم تُستدعَ install() — كما في بيئات Windows.
    """
    if sys.platform == "win32":
        return

    try:
        loop.remove_signal_handler(signal.SIGTERM)
        loop.remove_signal_handler(signal.SIGINT)
    except (NotImplementedError, RuntimeError):
        pass
