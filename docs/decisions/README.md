# Design Decisions

Before a decision reaches this directory, it passes through the feature investigation workflow.
→ [docs/internal/feature-workflow.md](../internal/feature-workflow.md)

Each file in this directory records one design decision made for Titan.

A decision is recorded whenever a feature, API change, or architectural direction was:
- **Accepted** — implemented and merged into the project.
- **Rejected** — investigated seriously and consciously turned down.
- **Deferred** — valid in principle, but not the right time.

Rejected decisions are as important as accepted ones. They prevent the same discussion from happening twice and show that Titan's design is built on engineering investigation, not personal preference.

---

## Format

Each file follows the same structure:

```
# NNN — Title

**Status:** Accepted | Rejected | Deferred

## Proposal
What was proposed and why it seemed worth considering.

## Investigation
What was studied. What the real problem turned out to be.

## Decision
What was decided, and why.

## Rule
The general principle derived from this decision.
Applies to future decisions in the same category.

## Alternatives Considered  [optional]
Other approaches that were evaluated.
For each: what it was, and why it was not chosen.
Include only when alternatives were meaningfully different and the reasoning
behind rejecting them adds value to a future reader.

## Consequences  [optional]
What was gained from this decision.
What constraints or tradeoffs were accepted.
Include only when the tradeoffs are non-obvious or worth remembering.
```

---

## Index

| # | Title | Status |
|---|---|---|
| [001](001-keyboard-builder.md) | Keyboard Builder | Rejected |
| [002](002-actions.md) | Actions | Accepted |
| [003](003-capabilities.md) | Capabilities | Accepted |
| [004](004-error-contracts.md) | Error Contracts | Accepted |
| [005](005-project-health.md) | Project Health | Accepted |
| [006](006-interactive-inspector.md) | Interactive Inspector | Accepted |
| [007](007-migration-assistant.md) | Migration Assistant | Accepted |
| [008](008-message-links-protocol.md) | Message Links Protocol | Accepted |
| [009](009-runtime-contract-validator.md) | Runtime Contract Validator | Accepted |
| [010](010-timeline.md) | Timeline | Accepted |
| [011](011-playground.md) | Playground | Accepted |
| [012](012-design-linter.md) | Design Linter | Accepted |
| [013](013-performance-profiler.md) | Performance Profiler | Accepted |
| [014](014-architect-ai.md) | Titan Light | Accepted |
| [015](015-data-lifecycle-responsibility.md) | Data Lifecycle Responsibility | Accepted |
| [016](016-user-data-registry.md) | User Data Registry و`erase_user` Architecture | Accepted |
| [017](017-reserved-privacy-commands.md) | الأوامر المحجوزة `/mydata` و`/forgetme` | Accepted |
| [018](018-permanent-resource-identity-scope.md) | نطاق Permanent Resource Identity | Accepted |
