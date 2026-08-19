"""
اختبارات طبقة Lifecycle Management — ADR-019.

تُغطي:
- PollingRunner: توزيع التحديثات، backoff، الإغلاق.
- signals: install / uninstall لا يُثيران استثناء.
"""

import asyncio
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from titan.lifecycle.runner import PollingRunner
from titan.lifecycle.registry import LifecycleRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw(update_id: int, chat_id: int = 1) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "text": "hi",
            "from": {"id": 1, "username": "u"},
            "chat": {"id": chat_id, "type": "private"},
        },
    }


def _make_runner(
    *,
    updates_sequence: list,
    chat_id_from_raw=None,
    handle_update=None,
    ensure_chat_worker=None,
    chat_queues=None,
    chat_workers=None,
    lifecycle=None,
) -> PollingRunner:
    """ينشئ PollingRunner مع mocks بسيطة."""
    api = MagicMock()
    api.get_updates = AsyncMock(side_effect=updates_sequence)

    if handle_update is None:
        handle_update = AsyncMock()
    if chat_id_from_raw is None:
        chat_id_from_raw = lambda raw: None  # كل التحديثات بدون chat → direct task
    if ensure_chat_worker is None:
        ensure_chat_worker = MagicMock()
    if lifecycle is None:
        lifecycle = LifecycleRegistry()
    if chat_queues is not None:
        lifecycle.chat_queues = chat_queues
    if chat_workers is not None:
        lifecycle.chat_workers = chat_workers

    return PollingRunner(
        api=api,
        handle_update=handle_update,
        chat_id_from_raw=chat_id_from_raw,
        ensure_chat_worker=ensure_chat_worker,
        lifecycle=lifecycle,
        log=lambda msg: None,
    )


# ---------------------------------------------------------------------------
# PollingRunner — التوزيع
# ---------------------------------------------------------------------------

class TestPollingRunnerDispatch:

    @pytest.mark.asyncio
    async def test_polling_tasks_are_owned_by_the_run_registry(self):
        """المهام المباشرة تمر عبر سجل دورة polling المحلي."""
        raw = _make_raw(1)
        cancelled = asyncio.CancelledError()
        lifecycle = LifecycleRegistry()
        handle_update = AsyncMock()

        runner = _make_runner(
            updates_sequence=[[raw], cancelled],
            chat_id_from_raw=lambda r: None,
            handle_update=handle_update,
            lifecycle=lifecycle,
        )

        with pytest.raises(asyncio.CancelledError):
            await runner.run(initial_offset=0, debug=False, offset_updated=None)

        await asyncio.sleep(0)
        assert len(lifecycle.tasks) == 1
        assert lifecycle.handler_tasks == lifecycle.tasks
        task = next(iter(lifecycle.handler_tasks))
        assert task.get_name() == "titan-update-1"

        await task
        handle_update.assert_awaited_once_with(raw)
        assert task.done()

    @pytest.mark.asyncio
    async def test_update_without_chat_creates_direct_task(self):
        """تحديث بدون chat_id → asyncio.create_task مباشرةً."""
        raw = _make_raw(1)
        cancelled = asyncio.CancelledError()

        runner = _make_runner(
            updates_sequence=[[raw], cancelled],
            chat_id_from_raw=lambda r: None,
        )

        with pytest.raises(asyncio.CancelledError):
            await runner.run(initial_offset=0, debug=False, offset_updated=None)

    @pytest.mark.asyncio
    async def test_update_with_chat_enqueues_to_worker(self):
        """تحديث بـ chat_id → يُضاف إلى قائمة الـ chat."""
        raw = _make_raw(1, chat_id=42)
        queue = asyncio.Queue()
        cancelled = asyncio.CancelledError()

        ensure_chat_worker = MagicMock(return_value=queue)

        runner = _make_runner(
            updates_sequence=[[raw], cancelled],
            chat_id_from_raw=lambda r: r.get("message", {}).get("chat", {}).get("id"),
            ensure_chat_worker=ensure_chat_worker,
        )

        with pytest.raises(asyncio.CancelledError):
            await runner.run(initial_offset=0, debug=False, offset_updated=None)

        ensure_chat_worker.assert_called_once_with(42)
        assert not queue.empty()

    @pytest.mark.asyncio
    async def test_offset_updated_called_for_each_update(self):
        """offset_updated يُستدعى لكل تحديث مع update_id الصحيح."""
        raws = [_make_raw(i) for i in range(1, 4)]
        cancelled = asyncio.CancelledError()
        collected: list[int] = []

        runner = _make_runner(
            updates_sequence=[raws, cancelled],
        )

        with pytest.raises(asyncio.CancelledError):
            await runner.run(
                initial_offset=0,
                debug=False,
                offset_updated=lambda ofs: collected.append(ofs),
            )

        assert collected == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_update_with_no_update_id_is_skipped(self):
        """تحديث بدون update_id يُتجاهَل بصمت — لا crash."""
        raw_invalid = {"message": {"text": "hi"}}   # no update_id
        cancelled = asyncio.CancelledError()
        collected: list[int] = []

        runner = _make_runner(
            updates_sequence=[[raw_invalid], cancelled],
        )

        with pytest.raises(asyncio.CancelledError):
            await runner.run(
                initial_offset=0,
                debug=False,
                offset_updated=lambda ofs: collected.append(ofs),
            )

        assert collected == []   # لم يُحدَّث الـ offset


# ---------------------------------------------------------------------------
# PollingRunner — Backoff
# ---------------------------------------------------------------------------

class TestPollingRunnerBackoff:

    @pytest.mark.asyncio
    async def test_backoff_on_transient_error(self):
        """خطأ مؤقت → asyncio.sleep يُستدعى، ثم تُستأنف الحلقة."""
        raw = _make_raw(1)
        cancelled = asyncio.CancelledError()

        runner = _make_runner(
            updates_sequence=[RuntimeError("network"), [raw], cancelled],
        )

        with patch("titan.lifecycle.runner.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(asyncio.CancelledError):
                await runner.run(initial_offset=0, debug=False, offset_updated=None)

        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert sleep_duration > 0

    @pytest.mark.asyncio
    async def test_backoff_resets_after_success(self):
        """backoff يرجع إلى صفر بعد نجاح get_updates."""
        raw = _make_raw(1)
        cancelled = asyncio.CancelledError()

        # خطأ → نجاح → خطأ → تأكيد أن backoff بدأ من البداية مرة ثانية
        sleep_durations: list[float] = []

        runner = _make_runner(
            updates_sequence=[
                RuntimeError("first error"),
                [raw],
                RuntimeError("second error"),
                cancelled,
            ],
        )

        async def mock_sleep(duration: float) -> None:
            sleep_durations.append(duration)

        with patch("titan.lifecycle.runner.asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(asyncio.CancelledError):
                await runner.run(initial_offset=0, debug=False, offset_updated=None)

        assert len(sleep_durations) == 2
        # الـ backoff الثاني يبدأ من _BACKOFF_BASE — لا يتراكم من السابق
        from titan.lifecycle.runner import _BACKOFF_BASE
        assert sleep_durations[1] == _BACKOFF_BASE


# ---------------------------------------------------------------------------
# PollingRunner — Shutdown
# ---------------------------------------------------------------------------

class TestPollingRunnerShutdown:

    @pytest.mark.asyncio
    async def test_shutdown_sends_sentinel_and_drains(self):
        """shutdown() يُرسل None لكل قائمة وينتظر انتهاء الـ workers."""
        queue: asyncio.Queue = asyncio.Queue()

        sentinel_received: list[bool] = []

        async def fake_worker():
            item = await queue.get()
            sentinel_received.append(item is None)

        task = asyncio.create_task(fake_worker())
        chat_queues = {1: queue}
        chat_workers = {1: task}

        runner = _make_runner(
            updates_sequence=[],
            chat_queues=chat_queues,
            chat_workers=chat_workers,
        )

        await runner.shutdown()

        assert sentinel_received == [True]
        assert chat_queues == {}
        assert chat_workers == {}

    @pytest.mark.asyncio
    async def test_shutdown_clears_state(self):
        """shutdown() يُفرّغ chat_queues وchat_workers."""
        chat_queues: dict = {1: asyncio.Queue(), 2: asyncio.Queue()}

        async def dummy():
            await asyncio.sleep(0)

        chat_workers: dict = {
            1: asyncio.create_task(dummy()),
            2: asyncio.create_task(dummy()),
        }

        runner = _make_runner(
            updates_sequence=[],
            chat_queues=chat_queues,
            chat_workers=chat_workers,
        )

        await runner.shutdown()

        assert chat_queues == {}
        assert chat_workers == {}


# ---------------------------------------------------------------------------
# signals — install / uninstall
# ---------------------------------------------------------------------------

class TestSignals:

    def test_install_and_uninstall_do_not_raise(self):
        """install() وuninstall() لا يُثيران استثناء في أي بيئة."""
        from titan.lifecycle import signals

        loop = asyncio.new_event_loop()
        try:
            # MagicMock كافٍ — signals.install تستدعي task.cancel() فقط،
            # ولا تحتاج asyncio.Task حقيقياً.
            task = MagicMock()
            signals.install(loop, task)
            signals.uninstall(loop)
        finally:
            loop.close()

    def test_uninstall_without_install_does_not_raise(self):
        """uninstall() قبل install() آمنة تماماً."""
        from titan.lifecycle import signals

        loop = asyncio.new_event_loop()
        try:
            signals.uninstall(loop)  # لا استثناء
        finally:
            loop.close()
