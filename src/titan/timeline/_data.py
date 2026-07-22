"""
titan.timeline._data

بيانات titan.timeline — private.

لا تُستورد مباشرةً. تُقرأ فقط من titan.timeline.__init__.

هذا الملف هو مصدر الحقيقة الوحيد. لا يُقرأ Markdown في وقت التشغيل —
نفس فلسفة titan.migration و titan.health: بيانات ثابتة، صريحة، غير متغيّرة.

عند إضافة قرار جديد لـ docs/decisions/: يُضاف إدخال هنا يدوياً، ثم يُشغَّل
scripts/generate_decisions_readme.py لتحديث docs/decisions/README.md.

حقل rule: dict ثنائي اللغة {"en": "...", "ar": "..."}.
الإنجليزية هي fallback الأساسية. استهلاك مُوجَّه عبر titan.light.rules(locale=).
"""

from __future__ import annotations

from titan.timeline.models import ArchiveEntry


ENTRIES: tuple[ArchiveEntry, ...] = (
    ArchiveEntry(
        number="001",
        title="Keyboard Builder",
        status="Rejected",
        rule={
            "en": (
                "Fix documentation before adding API. An API added to compensate "
                "for a poorly documented existing API is not justified — a new "
                "API is justified only when the limitation is in the "
                "implementation itself, not in its explanation."
            ),
            "ar": (
                "أصلح التوثيق قبل إضافة API. أي API يُضاف تعويضاً عن API موجود "
                "موثَّق توثيقاً رديئاً غير مبرَّر — الـ API الجديد مبرَّر فقط "
                "عندما يكون القيد في التنفيذ نفسه، لا في شرحه."
            ),
        },
        summary=(
            "A dedicated Keyboard builder class was proposed to make row-based "
            "layout more readable. Investigation found the real problem was a "
            "misleading documented convention around InlineKeyboard.row(), not "
            "a gap in the implementation. The docs were fixed; no new API was added."
        ),
        tags=("api-design", "documentation", "keyboard"),
        date=None,
        path="docs/decisions/001-keyboard-builder.md",
    ),
    ArchiveEntry(
        number="002",
        title="Actions",
        status="Accepted",
        rule={
            "en": (
                "An Action is a ctx-bound signal that affects how the bot is "
                "perceived or what it communicates — not a message, not a "
                "result, and not a standalone utility. Its implementation shape "
                "follows from its own behavior, not from precedent."
            ),
            "ar": (
                "الـ Action إشارة مرتبطة بـ ctx تؤثر على طريقة إدراك البوت أو "
                "ما يوصله — ليست رسالة، ولا نتيجة، ولا utility مستقلة. شكل "
                "تنفيذها يتبع سلوكها الخاص لا السابقة."
            ),
        },
        summary=(
            "Defined the Action concept: a ctx-bound operation that signals "
            "something on behalf of the bot without returning data the "
            "developer uses. ctx.typing() was implemented as the first Action, "
            "using an async context manager because typing is a temporary state."
        ),
        tags=("ctx", "actions", "api-design"),
        date=None,
        path="docs/decisions/002-actions.md",
    ),
    ArchiveEntry(
        number="003",
        title="Capabilities",
        status="Accepted",
        rule={
            "en": (
                "Ownership follows scope. If a capability is global (independent "
                "of the current update or chat), it belongs on bot. If it is "
                "contextual (depends on the current chat or update), it belongs "
                "on ctx. Different concepts are allowed to have different APIs."
            ),
            "ar": (
                "الملكية تتبع النطاق. إذا كانت القدرة عامة (مستقلة عن التحديث "
                "أو المحادثة الحالية) فتنتمي إلى bot. إذا كانت سياقية (تعتمد "
                "على المحادثة أو التحديث الحالي) فتنتمي إلى ctx. يُسمح لمفاهيم "
                "مختلفة بأن يكون لها APIs مختلفة."
            ),
        },
        summary=(
            "Replaced the ambiguous ctx.can_delete with two explicit surfaces: "
            "bot.capabilities for global, stable account-level abilities from "
            "getMe, and ctx.permissions for per-chat permissions discovered "
            "explicitly via getChatMember. Failures propagate instead of "
            "collapsing into an ambiguous False."
        ),
        tags=("capabilities", "ctx", "bot", "models"),
        date=None,
        path="docs/decisions/003-capabilities.md",
    ),
    ArchiveEntry(
        number="004",
        title="Error Contracts",
        status="Accepted",
        rule={
            "en": (
                "Titan declares contract violations at a level proportional to "
                "how impossible the violation is: always wrong -> exception; "
                "currently impossible but may become valid -> warning; expected "
                "and inconsequential -> silent."
            ),
            "ar": (
                "Titan يُعلن عن انتهاكات العقد بمستوى متناسب مع درجة استحالة "
                "الانتهاك: خاطئ دائماً → استثناء؛ مستحيل حالياً لكن قد يصبح "
                "صحيحاً → تحذير؛ متوقع وغير ذي عواقب → صامت."
            ),
        },
        summary=(
            "Classified every silently-failing ctx method into three tiers — "
            "Hard Contract (raise TitanError), Soft Contract (log warning), "
            "and Best-Effort (silent no-op) — and applied the classification "
            "consistently across ctx.reply(), ctx.send(), ctx.answer_callback() "
            "and others."
        ),
        tags=("errors", "contracts", "ctx", "philosophy"),
        date=None,
        path="docs/decisions/004-error-contracts.md",
    ),
    ArchiveEntry(
        number="005",
        title="Project Health",
        status="Accepted",
        rule={
            "en": (
                "Project Health evaluates the project's state — it does not fix it. "
                "Any new check must be verifiable from internal state only "
                "(no file scanning, no AST), must represent a real common problem "
                "rather than a default assumption, and must be testable without "
                "a real Telegram session."
            ),
            "ar": (
                "Project Health يُقيّم حالة المشروع. لا تُصلحها. أي فحص جديد يجب "
                "أن يكون قابلاً للتحقق من الـ state الداخلي فقط (لا file "
                "scanning، لا AST)، يمثّل مشكلة شائعة لا حالة افتراضية، وقابلاً "
                "للاختبار بدون Telegram session حقيقية."
            ),
        },
        summary=(
            "Added bot.health() — a structural and operational audit that "
            "returns a list of HealthFinding objects (ERROR / WARNING / INFO) "
            "describing likely gaps such as missing handlers or an unused "
            "capability, without ever modifying the project itself."
        ),
        tags=("health", "diagnostics", "bot"),
        date=None,
        path="docs/decisions/005-project-health.md",
    ),
    ArchiveEntry(
        number="006",
        title="Interactive Inspector",
        status="Accepted",
        rule={
            "en": (
                'Inspector describes, it does not judge. Any logic that renders '
                'a verdict ("problem", "unused", "missing") does not belong in '
                "Inspector — it belongs in Health."
            ),
            "ar": (
                "Inspector يصف، ولا يُقيّم. أي منطق يُصدر حكماً (\"مشكلة\"، "
                "\"غير مستخدم\"، \"مفقود\") لا يدخل Inspector — يذهب إلى Health."
            ),
        },
        summary=(
            "Added bot.inspect(), returning a frozen BotSnapshot describing "
            "the bot's current registration state — commands, callbacks, "
            "events, middleware count, error handler presence — as pure "
            "description, never judgment."
        ),
        tags=("inspector", "bot", "models"),
        date=None,
        path="docs/decisions/006-interactive-inspector.md",
    ),
    ArchiveEntry(
        number="007",
        title="Migration Assistant",
        status="Accepted",
        rule={
            "en": (
                "Migration Assistant explains the philosophy, it does not translate "
                "code. The goal: the developer understands why Titan works this way, "
                "not just what to write."
            ),
            "ar": (
                "Migration Assistant يشرح الفلسفة، لا يُترجم الكود. الهدف: "
                "المطور يفهم لماذا Titan يعمل بهذه الطريقة، لا فقط ماذا يكتب."
            ),
        },
        summary=(
            "Built two complementary layers for developers coming from other "
            "frameworks: philosophical migration guides in docs/migration/, "
            "and a queryable titan.migration Knowledge API (frameworks(), "
            "concepts(), compare()) covering PTB, aiogram, and telebot."
        ),
        tags=("migration", "knowledge-base", "api-design"),
        date=None,
        path="docs/decisions/007-migration-assistant.md",
    ),
    ArchiveEntry(
        number="008",
        title="Message Links Protocol",
        status="Accepted",
        rule={
            "en": (
                "The identity protocol is not a utility — it deserves its own domain. "
                "Operational storage is not Titan code: the separation between "
                "titan/links/ (code) and .titan/links.db (data) is a principle, "
                "not an organizational choice."
            ),
            "ar": (
                "بروتوكول الهوية ليس utility — يستحق domain مستقلاً. التخزين "
                "التشغيلي ليس كود Titan: الفصل بين titan/links/ (كود) و "
                ".titan/links.db (بيانات) مبدأ، لا تنظيم."
            ),
        },
        summary=(
            "Introduced titan.links: every message a bot sends automatically "
            "receives a stable identity (TitanMessageAddress) built on a "
            "sequential per-bot TitanMessageId, with an optional Archive "
            "Layer and a /link command that discovers — never creates — identity."
        ),
        tags=("links", "identity", "protocol"),
        date=None,
        path="docs/decisions/008-message-links-protocol.md",
    ),
    ArchiveEntry(
        number="009",
        title="Runtime Contract Validator",
        status="Accepted",
        rule={
            "en": (
                "Fail as Early as Possible: validation happens at the nearest "
                "registration point. Any violation of a handler/middleware/"
                "error-handler contract raises TitanError immediately at "
                "registration (import time), not at bot.run() or when an "
                "update arrives."
            ),
            "ar": (
                "Fail as Early as Possible: التحقق يحدث في أقرب نقطة تسجيل. أي "
                "انتهاك لعقد handler/middleware/error-handler يرفع TitanError "
                "فوراً عند التسجيل (import time)، وليس عند bot.run() أو وصول update."
            ),
        },
        summary=(
            "Added validate_handler / validate_middleware / "
            "validate_error_handler in titan.validation, checked at every "
            "registration point (@bot.command, @router.command, ...), "
            "verifying asyncness and parameter count so a broken callable is "
            "rejected the moment it is registered — including async callable objects."
        ),
        tags=("validation", "contracts", "fail-fast"),
        date="2026-07-10",
        path="docs/decisions/009-runtime-contract-validator.md",
    ),
    ArchiveEntry(
        number="010",
        title="Timeline",
        status="Accepted",
        rule={
            "en": (
                "titan.timeline is architectural memory, not a Markdown index — "
                "no runtime parsing of any document, ever. Direction always flows "
                "from code to derived documentation, never the reverse. "
                "ArchiveEntry describes the architectural event, not just its "
                "current type. No API without a real consumer."
            ),
            "ar": (
                "titan.timeline ذاكرة معمارية، لا فهرس Markdown — لا runtime "
                "parsing لأي مستند أبداً. الاتجاه دائماً من الكود إلى التوثيق "
                "المُشتق، لا العكس. ArchiveEntry تصف الحدث المعماري لا نوعه "
                "الحالي فقط. لا API بدون مستهلك فعلي."
            ),
        },
        summary=(
            "Established titan.timeline as an independent architectural-"
            "memory domain (not a utility, not folded into migration or "
            "health): ArchiveEntry is deliberately generic so future entry "
            "kinds beyond ADR can be added without a model change, _data.py "
            "remains the sole source of truth, docs/decisions/README.md is "
            "generated from it (never the reverse), and by_tag() was "
            "deliberately deferred in v1 — tags already support manual "
            "filtering and no real consumer needs a dedicated function yet."
        ),
        tags=("timeline", "architecture", "api-design", "philosophy"),
        date="2026-07-10",
        path="docs/decisions/010-timeline.md",
    ),
    ArchiveEntry(
        number="011",
        title="Playground",
        status="Accepted",
        rule={
            "en": (
                "Playground does not add capabilities to Titan — it exposes "
                "existing Titan capabilities in an explorable way. The event feed "
                "point lives in Core, not in the tool consuming it. No Core "
                "abstraction for a single consumer. Every simulation alternative "
                "fails explicitly outside its declared scope."
            ),
            "ar": (
                "Playground لا يضيف قدرات إلى Titan، بل يكشف قدرات Titan "
                "الموجودة بطريقة قابلة للاستكشاف. نقطة تغذية الأحداث تعيش في "
                "Core لا في الأداة التي تستهلكها. لا تجريد في Core لمستهلك "
                "واحد. كل بديل محاكاة يفشل بوضوح خارج نطاقه المُعلن."
            ),
        },
        summary=(
            "Established titan.playground as an architectural lab, not a "
            "code sandbox: added Titan.feed_update() as a genuine Core "
            "capability (an official non-polling event entry point serving "
            "Playground, advanced tests, and future Userbot Support), "
            "RecordingTelegram as a duck-typed in-memory Telegram double "
            "scoped strictly to what Context/TelegramAdapter actually call, "
            "and factory.py for building fake Telegram-shaped updates — all "
            "confined to the playground package, not exported from root, "
            "and without touching telegram.py."
        ),
        tags=("playground", "architecture", "api-design", "philosophy"),
        date="2026-07-10",
        path="docs/decisions/011-playground.md",
    ),
    ArchiveEntry(
        number="012",
        title="Design Linter",
        status="Accepted",
        rule={
            "en": (
                "bot.lint() inspects conventions, not structure or signatures. "
                "No AST inside src/titan/ — static analysis belongs to a future "
                "external tool. hint is mandatory in every LintFinding — Linter "
                "teaches, it does not punish. v1 = 3A (registration-time) + "
                "3B (aggregated state), no expansion before a real consumer."
            ),
            "ar": (
                "bot.lint() تفحص الاتفاقيات لا البنية ولا التوقيع. لا AST داخل "
                "src/titan/ — الفحص الثابت ينتمي لأداة خارجية مستقبلية. "
                "hint إلزامي في كل LintFinding — Linter يُعلّم لا يُعاقب. "
                "v1 = 3أ (وقت التسجيل) + 3ب (حالة مجمّعة)، لا توسع قبل مستهلك حقيقي."
            ),
        },
        summary=(
            "Added bot.lint() as a Core capability completing the self-awareness "
            "triad: inspect (what exists) + health (is it complete) + lint "
            "(are conventions respected). Introduced LintFinding as an "
            "independent datatype with a mandatory hint field. v1 ships five "
            "rules across two tiers: 3A registration-time rules — command names "
            "must be lowercase (TITAN_LINT_001), callback_data must not be empty "
            "or whitespace-only (TITAN_LINT_002), on_offset must not be an async "
            "callable silently ignored (TITAN_LINT_003) — and 3B aggregated "
            "rules — empty routers (TITAN_LINT_010), excessive fan-out on a "
            "single event type beyond threshold 10 (TITAN_LINT_011). Internal "
            "structure lives in src/titan/lint/ with engine + rules subpackage. "
            "Added _included_router_objects and _on_offset to bot internals for "
            "lint introspection without touching the public API. Static analysis "
            "(AST-based rules for anti-patterns in developer code) is explicitly "
            "deferred to a future titan-lint CLI/ruff plugin outside this repo."
        ),
        tags=("lint", "architecture", "api-design", "philosophy", "conventions"),
        date="2026-07-11",
        path="docs/decisions/012-design-linter.md",
    ),
    ArchiveEntry(
        number="013",
        title="Performance Profiler",
        status="Accepted",
        rule={
            "en": (
                "Build on what exists before adding what is new. If a tool serves "
                "development only, its scope is the development environment — no "
                "production overhead justifies Core complexity. feed_update() "
                "exists for sound architectural reasons; Profiler benefits from "
                "it without asking Core for anything new."
            ),
            "ar": (
                "يبني على ما هو موجود قبل إضافة ما هو جديد. إذا كانت الأداة "
                "تخدم التطوير فقط، فحدودها هي حدود بيئة التطوير — لا overhead "
                "في production يُبرر complexity في Core. feed_update() وُجد "
                "لأسباب معمارية سليمة؛ الـ Profiler يستفيد منه دون أن يطلب "
                "من Core شيئاً جديداً."
            ),
        },
        summary=(
            "Established titan.profiler as a development-only domain built "
            "entirely on top of feed_update() and titan.playground — no Core "
            "changes, no bot state, zero production overhead. Profiling is "
            "Playground-based: profile_update(bot, fake_command('start'), n=100) "
            "wraps feed_update() with time.perf_counter() and accumulates "
            "ProfileEntry(event_type, duration_ms, metadata) objects into a "
            "ProfilingSession with a summary() method. ProfileEntry carries "
            "metadata: dict (empty in v1) instead of specialized breakdown "
            "fields — keeping the model open for a future ProfileTrace without "
            "a breaking change. event_type is inferred from update structure. "
            "Production monitoring deferred as an independent decision."
        ),
        tags=("profiler", "performance", "playground", "api-design"),
        date="2026-07-11",
        path="docs/decisions/013-performance-profiler.md",
    ),
    ArchiveEntry(
        number="014",
        title="Titan Light",
        status="Accepted",
        rule={
            "en": (
                "Titan Light summarises what Titan already knows — deterministic "
                "results in v1, LLM optional later. Output is always structured "
                "so external tools and AI systems can consume it — "
                "human developer first."
            ),
            "ar": (
                "Titan Light تُلخّص ما يعرفه Titan بالفعل — محددة النتائج في v1، "
                "LLM اختياري لاحقاً. الـ output مُهيكل دائماً حتى تستطيع الأدوات "
                "وأنظمة AI الخارجية استهلاكه — human developer first."
            ),
        },
        summary=(
            "Established titan.light (Titan Light) as a separate domain "
            "providing a deterministic architectural knowledge layer over "
            "titan.timeline. v1 is purely rule-based — no LLM, no external "
            "dependencies. Four functions: search() (deterministic keyword "
            "matching across title/tags/rule/summary with weighted relevance — "
            "not AI), explain() (interpretation of one decision: rule + summary "
            "+ path to full ADR — more than retrieval), rules() (architectural "
            "principles extracted from ADR decisions — not lint or Python rules), "
            "decisions() (structured summaries with status/tag filtering). "
            "All return frozen dataclasses — human-readable and machine-consumable. "
            "Not attached to bot; bot is the execution engine, Titan Light is a "
            "consumer of knowledge domains. check_against_rules() deferred — "
            "overlaps with Design Linter. LLM backend left as future pluggable option. "
            "rule field in ArchiveEntry is a bilingual dict {\"en\": ..., \"ar\": ...}; "
            "rules(locale=\"en\") and rules(locale=\"ar\") resolve it with English fallback."
        ),
        tags=("light", "timeline", "api-design", "philosophy", "knowledge"),
        date="2026-07-11",
        path="docs/decisions/014-architect-ai.md",
    ),
)
