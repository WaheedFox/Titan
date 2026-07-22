"""
اختبارات titan.profiler

تتحقق من:
    1. ProfileEntry — نموذج ثابت (frozen)، metadata فارغ في v1
    2. استنتاج event_type من بنية الـ update dict
    3. ProfilingSession.summary() — حسابات صحيحة
    4. profile_update() — يعمل عبر feed_update() فقط
    5. لا اتصال حقيقي بـ Telegram خلال القياس
    6. يُستعاد الـ API الأصلي بعد القياس دائماً
    7. لا أثر على الاختبارات القديمة (عزل تام)
"""

from __future__ import annotations

import pytest

from titan.bot import Titan
from titan.playground import RecordingTelegram, fake_callback, fake_command, fake_message
from titan.profiler import ProfileEntry, ProfilingSession, profile_update
from titan.profiler._run import _infer_event_type


# ===========================================================================
# مساعدات
# ===========================================================================

def make_bot() -> tuple[Titan, RecordingTelegram]:
    bot = Titan("dummy-token")
    api = RecordingTelegram()
    bot._api = api
    bot.telegram._api = api
    return bot, api


# ===========================================================================
# ProfileEntry
# ===========================================================================

class TestProfileEntry:
    def test_is_frozen(self):
        entry = ProfileEntry(event_type="message", duration_ms=5.0)
        with pytest.raises((AttributeError, TypeError)):
            entry.event_type = "command/start"  # type: ignore[misc]

    def test_metadata_defaults_to_empty_dict(self):
        entry = ProfileEntry(event_type="message", duration_ms=5.0)
        assert entry.metadata == {}

    def test_explicit_fields(self):
        entry = ProfileEntry(event_type="command/start", duration_ms=12.4)
        assert entry.event_type == "command/start"
        assert entry.duration_ms == 12.4

    def test_metadata_is_not_part_of_equality(self):
        """metadata مستبعد من compare — القيمتان متساويتان رغم اختلاف metadata."""
        a = ProfileEntry(event_type="message", duration_ms=1.0, metadata={"x": 1})
        b = ProfileEntry(event_type="message", duration_ms=1.0, metadata={})
        assert a == b


# ===========================================================================
# استنتاج event_type
# ===========================================================================

class TestInferEventType:
    def test_command(self):
        assert _infer_event_type(fake_command("start")) == "command/start"

    def test_command_with_at_suffix(self):
        update = fake_command("start")
        update["message"]["text"] = "/start@mybot"
        assert _infer_event_type(update) == "command/start"

    def test_command_with_args(self):
        update = fake_command("start")
        update["message"]["text"] = "/start arg1 arg2"
        assert _infer_event_type(update) == "command/start"

    def test_plain_message(self):
        assert _infer_event_type(fake_message("hello")) == "message"

    def test_callback(self):
        assert _infer_event_type(fake_callback("yes")) == "callback/yes"

    def test_callback_empty_data(self):
        update = fake_callback("")
        assert _infer_event_type(update) == "callback"

    def test_channel_post(self):
        update = {"update_id": 1, "channel_post": {"text": "news"}}
        assert _infer_event_type(update) == "channel"

    def test_new_member(self):
        update = {
            "update_id": 1,
            "message": {"new_chat_members": [{"id": 2}]},
        }
        assert _infer_event_type(update) == "new_member"

    def test_left_member(self):
        update = {
            "update_id": 1,
            "message": {"left_chat_member": {"id": 2}},
        }
        assert _infer_event_type(update) == "left_member"

    def test_callback_takes_priority_over_message(self):
        """callback_query له أولوية على message إن وُجدا معاً."""
        update = fake_callback("ok")
        update["message"] = {"text": "/start"}
        assert _infer_event_type(update).startswith("callback/")

    def test_channel_takes_priority_over_message(self):
        update = {"update_id": 1, "channel_post": {}, "message": {"text": "x"}}
        assert _infer_event_type(update) == "channel"


# ===========================================================================
# ProfilingSession.summary()
# ===========================================================================

class TestProfilingSessionSummary:
    def test_empty_session(self):
        session = ProfilingSession([])
        assert session.summary() == {}

    def test_single_entry(self):
        session = ProfilingSession([
            ProfileEntry(event_type="command/start", duration_ms=10.0),
        ])
        result = session.summary()
        assert result == {
            "command/start": {
                "count": 1,
                "avg_ms": 10.0,
                "min_ms": 10.0,
                "max_ms": 10.0,
            }
        }

    def test_average_correct(self):
        session = ProfilingSession([
            ProfileEntry(event_type="message", duration_ms=10.0),
            ProfileEntry(event_type="message", duration_ms=20.0),
        ])
        s = session.summary()["message"]
        assert s["avg_ms"] == 15.0
        assert s["min_ms"] == 10.0
        assert s["max_ms"] == 20.0
        assert s["count"] == 2

    def test_multiple_event_types(self):
        session = ProfilingSession([
            ProfileEntry(event_type="command/start", duration_ms=5.0),
            ProfileEntry(event_type="message", duration_ms=3.0),
            ProfileEntry(event_type="command/start", duration_ms=7.0),
        ])
        s = session.summary()
        assert s["command/start"]["count"] == 2
        assert s["command/start"]["avg_ms"] == 6.0
        assert s["message"]["count"] == 1

    def test_preserves_insertion_order(self):
        session = ProfilingSession([
            ProfileEntry(event_type="a", duration_ms=1.0),
            ProfileEntry(event_type="b", duration_ms=2.0),
            ProfileEntry(event_type="c", duration_ms=3.0),
        ])
        assert list(session.summary().keys()) == ["a", "b", "c"]

    def test_entries_list_is_copy(self):
        entries = [ProfileEntry(event_type="message", duration_ms=1.0)]
        session = ProfilingSession(entries)
        entries.clear()
        assert len(session.entries) == 1


# ===========================================================================
# profile_update()
# ===========================================================================

class TestProfileUpdate:
    @pytest.mark.asyncio
    async def test_returns_profiling_session(self):
        bot, _ = make_bot()
        session = await profile_update(bot, fake_command("start"))
        assert isinstance(session, ProfilingSession)

    @pytest.mark.asyncio
    async def test_n_equals_one_produces_one_entry(self):
        bot, _ = make_bot()
        session = await profile_update(bot, fake_command("start"), n=1)
        assert len(session.entries) == 1

    @pytest.mark.asyncio
    async def test_n_produces_correct_entry_count(self):
        bot, _ = make_bot()
        session = await profile_update(bot, fake_message("hi"), n=50)
        assert len(session.entries) == 50

    @pytest.mark.asyncio
    async def test_default_n_is_one(self):
        bot, _ = make_bot()
        session = await profile_update(bot, fake_message("hi"))
        assert len(session.entries) == 1

    @pytest.mark.asyncio
    async def test_n_less_than_one_raises(self):
        bot, _ = make_bot()
        with pytest.raises(ValueError, match="n يجب"):
            await profile_update(bot, fake_command("start"), n=0)

    @pytest.mark.asyncio
    async def test_event_type_inferred_from_update(self):
        bot, _ = make_bot()
        session = await profile_update(bot, fake_command("start"), n=3)
        for entry in session.entries:
            assert entry.event_type == "command/start"

    @pytest.mark.asyncio
    async def test_duration_ms_is_positive(self):
        bot, _ = make_bot()
        session = await profile_update(bot, fake_message("hi"), n=5)
        for entry in session.entries:
            assert entry.duration_ms > 0

    @pytest.mark.asyncio
    async def test_metadata_is_empty_in_v1(self):
        bot, _ = make_bot()
        session = await profile_update(bot, fake_message("hi"))
        for entry in session.entries:
            assert entry.metadata == {}

    @pytest.mark.asyncio
    async def test_handler_is_called_during_profiling(self):
        """يثبت أن feed_update() يُشغَّل فعلاً — ليس مجرد قياس فارغ."""
        bot, _ = make_bot()
        call_count = [0]

        @bot.command("start")
        async def on_start(ctx):
            call_count[0] += 1

        await profile_update(bot, fake_command("start"), n=10)
        assert call_count[0] == 10

    @pytest.mark.asyncio
    async def test_no_real_telegram_calls_during_profiling(self):
        """يثبت أن RecordingTelegram يُحقن — لا اتصال حقيقي بـ Telegram."""
        bot, _ = make_bot()

        @bot.on("message")
        async def on_message(ctx):
            await ctx.reply("رد")

        # إذا وصل اتصال حقيقي لـ Telegram ستفشل الاختبارات —
        # RecordingTelegram يسجل بدل إرسال.
        session = await profile_update(bot, fake_message("hi"), n=5)
        assert len(session.entries) == 5

    @pytest.mark.asyncio
    async def test_original_api_restored_after_profiling(self):
        """يُستعاد الـ API الأصلي دائماً بعد انتهاء القياس."""
        bot, original_api = make_bot()
        await profile_update(bot, fake_message("hi"))
        assert bot._api is original_api

    @pytest.mark.asyncio
    async def test_original_api_restored_even_on_handler_exception(self):
        """يُستعاد الـ API الأصلي حتى إذا رفع الـ handler استثناءً."""
        bot, original_api = make_bot()

        @bot.on("message")
        async def boom(ctx):
            raise RuntimeError("خطأ متعمد")

        try:
            await profile_update(bot, fake_message("hi"))
        except Exception:
            pass
        assert bot._api is original_api

    @pytest.mark.asyncio
    async def test_summary_reflects_n_runs(self):
        bot, _ = make_bot()
        session = await profile_update(bot, fake_command("start"), n=20)
        s = session.summary()
        assert s["command/start"]["count"] == 20


# ===========================================================================
# عزل تام — لا تعديل في Core
# ===========================================================================

class TestCoreIsolation:
    def test_bot_py_not_modified(self):
        """
        يثبت أن bot.py لا يعرف بوجود titan.profiler.
        الـ profiler يبني من الخارج — لا import، لا reference.
        """
        import inspect
        from titan import bot as bot_module

        source = inspect.getsource(bot_module)
        assert "profiler" not in source

    def test_profiler_not_exported_from_root(self):
        """
        titan.profiler غير مُصدَّرة من جذر الحزمة —
        الاستيراد يجب أن يكون صريحاً.
        """
        import titan
        assert not hasattr(titan, "profile_update")
        assert not hasattr(titan, "ProfileEntry")
        assert not hasattr(titan, "ProfilingSession")
