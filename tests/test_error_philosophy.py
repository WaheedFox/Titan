"""
test_error_philosophy.py

فلسفة Titan للأخطاء — التحقق من المبدأ نفسه، وليس النصوص.

ثلاثة مبادئ يجب أن تصمد دائماً:

1. Hard Contract لا يصمت.
   كل method تنتمي حصرياً لسياق واحد يجب أن ترفع TitanError عند استخدامها
   خارج ذلك السياق — ولا تُعيد None بصمت.

2. Primary action لا يفشل بصمت.
   كل عملية جوهرية (reply, send, edit, delete, ban, leave) يجب أن تُسجّل
   تحذيراً مرئياً عند غياب شرطها المسبق — ولا تختفي بصمت.

3. Best-Effort لا يُطلق استثناءات.
   العمليات الجانبية (typing) يجب ألا ترفع استثناءات عند غياب شرطها المسبق.
"""

import logging
import pytest
from unittest.mock import AsyncMock, MagicMock

from titan.ctx import Context
from titan.update import Update
from titan.errors import TitanError


# -------------------------
# Shared fixtures
# -------------------------

def make_api():
    api = MagicMock()
    api.send_message = AsyncMock(return_value={"ok": True})
    api.edit_message_text = AsyncMock(return_value={"ok": True})
    api.delete_message = AsyncMock(return_value={"ok": True})
    api.ban_user = AsyncMock(return_value={"ok": True})
    api.leave_chat = AsyncMock(return_value={"ok": True})
    api.answer_callback_query = AsyncMock(return_value={"ok": True})
    api.send_chat_action = AsyncMock(return_value={"ok": True})
    return api


def make_ctx(raw: dict) -> Context:
    return Context(Update(raw), make_api())


# Update with no chat_id — simulates future non-chat update type.
RAW_NO_CHAT = {"update_id": 99}

# Normal message update — has chat_id and message_id.
RAW_MESSAGE = {
    "update_id": 1,
    "message": {
        "message_id": 10,
        "text": "hello",
        "from": {"id": 99, "username": "ali"},
        "chat": {"id": 200, "type": "private"},
    },
}

# Callback update — has callback_query context.
RAW_CALLBACK = {
    "update_id": 2,
    "callback_query": {
        "id": "cq1",
        "data": "yes",
        "from": {"id": 55},
        "message": {
            "message_id": 30,
            "chat": {"id": 400, "type": "group"},
        },
    },
}


# -------------------------
# Principle 1: Hard Contract never silences
# -------------------------

class TestHardContractNeverSilences:
    """
    Hard Contract methods must raise TitanError when called outside their
    valid context. Returning None silently is a contract violation.
    """

    @pytest.mark.asyncio
    async def test_answer_callback_raises_outside_callback(self):
        """ctx.answer_callback() is callback-only. Outside callback → raise, not None."""
        ctx = make_ctx(RAW_MESSAGE)
        with pytest.raises(TitanError):
            await ctx.answer_callback()

    @pytest.mark.asyncio
    async def test_edit_raises_outside_callback(self):
        """ctx.edit() is callback-only. Outside callback → raise, not None."""
        ctx = make_ctx(RAW_MESSAGE)
        with pytest.raises(TitanError):
            await ctx.edit("text")

    @pytest.mark.asyncio
    async def test_answer_callback_does_not_return_none_silently(self):
        """Hard Contract must not be silent: the method must raise, not disappear."""
        ctx = make_ctx(RAW_MESSAGE)
        raised = False
        try:
            await ctx.answer_callback()
        except TitanError:
            raised = True
        assert raised, (
            "ctx.answer_callback() must raise TitanError outside callback context, "
            "not return None silently."
        )

    @pytest.mark.asyncio
    async def test_edit_does_not_return_none_silently(self):
        """Hard Contract must not be silent: the method must raise, not disappear."""
        ctx = make_ctx(RAW_MESSAGE)
        raised = False
        try:
            await ctx.edit("text")
        except TitanError:
            raised = True
        assert raised, (
            "ctx.edit() must raise TitanError outside callback context, "
            "not return None silently."
        )

    @pytest.mark.asyncio
    async def test_answer_callback_raises_when_callback_id_missing(self):
        """Hard Contract: callback_query present but id missing must raise, not return None."""
        raw_malformed = {
            "update_id": 2,
            "callback_query": {
                # intentionally no 'id' field
                "data": "yes",
                "from": {"id": 55},
                "message": {
                    "message_id": 30,
                    "chat": {"id": 400, "type": "group"},
                },
            },
        }
        ctx = make_ctx(raw_malformed)
        with pytest.raises(TitanError):
            await ctx.answer_callback()


# -------------------------
# Principle 2: Primary actions never fail silently
# -------------------------

class TestPrimaryActionsNeverFailSilently:
    """
    Primary actions must emit a 'titan' logger warning when their precondition
    is absent. They still return None — but the failure is visible.
    """

    @pytest.mark.asyncio
    async def test_reply_warns_when_no_chat_id(self, caplog):
        ctx = make_ctx(RAW_NO_CHAT)
        with caplog.at_level(logging.WARNING, logger="titan"):
            result = await ctx.reply("hello")
        assert result is None
        assert "ctx.reply()" in caplog.text
        assert "chat_id" in caplog.text

    @pytest.mark.asyncio
    async def test_send_warns_when_no_chat_id(self, caplog):
        ctx = make_ctx(RAW_NO_CHAT)
        with caplog.at_level(logging.WARNING, logger="titan"):
            result = await ctx.send("hello")
        assert result is None
        assert "ctx.send()" in caplog.text
        assert "chat_id" in caplog.text

    @pytest.mark.asyncio
    async def test_delete_message_warns_when_no_chat_id(self, caplog):
        ctx = make_ctx(RAW_NO_CHAT)
        with caplog.at_level(logging.WARNING, logger="titan"):
            result = await ctx.delete_message()
        assert result is None
        assert "ctx.delete_message()" in caplog.text

    @pytest.mark.asyncio
    async def test_ban_user_warns_when_no_chat_id(self, caplog):
        ctx = make_ctx(RAW_NO_CHAT)
        with caplog.at_level(logging.WARNING, logger="titan"):
            result = await ctx.ban_user()
        assert result is None
        assert "ctx.ban_user()" in caplog.text

    @pytest.mark.asyncio
    async def test_leave_warns_when_no_chat_id(self, caplog):
        ctx = make_ctx(RAW_NO_CHAT)
        with caplog.at_level(logging.WARNING, logger="titan"):
            result = await ctx.leave()
        assert result is None
        assert "ctx.leave()" in caplog.text
        assert "chat_id" in caplog.text

    @pytest.mark.asyncio
    async def test_reply_warning_names_the_method(self, caplog):
        """The warning must identify the specific method that did not execute."""
        ctx = make_ctx(RAW_NO_CHAT)
        with caplog.at_level(logging.WARNING, logger="titan"):
            await ctx.reply("hello")
        assert "ctx.reply()" in caplog.text, (
            "Warning must name the method so the developer knows which call did not execute."
        )

    @pytest.mark.asyncio
    async def test_primary_actions_still_return_none(self, caplog):
        """Soft Contract: warning is emitted, return value is still None, no crash."""
        ctx = make_ctx(RAW_NO_CHAT)
        with caplog.at_level(logging.WARNING, logger="titan"):
            assert await ctx.reply("x") is None
            assert await ctx.send("x") is None
            assert await ctx.delete_message() is None
            assert await ctx.ban_user() is None
            assert await ctx.leave() is None


# -------------------------
# Principle 3: Best-Effort stays silent
# -------------------------

class TestBestEffortStaysSilent:
    """
    Best-Effort side effects must not raise and must not emit warnings.
    Their absence has no user-facing consequence.
    """

    @pytest.mark.asyncio
    async def test_typing_does_not_raise_without_chat_id(self):
        """ctx.typing() is best-effort: no chat_id → no crash."""
        ctx = make_ctx(RAW_NO_CHAT)
        async with ctx.typing():
            pass  # must not raise

    @pytest.mark.asyncio
    async def test_typing_does_not_warn_without_chat_id(self, caplog):
        """ctx.typing() is best-effort: no chat_id → no warning."""
        ctx = make_ctx(RAW_NO_CHAT)
        with caplog.at_level(logging.WARNING, logger="titan"):
            async with ctx.typing():
                pass
        titan_warnings = [
            r for r in caplog.records
            if r.name == "titan" and r.levelno >= logging.WARNING
        ]
        assert len(titan_warnings) == 0, (
            "ctx.typing() must be completely silent when chat_id is absent. "
            "Best-effort actions do not produce warnings."
        )

    @pytest.mark.asyncio
    async def test_typing_works_normally_with_chat_id(self):
        """ctx.typing() executes normally when chat_id is present."""
        api = make_api()
        ctx = Context(Update(RAW_MESSAGE), api)
        async with ctx.typing():
            pass
        api.send_chat_action.assert_called_once_with(200, "typing")


# -------------------------
# Edge case: Soft Contract warning inside callback context
# -------------------------

class TestEditSoftContractInsideCallback:
    """
    ctx.edit() raises Hard Contract when called outside a callback context.
    Within a callback context, if chat_id or message_id is unexpectedly absent,
    it falls to Soft Contract: warning emitted, None returned, no crash.
    """

    @pytest.mark.asyncio
    async def test_edit_warns_when_chat_id_missing_in_callback(self, caplog):
        """In callback context, missing chat_id triggers Soft Contract warning."""
        raw_callback_no_chat = {
            "update_id": 2,
            "callback_query": {
                "id": "cq1",
                "data": "yes",
                "from": {"id": 55},
                # message present but no chat
                "message": {"message_id": 30},
            },
        }
        ctx = make_ctx(raw_callback_no_chat)
        with caplog.at_level(logging.WARNING, logger="titan"):
            result = await ctx.edit("new text")
        assert result is None
        assert "ctx.edit()" in caplog.text
