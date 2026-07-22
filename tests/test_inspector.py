# ﷽
"""
اختبارات Interactive Inspector — bot.inspect() و BotSnapshot

تغطي:
- BotSnapshot: النموذج، الخصائص، الثبات
- build_snapshot: منطق البناء
- bot.inspect(): التكامل مع Titan
- MiddlewareChain.count: التحسين الصغير المرافق
- Public API contract: BotSnapshot مُصدَّرة من الجذر
"""

import pytest
from dataclasses import dataclass, fields, FrozenInstanceError

from titan import Titan, BotSnapshot
from titan.inspector import BotSnapshot as BotSnapshotDirect, build_snapshot
from titan.middleware import MiddlewareChain
from titan.router import Router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_bot() -> Titan:
    return Titan("0:test")


async def noop(ctx):
    pass


async def noop2(ctx):
    pass


async def middleware_fn(ctx, next):
    await next()


async def error_handler(ctx, exc):
    pass


# ===========================================================================
# BotSnapshot — النموذج
# ===========================================================================

class TestBotSnapshotModel:
    def test_is_dataclass(self):
        assert hasattr(BotSnapshot, "__dataclass_fields__")

    def test_is_frozen(self):
        snapshot = BotSnapshot(
            commands=("start",),
            callbacks=("yes",),
            events={"message": 1},
            middleware_count=0,
            has_error_handler=False,
            included_router_count=0,
            capabilities_available=False,
        )
        with pytest.raises(FrozenInstanceError):
            snapshot.commands = ("other",)  # type: ignore[misc]

    def test_all_fields_present(self):
        field_names = {f.name for f in fields(BotSnapshot)}
        expected = {
            "commands",
            "callbacks",
            "events",
            "middleware_count",
            "has_error_handler",
            "included_router_count",
            "capabilities_available",
        }
        assert field_names == expected

    def test_commands_is_tuple(self):
        snapshot = BotSnapshot(
            commands=("start", "help"),
            callbacks=(),
            events={},
            middleware_count=0,
            has_error_handler=False,
            included_router_count=0,
            capabilities_available=False,
        )
        assert isinstance(snapshot.commands, tuple)

    def test_callbacks_is_tuple(self):
        snapshot = BotSnapshot(
            commands=(),
            callbacks=("yes", "no"),
            events={},
            middleware_count=0,
            has_error_handler=False,
            included_router_count=0,
            capabilities_available=False,
        )
        assert isinstance(snapshot.callbacks, tuple)

    def test_events_is_mapping(self):
        from types import MappingProxyType
        snapshot = BotSnapshot(
            commands=(),
            callbacks=(),
            events=MappingProxyType({"message": 2}),
            middleware_count=0,
            has_error_handler=False,
            included_router_count=0,
            capabilities_available=False,
        )
        assert snapshot.events["message"] == 2

    def test_events_is_immutable(self):
        """events لا تقبل الكتابة رغم أن الـ dataclass frozen لا يحمي nested objects."""
        from types import MappingProxyType
        import pytest
        snapshot = BotSnapshot(
            commands=(),
            callbacks=(),
            events=MappingProxyType({"message": 1}),
            middleware_count=0,
            has_error_handler=False,
            included_router_count=0,
            capabilities_available=False,
        )
        with pytest.raises(TypeError):
            snapshot.events["new_event"] = 1  # type: ignore[index]

    def test_empty_snapshot_is_valid(self):
        snapshot = BotSnapshot(
            commands=(),
            callbacks=(),
            events={},
            middleware_count=0,
            has_error_handler=False,
            included_router_count=0,
            capabilities_available=False,
        )
        assert snapshot.commands == ()
        assert snapshot.callbacks == ()
        assert snapshot.events == {}
        assert snapshot.middleware_count == 0
        assert snapshot.has_error_handler is False
        assert snapshot.included_router_count == 0
        assert snapshot.capabilities_available is False


# ===========================================================================
# MiddlewareChain.count — التحسين المرافق
# ===========================================================================

class TestMiddlewareChainCount:
    def test_count_zero_on_empty(self):
        chain = MiddlewareChain()
        assert chain.count == 0

    def test_count_increments_on_add(self):
        chain = MiddlewareChain()
        chain.add(middleware_fn)
        assert chain.count == 1
        chain.add(middleware_fn)
        assert chain.count == 2

    def test_count_multiple(self):
        chain = MiddlewareChain()
        for _ in range(5):
            chain.add(middleware_fn)
        assert chain.count == 5

    def test_count_is_property_not_method(self):
        chain = MiddlewareChain()
        # يجب أن يكون property لا callable
        assert not callable(chain.count)

    def test_run_still_works_after_count(self):
        """إضافة count لا تكسر الـ run()."""
        import asyncio

        chain = MiddlewareChain()
        called = []

        async def mw(ctx, next):
            called.append("mw")
            await next()

        async def handler():
            called.append("handler")

        chain.add(mw)

        async def run():
            await chain.run(None, handler)  # type: ignore[arg-type]

        asyncio.run(run())
        assert called == ["mw", "handler"]


# ===========================================================================
# build_snapshot — منطق البناء
# ===========================================================================

class TestBuildSnapshot:
    def test_empty_bot(self):
        bot = make_bot()
        snap = build_snapshot(bot)
        assert snap.commands == ()
        assert snap.callbacks == ()
        assert snap.events == {}
        assert snap.middleware_count == 0
        assert snap.has_error_handler is False
        assert snap.included_router_count == 0
        assert snap.capabilities_available is False

    def test_commands_sorted(self):
        bot = make_bot()
        bot.command("start")(noop)
        bot.command("help")(noop)
        bot.command("admin")(noop)
        snap = build_snapshot(bot)
        assert snap.commands == ("admin", "help", "start")

    def test_callbacks_sorted(self):
        bot = make_bot()
        bot.callback("yes")(noop)
        bot.callback("no")(noop)
        bot.callback("cancel")(noop)
        snap = build_snapshot(bot)
        assert snap.callbacks == ("cancel", "no", "yes")

    def test_events_counts_handlers(self):
        bot = make_bot()
        bot.on("message")(noop)
        bot.on("message")(noop2)
        bot.on("new_member")(noop)
        snap = build_snapshot(bot)
        assert snap.events == {"message": 2, "new_member": 1}

    def test_events_excludes_empty_lists(self):
        """حدث مسجل ثم فارغ لا يظهر في events."""
        bot = make_bot()
        bot.handlers["phantom"] = []  # يُضاف مباشرة لكنه فارغ
        snap = build_snapshot(bot)
        assert "phantom" not in snap.events

    def test_middleware_count_reflects_chain(self):
        bot = make_bot()
        bot.middleware(middleware_fn)
        bot.middleware(middleware_fn)
        snap = build_snapshot(bot)
        assert snap.middleware_count == 2

    def test_has_error_handler_false_by_default(self):
        bot = make_bot()
        snap = build_snapshot(bot)
        assert snap.has_error_handler is False

    def test_has_error_handler_true_when_registered(self):
        bot = make_bot()
        bot.error_handler(error_handler)
        snap = build_snapshot(bot)
        assert snap.has_error_handler is True

    def test_included_router_count_zero_by_default(self):
        bot = make_bot()
        snap = build_snapshot(bot)
        assert snap.included_router_count == 0

    def test_included_router_count_increments(self):
        bot = make_bot()
        r1 = Router()
        r2 = Router()
        bot.include(r1)
        bot.include(r2)
        snap = build_snapshot(bot)
        assert snap.included_router_count == 2

    def test_capabilities_available_false_before_run(self):
        """قبل bot.run() لا توجد capabilities — capabilities_available = False."""
        bot = make_bot()
        snap = build_snapshot(bot)
        assert snap.capabilities_available is False

    def test_capabilities_available_true_when_me_present(self):
        """بعد getMe — capabilities_available = True."""
        bot = make_bot()
        # نُحاكي وجود _me (كما يحدث بعد bot.run_async)
        bot._api._me = {"id": 123, "is_bot": True, "first_name": "TestBot"}
        snap = build_snapshot(bot)
        assert snap.capabilities_available is True

    def test_returns_botsnapshot(self):
        bot = make_bot()
        snap = build_snapshot(bot)
        assert isinstance(snap, BotSnapshot)

    def test_snapshot_is_frozen(self):
        bot = make_bot()
        snap = build_snapshot(bot)
        with pytest.raises(FrozenInstanceError):
            snap.commands = ("other",)  # type: ignore[misc]


# ===========================================================================
# bot.inspect() — التكامل مع Titan
# ===========================================================================

class TestBotInspect:
    def test_inspect_returns_botsnapshot(self):
        bot = make_bot()
        assert isinstance(bot.inspect(), BotSnapshot)

    def test_inspect_reflects_commands(self):
        bot = make_bot()
        bot.command("start")(noop)
        snap = bot.inspect()
        assert "start" in snap.commands

    def test_inspect_reflects_callbacks(self):
        bot = make_bot()
        bot.callback("confirm")(noop)
        snap = bot.inspect()
        assert "confirm" in snap.callbacks

    def test_inspect_reflects_events(self):
        bot = make_bot()
        bot.on("message")(noop)
        snap = bot.inspect()
        assert "message" in snap.events
        assert snap.events["message"] == 1

    def test_inspect_reflects_middleware(self):
        bot = make_bot()
        bot.middleware(middleware_fn)
        snap = bot.inspect()
        assert snap.middleware_count == 1

    def test_inspect_reflects_error_handler(self):
        bot = make_bot()
        assert bot.inspect().has_error_handler is False
        bot.error_handler(error_handler)
        assert bot.inspect().has_error_handler is True

    def test_inspect_reflects_routers(self):
        bot = make_bot()
        router = Router()
        bot.include(router)
        snap = bot.inspect()
        assert snap.included_router_count == 1

    def test_inspect_merges_router_registrations(self):
        """registrations الـ router تظهر في snapshot بعد include()."""
        bot = make_bot()
        router = Router()
        router.command("admin")(noop)
        router.callback("delete")(noop)
        bot.include(router)
        snap = bot.inspect()
        assert "admin" in snap.commands
        assert "delete" in snap.callbacks

    def test_inspect_snapshot_does_not_mutate_on_later_changes(self):
        """الـ snapshot مجمّدة — التغييرات اللاحقة لا تؤثر عليها."""
        bot = make_bot()
        bot.command("start")(noop)
        snap1 = bot.inspect()
        bot.command("help")(noop)
        snap2 = bot.inspect()
        # snap1 لا تتغير
        assert "help" not in snap1.commands
        assert "help" in snap2.commands

    def test_inspect_usable_before_run(self):
        """bot.inspect() لا تحتاج bot.run() — تعمل في أي وقت."""
        bot = make_bot()
        bot.command("start")(noop)
        snap = bot.inspect()
        assert "start" in snap.commands

    def test_inspect_full_bot(self):
        """تكامل: bot به كل أنواع الـ registrations."""
        bot = make_bot()
        bot.command("start")(noop)
        bot.command("help")(noop)
        bot.on("message")(noop)
        bot.on("message")(noop2)
        bot.on("new_member")(noop)
        bot.callback("yes")(noop)
        bot.callback("no")(noop)
        bot.middleware(middleware_fn)
        bot.error_handler(error_handler)
        router = Router()
        bot.include(router)

        snap = bot.inspect()
        assert set(snap.commands) == {"start", "help"}
        assert set(snap.callbacks) == {"yes", "no"}
        assert snap.events == {"message": 2, "new_member": 1}
        assert snap.middleware_count == 1
        assert snap.has_error_handler is True
        assert snap.included_router_count == 1
        assert snap.capabilities_available is False


# ===========================================================================
# Public API Contract
# ===========================================================================

class TestPublicAPIContract:
    def test_botsnapshot_importable_from_root(self):
        from titan import BotSnapshot as BS
        assert BS is BotSnapshot

    def test_botsnapshot_in_all(self):
        import titan
        assert "BotSnapshot" in titan.__all__

    def test_botsnapshot_is_same_object_as_direct_import(self):
        assert BotSnapshot is BotSnapshotDirect

    def test_bot_has_inspect_method(self):
        bot = make_bot()
        assert callable(bot.inspect)

    def test_no_circular_import(self):
        """استيراد titan.inspector لا يسبب circular import."""
        import importlib
        import sys
        # نُزيل المودول من الـ cache ثم نعيد استيراده
        for key in list(sys.modules.keys()):
            if "titan" in key:
                del sys.modules[key]
        import titan.inspector  # noqa: F401
