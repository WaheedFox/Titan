# design_notes.md

Internal design notebook.
Not documentation. Not marketing. Not a justification of existing code.
This is the workshop from which `PHILOSOPHY.md` will eventually be written.

---

## Status Key

- `[confirmed]` — survived critical review; believed to hold under significant growth
- `[implementation]` — true of the current code but not a timeless principle; already documented in CONTRACT.md or ROADMAP.md
- `[open]` — unresolved tension or question; no position taken yet
- `[tension]` — two confirmed principles that pull against each other

---

## Part I — Confirmed Principles

Five principles survived the critical review. Five did not. See Part II for what was moved and why.

---

### 1. ctx is the primary surface within the update-response cycle `[confirmed]`

Every operation a developer needs during handler execution — replying, editing, banning, answering callbacks — lives on `ctx`.

The original wording was "ctx is the developer's primary world." That was too broad. If Titan grows to include proactive messaging, scheduled tasks, or Userbot-style operations, the developer will spend significant time outside handlers entirely. ctx would remain central within a handler, but not across all of Titan.

The narrowed claim holds under growth: within a handler, ctx is and should remain the complete interface. Reaching for `bot.telegram` inside a handler is a signal — either something is missing from ctx, or the use case intentionally exceeds the update-response cycle.

---

### 2. Depth is expressed through object hierarchy, not package splits `[confirmed]`

Titan does not separate beginner from advanced usage via distinct packages (unlike PTB's `telegram` vs `telegram.ext`). Instead, depth increases through the object structure within a single namespace:

```
ctx.reply()          ← immediate surface
ctx.sender.username  ← structured data model
ctx.raw              ← raw escape, non-frozen
bot.telegram.*       ← full API, no middleware, no ctx
```

This is a real design choice with a real cost: the gradient is enforced by convention only. Nothing in Python's import system prevents a beginner from landing directly on `bot.telegram`.

This principle holds if Titan adds new adapters or capabilities — as long as Titan remains a single-namespace library. If Titan ever splits into subpackages for distinct platforms or concerns, this principle would need to be revisited.

---

### 3. Explicit over implicit `[confirmed]`

Titan does not act unless asked.

- `bot.banned_users` is a plain `set`. Titan does not enforce it automatically — middleware decides.
- `ctx.refresh_permissions()` requires an explicit call. No API request happens on construction.
- Offset persistence is the developer's responsibility. Titan exposes the hook; it does not manage the store.

The pattern: Titan signals state, the developer decides behavior.

This principle is implementation-independent. It would apply equally under webhook support, Userbot mode, or a larger ecosystem. It describes a stance, not a feature.

---

### 4. Models represent known facts, not the absence of facts `[confirmed]`

A model in Titan wraps information that has already been retrieved. When a model
exists, its properties are unconditionally true — not "possibly true," not "true
if loaded." True.

The absence of a fact is represented by the absence of the model (`None` at the
boundary), not by an object that carries discovery state internally. An object
with a `loaded: bool` or `None`-returning properties is not a model; it is a
placeholder that borrowed a model's shape.

Discovery belongs outside the model. The surface that owns the context for
discovery (`ctx`, `bot`) performs it. The model receives already-discovered data.

This rule was formalized through the Capabilities feature and applies to all
present and future models: `Sender`, `Chat`, `Message`, `BotCapabilities`,
`ChatPermissions`, and any model added later.

→ Full treatment: [concepts/models.md](../concepts/models.md)

---

### 5. Each component has a single, bounded responsibility `[confirmed]`

This is the principle that explains several specific design decisions:

- Middleware handles flow control only. It cannot inject behavior into ctx or contain business logic.
- Router collects handler registrations. It has no runtime execution of its own.
- `bot.telegram` sends API calls. It does not interact with middleware, routing, or ctx.

The specific decisions (no Router middleware, no plugin-based middleware) are consequences of this principle, not the principle itself. Documenting the specific decisions in CONTRACT.md is correct. Documenting the principle here allows future decisions to be evaluated against it directly.

This holds under growth. A new component added to Titan should have one stated purpose. Scope creep in any component is a violation of this principle, not a tradeoff to be negotiated.

---

### 5. Stability is a hard constraint, not a goal `[confirmed]`

The distinction is meaningful and consequential.

A goal can be traded off against other goals. A constraint cannot.

Treating stability as a constraint means: a feature that is useful but expands the frozen API surface is not deferred reluctantly — it is deferred by default, and added only when the case for it is unambiguous. "Other frameworks support this" is not an argument. "Developers cannot accomplish X without it" might be.

This principle would become more important as Titan grows, not less. A larger ecosystem creates more pressure to expand the surface. The constraint is the defense against that pressure.

This is a project philosophy principle, not an architectural one. It belongs in PHILOSOPHY.md. It is confirmed here.

---

### 6. Escape hatches exist, but outside the stability boundary `[confirmed]`

Titan acknowledges that its abstraction is incomplete. There are things `ctx` does not expose. There are things `bot.telegram` does not wrap conveniently. There are fields in Telegram's raw JSON that Titan never surfaces.

Rather than pretending the abstraction is complete, Titan provides explicit escape hatches (`ctx.raw`, `bot.telegram`) and documents them as outside the frozen contract.

This is a principle about how Titan handles its own limits: honestly, explicitly, without forcing developers to subclass or monkey-patch their way out.

The original wording (P10) described a specific attribute, `ctx.raw`. That belongs in CONTRACT.md. The principle is broader: wherever the abstraction ends, there should be a documented, stable way out — and that way out should not carry the same stability promises as the core API.

---

### 7. Recipes reveal Core inconsistencies; they do not define Core structure `[confirmed]`

Recipes are read-only consumers of the Core. The direction of influence is strictly one-way:

```
Core defines what is available → Recipes use what is available
```

The reverse is forbidden:

```
Recipe needs something → Core is changed to match what Recipe needs  ← violation
```

**The test before any Core change made during Recipe work:**

Ask: *Is this a genuine Core design flaw that would matter even if Recipes did not exist?*

- If yes → the change belongs in Core. The Recipe happened to surface it.
- If no → the change does not belong in Core. The Recipe is asking for too much.

**What happened with `ctx.new_members`:**

`ctx.new_members` returned `list[dict] | None` while `Sender` — a typed model that wraps those same dicts — already existed in Core and was used consistently everywhere else (e.g., `ctx.sender`). The inconsistency was real: Core had two different conventions for representing the same Telegram concept (a user) depending on which `ctx` property you accessed.

The fix (returning `list[Sender] | None`) answered yes to the test above. A developer using `ctx.new_members` without any Recipe would have encountered the same raw dict leakage. The Recipe surfaced the inconsistency; the inconsistency was not created by the Recipe's requirements.

**What a violation would look like:**

If `ctx.new_members` had been consistent with the rest of Core — returning Sender objects — but the Recipe still needed something the Core did not offer, and we added a method to Core to satisfy it, that would be a violation. The Core change would exist to serve the Recipe's implementation style, not to correct a genuine design flaw.

This principle is the structural guard against Core gradually becoming a support layer for Recipe authoring preferences.

---

## Part II — Moved Out of Confirmed

These were listed as confirmed principles in the previous version. They did not survive the critical review. Each entry explains why it was moved.

---

### "The underscore is the only structural signal" → Observation, not principle

This is Python convention, not a Titan design decision. Every Python library uses `_` for internals. Restating this as a Titan principle adds no information.

What was actually worth capturing: Titan has no structural enforcement mechanism for its layer model beyond Python conventions. No type system, no separate packages, no ABCs, no runtime checks. The layering is real but enforced only by documentation and naming. That observation belongs in Q1 (open questions) — it is a known gap, not a confirmed principle.

---

### "Router is an organizer, not a routing tree" → Implementation decision

This describes the current Router. It is already documented in CONTRACT.md §14 with the exact same language. Restating it here adds no design value.

The underlying principle — that components should not accumulate responsibilities — is captured in Confirmed Principle 4. Router's specific scope is a consequence of that principle applied to one component.

---

### "Errors are guides, not crash reports" → Implementation standard

This is good practice that applies to any well-designed library. It does not say anything specific about Titan's design choices or philosophy. The three-part error structure is an implementation standard, not an architectural principle.

It should live in a contributor guide or implementation checklist, not in a document that informs PHILOSOPHY.md.

---

### "Multiple entrypoints, single implementation" → Already in CONTRACT.md §0

This is the Dual Entry principle, documented verbatim in CONTRACT.md §0. Repeating it here creates two sources of record for the same rule, which will eventually diverge.

The principle is valid. Its home is the contract.

---

## Part III — Open Questions

---

### Q1. Where is the layer boundary enforced, if not structurally? `[open]`

Confirmed Principle 2 acknowledges that Titan's depth gradient is enforced by convention, not by Python's import system. This is a known tradeoff.

The question is whether convention is sufficient. PTB uses package separation. Titan uses sub-object hierarchy. One is structural; the other is not.

If convention breaks — if developers habitually use `bot.telegram` inside handlers, or if autocomplete surfaces advanced APIs before simple ones — the Swimming/Diving model collapses in practice while remaining intact in documentation.

No decision. Options range from accepting this as a known tradeoff, to introducing structural markers (type annotations, linting rules, naming patterns), to reconsidering the single-namespace commitment.

---

### Q2. Should `ctx.raw` carry an underscore? `[open]`

`ctx.raw` is public (no underscore) but explicitly non-frozen.

Making it `ctx._raw` would signal "internal, do not rely on this." But it is intentionally accessible to developers who need it. A private-feeling escape hatch discourages exactly the usage it was designed for.

Making it public and non-frozen is the current approach. The risk: developers treat non-frozen as "stable enough," build on it, and then complain when Telegram changes the underlying JSON structure.

No decision has been made.

---

### Q3. Does the alias system fit the layer model? `[open]`

`bot.alias()` operates at a meta-level — renaming ctx methods without changing behavior. It is neither swimming nor diving. It is a naming layer that sits orthogonally to both.

It is fully opt-in. If unused, it leaves no trace. But its existence implies that Titan's API surface is not the final surface — developers can build a custom vocabulary on top of it.

Two interpretations:
1. The alias system is a natural extension of "developer choice of expression" (from CONTRACT.md §0). It belongs.
2. The alias system creates a second, invisible API layer that makes code harder to read for anyone who doesn't know which aliases are active. It is a liability.

No position taken.

---

### Q4. How is feature gravity resisted without structural enforcement? `[open]`

Feature gravity: the tendency for the swimming-layer API to accumulate capabilities from the diving layer, because users find the escape hatch "too far."

PTB has package separation as a structural defense. Titan has the ROADMAP.md rejection log and maintainer judgment.

The rejection log is evidence that this problem has already been anticipated. But a log is reactive. Each request still requires judgment. Over time, edge cases accumulate, and the boundary erodes in small increments that individually seem reasonable.

Question: is there a principled boundary — a rule about what categories of capability belong on `ctx` vs `bot.telegram` — that could make many decisions automatic rather than case-by-case?

No answer yet.

---

### Q5. What does Titan say about state? `[open]`

Titan provides no state management. Conversation state is the developer's responsibility.

The open question is not whether to add FSM — that is unlikely given the stability constraint. The question is whether Titan's design should make an explicit statement about state: where it belongs, how it should be attached to the bot or context, and what patterns are and are not compatible with Titan's model.

Silence is a valid answer. But silence can also be interpreted as "anything goes," which may lead to patterns that conflict with Titan's design in ways that are hard to address later.

---

### Q6. Are `bot.commands`, `bot.handlers`, `bot.callback_handlers` intentionally public? `[open]`

These dicts are directly accessible on the `Titan` instance. Direct mutation bypasses duplicate checks and contract guarantees (noted in ROADMAP.md).

The design question is prior to the implementation question: should registration state be part of the public API?

Arguments for public: developers may need to inspect registered handlers for debugging, testing, or dynamic routing scenarios that Titan does not anticipate.

Arguments for private: these structures are internal bookkeeping. Exposing them invites mutation that violates the contract. Inspection can be served by a read-only API if genuinely needed.

No decision.

---

## Part IV — Tensions Without Resolution

---

### T1. Frozen surface vs progressive depth `[tension]`

Progressive depth implies the surface can grow — new sub-objects, new properties on ctx, new methods on `bot.telegram`.

A frozen API implies the surface does not change.

These are not contradictory, but they create ongoing pressure. Every addition to the progressive surface is a candidate for the frozen API. The discipline required: additions to the diving layer (bot.telegram) are cheap because they follow Telegram's API, not Titan's contract. Additions to the swimming layer (ctx methods, bot decorators) are expensive because they become permanent commitments.

The principle worth holding onto: **the swimming surface is expensive; the diving surface is cheap.**

No structural resolution. Requires case-by-case judgment against that principle.

---

### T2. "ctx is sufficient" vs "bot.telegram is first-class" `[tension]`

If ctx is the primary handler surface, then `bot.telegram` should feel like leaving that surface — deliberate, slightly out of the way.

But `bot.telegram` is documented as a stable, official, first-class entrypoint. It does not feel like an emergency exit. It is designed to feel comfortable.

The risk: if `bot.telegram` is too comfortable, developers default to it regardless of context. ctx becomes a thin wrapper that nobody uses past the first three methods. The design intent collapses without any rule being violated.

This tension has no resolution. It may only be resolvable by observing real usage patterns over time and adjusting documentation to make the gradient more visible.

---

---

## Part IV-B — Rejected Feature Scope

### Tiny Helpers — rejected as independent feature

Investigated recurring patterns across examples and Core. Found three categories:

- **Core gaps** — missing properties on `ctx` or models, not helper opportunities.
- **Sugar** — e.g. `answer_callback()` + action: two trivial lines, different parameters,
  no architectural mistake being prevented. Combining them adds complexity, not clarity.
- **Content decisions** — e.g. display name fallback text. Not the framework's concern.

Decision: Tiny Helpers does not qualify as an independent feature. No Core additions,
no shortcuts for simple operations, no content-decision wrappers.

**Candidate for a future Core feature (not a helper):**

`ctx.message.raw.get("reply_to_message", {}).get("from", {}).get("id")` appears
twice identically in `examples/moderation_bot.py`. This is raw dict access because
`ctx` does not expose the replied-to message's sender. This is a missing `ctx`
property — a Core gap, not a helper. A future feature should add a typed property
(e.g. `ctx.replied_user_id: int | None`) to eliminate this pattern.

---

## Part V — Feature Decisions

Design decisions with full investigation records live in `docs/decisions/`.
Each file there records what was studied, what was decided, and the rule derived.

Index:

- [001 — Keyboard Builder](../decisions/001-keyboard-builder.md) — Rejected. Real problem was a documentation convention, not the API.
- [004 — Error Contracts](../decisions/004-error-contracts.md) — Accepted. Classifies all silent failures; defines TitanError and TelegramError contracts; establishes the three-question rule for any future error. Implemented in Feature #5.
- [005 — Project Health](../decisions/005-project-health.md) — Accepted. `bot.health()` returns `list[HealthFinding]`. Three severity levels: ERROR/WARNING/INFO. Two phases: structural (pre-run) and operational (post-run via capabilities). No side effects — caller decides how to consume findings.
- [006 — Interactive Inspector](../decisions/006-interactive-inspector.md) — Accepted. `bot.inspect()` returns `BotSnapshot` (frozen dataclass). Describes registration state: commands, callbacks, events, middleware_count, has_error_handler, included_router_count, capabilities_available. Inspector describes — Health evaluates. No judgments in Inspector.
- [007 — Migration Assistant](../decisions/007-migration-assistant.md) — Accepted. Two layers in v1: docs/migration/ (philosophy-first guides for PTB/aiogram/telebot) + titan.migration Knowledge API (frameworks(), concepts(), compare() → ConceptMapping). Migration Assistant explains philosophy, not translates code. Version Migration and CLI scanner deferred.

---

## Root Export Policy `[confirmed]`

`titan/__init__.py` is a stability contract, not a convenience re-export of every domain type.

**Rule:** A type may be exported from the root (`from titan import X`) only when:
1. It appears in function signatures that a developer is expected to call or annotate against — i.e., it is part of the observable public API.
2. It is stable: not expected to be renamed, restructured, or removed in the foreseeable roadmap.

**Corollary:** `HealthFinding` and `HealthLevel` qualify because `bot.health()` returns `list[HealthFinding]` and a developer consuming that return value will need to import the type. They are part of the public contract.

**What does not qualify:** Internal intermediary types, implementation details, and types that only appear inside a domain's own module. These stay behind `titan.<domain>` and are imported explicitly if needed (`from titan.health import HealthFinding`).

**Why this matters:** As Titan grows, each domain will produce types. Exporting all of them from the root creates an ever-expanding surface that is hard to version and impossible to shrink without breaking changes. The root must stay narrow so that `from titan import ...` remains a reliable, stable statement — not a grab-bag.

**Checkpoint for future decisions:** Before adding any root export, ask — "does a developer need this type to use the public API, or only to look inside the implementation?"

---

*Last updated: 2026-07-08*
*Previous version: 10 confirmed principles. This version: 7 confirmed, 4 moved out with documented reasons.*
*Source: design discussions, CONTRACT.md, ROADMAP.md, code review of ctx.py / bot.py / keyboard.py*
