"""
titan.lifecycle.runner

PollingRunner — تُدير حلقة long-polling مع Telegram.

المسؤوليات:
- جلب التحديثات عبر get_updates مع exponential backoff.
- توزيع كل تحديث على قائمة chat worker المناسبة أو task مستقل.
- إغلاق الـ workers بشكل نظيف عند الانتهاء.

داخلية — تُستخدم حصراً من titan.bot.Titan.run_async().
لا تُصدَّر كـ Public API.

ADR-019: Lifecycle Management Layer
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable

_log = logging.getLogger("titan")

_BACKOFF_BASE: float = 1.0
_BACKOFF_MAX: float = 30.0

RawUpdateHandler = Callable[[dict[str, Any]], Awaitable[None]]
ChatIdExtractor = Callable[[dict[str, Any]], "int | None"]
QueueEnsurer = Callable[[int], "asyncio.Queue[dict | None]"]
OffsetUpdated = Callable[[int], None]


class PollingRunner:
    """
    تُدير حلقة long-polling مع Telegram.

    تُنشأ داخل Titan.run_async() وتُوجَّه بـ:
    - api: جلسة Telegram النشطة.
    - handle_update: مسار معالجة التحديثات.
    - chat_id_from_raw: استخراج chat_id من raw update.
    - ensure_chat_worker: الحصول على قائمة الـ chat أو إنشاؤها.
    - chat_queues / chat_workers: مراجع مباشرة لحالة البوت — تُنظَّف في shutdown().
    - log: دالة تسجيل مُمرَّرة من Titan.

    التصميم: كل dependency صريحة — لا مشاركة حالة ضمنية مع Titan.
    """

    def __init__(
        self,
        *,
        api: Any,
        handle_update: RawUpdateHandler,
        chat_id_from_raw: ChatIdExtractor,
        ensure_chat_worker: QueueEnsurer,
        chat_queues: dict[int, asyncio.Queue],
        chat_workers: dict[int, asyncio.Task],
        log: Callable[[str], None],
    ) -> None:
        self._api = api
        self._handle_update = handle_update
        self._chat_id_from_raw = chat_id_from_raw
        self._ensure_chat_worker = ensure_chat_worker
        self._chat_queues = chat_queues
        self._chat_workers = chat_workers
        self._log = log

    async def run(
        self,
        *,
        initial_offset: int,
        debug: bool,
        offset_updated: OffsetUpdated | None,
    ) -> None:
        """
        تُشغّل حلقة polling حتى يُلغى الـ task الحالي.

        عند كل تحديث ناجح:
        - يُوزَّع على chat worker (إن وُجد chat_id) أو task مستقل.
        - يُستدعى offset_updated(update_id) لتحديث الـ offset.

        عند خطأ مؤقت: exponential backoff من _BACKOFF_BASE إلى _BACKOFF_MAX.
        CancelledError: تنتشر مباشرةً — لا backoff.
        """
        current_offset = initial_offset
        backoff: float = 0.0

        while True:
            try:
                updates = await self._api.get_updates(offset=current_offset + 1)
                backoff = 0.0

                for raw in updates:
                    update_id = raw.get("update_id")
                    if update_id is None:
                        self._log(f"Skipping update with no update_id: {raw}")
                        continue

                    if debug:
                        self._log(f"update received: {raw}")

                    chat_id = self._chat_id_from_raw(raw)
                    if chat_id is not None:
                        await self._ensure_chat_worker(chat_id).put(raw)
                    else:
                        asyncio.create_task(
                            self._handle_update(raw),
                            name=f"titan-update-{update_id}",
                        )

                    current_offset = update_id

                    if offset_updated is not None:
                        offset_updated(current_offset)

            except Exception as e:
                backoff = min(
                    backoff * 2 if backoff else _BACKOFF_BASE,
                    _BACKOFF_MAX,
                )
                self._log(f"Polling error: {e}. Retrying in {backoff:.0f}s...")
                await asyncio.sleep(backoff)

    async def shutdown(self) -> None:
        """
        إغلاق نظيف لجميع الـ chat workers.

        يُرسل sentinel (None) لكل قائمة ثم ينتظر انتهاء جميع الـ workers.
        يُنظّف chat_queues وchat_workers بعد الانتهاء.
        """
        for queue in self._chat_queues.values():
            await queue.put(None)
        if self._chat_workers:
            await asyncio.gather(
                *self._chat_workers.values(), return_exceptions=True
            )
        self._chat_queues.clear()
        self._chat_workers.clear()
