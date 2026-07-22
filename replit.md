# titanx

A minimal, stability-driven asynchronous Python framework for building Telegram bots.

## Project Overview

**titanx** is a Python library (not a web app) that provides a clean API for building Telegram bots using `asyncio` and `aiohttp`. It emphasizes readable code and predictable runtime behavior.

This is the development environment for the **Titan framework itself** — not a bot built on top of it. Work here follows ADR-driven development: every feature passes through investigation → ADR → implementation.

## Tech Stack

- **Language:** Python 3.10+
- **Async Engine:** asyncio
- **HTTP Client:** aiohttp >= 3.9
- **Testing:** pytest + pytest-asyncio

## Project Structure

- `src/titan/` — Core framework source code
  - `bot.py` — Main `Titan` class (update loops, event registration, privacy API)
  - `ctx.py` — Context object passed to handlers
  - `router.py` — `Router` class for modular handler organization
  - `telegram.py` — Telegram Bot API methods
  - `adapter.py` — Maps raw JSON updates to framework objects
  - `models/` — Data classes (Message, Chat, Sender)
  - `extras/` — Optional utilities (AliasMap, AskManager)
  - `keyboard.py` — InlineKeyboard / InlineButton builder
  - `health/` — `bot.health()` — structural & operational diagnostics
  - `inspector.py` — `bot.inspect()` → BotSnapshot (registration state)
  - `lint/` — `bot.lint()` → LintFinding list (convention checks)
  - `migration/` — `titan.migration` knowledge API (ConceptMapping)
  - `links/` — Message Links Protocol (LinksManager, SqliteMessageStore)
  - `privacy/` — Privacy Protocol (UserDataRegistry, UserDataModule, /mydata & /forgetme handlers)
  - `timeline/` — `titan.timeline` architectural memory API
  - `playground/` — `titan.playground` test harness (feed_update, RecordingTelegram)
  - `validation.py` — Runtime Contract Validator (decorator-time signature checks)
  - `recipes/` — `titan.recipes` curated usage patterns
- `tests/` — Full test suite (859 tests, all passing)
- `examples/` — Sample bot implementations
- `docs/` — Architecture documentation
  - `docs/decisions/` — ADRs (001–018)
  - `docs/internal/` — Investigations, design notes, feature workflow
  - `docs/internal/expected-failure-cases.md` — Privacy Protocol failure contract
  - `docs/migration/` — Philosophy-first migration guides (PTB, aiogram, telebot)

## Running Tests

```bash
python -m pytest tests/ -v
```

## Building for PyPI

```bash
pip install build twine wheel
python -m build --no-isolation .   # produces dist/ with .whl and .tar.gz
python -m twine check dist/*       # verify package metadata before upload
python -m twine upload dist/*      # upload to PyPI (requires credentials)
```

> Note: `python -m build` (with isolation) does not work in Replit's environment.
> Use `--no-isolation` instead — requires `wheel` to be installed first.

## Development Workflow

Every feature follows the order in `docs/internal/feature-workflow.md`:
1. State the problem from the developer's perspective
2. Investigate the current Core
3. Decide whether the problem is real
4. Determine the minimum intervention
5. Write an ADR in `docs/decisions/` if the decision is non-trivial
6. Implement

Source of truth: `CONTRACT.md`, `ROADMAP.md`, `docs/decisions/`, `docs/internal/investigations/`

## Completed Features (as of 2026-07-16)

| Feature | ADR |
|---|---|
| Message Links Protocol | 008 |
| Interactive Inspector (`bot.inspect()`) | 006 |
| Migration Assistant (`titan.migration`) | 007 |
| Project Health (`bot.health()`) | 005 |
| Runtime Contract Validator | 009 |
| Playground (`titan.playground`) | 011 |
| Design Linter (`bot.lint()`) | 012 |
| Architectural Timeline (`titan.timeline`) | 010 |
| Performance Profiler (`titan.profiler`) | 013 |
| Titan Light (`titan.light`) | 014 |
| Data Lifecycle Responsibility | 015 |
| User Data Registry (`UserDataRegistry`, `erase_user`, `data_held_for`) | 016 |
| Reserved Privacy Commands (`/mydata`, `/forgetme`) | 017 |
| Permanent Resource Identity Scope | 018 |

Silent Failures cleanup (SF-01, SF-02, SF-06) is also closed — see `docs/internal/investigations/silent-failures.md` and `CHANGELOG.md`.

## Privacy Protocol API (ADR-015–017)

```python
# Third-party module registration
bot.declare_user_data(MyModule())

# First-party optional module (AskManager)
ask = bot.enable_ask()

# Programmatic access
await bot.erase_user(user_id=123456789)
report = await bot.data_held_for(user_id=123456789)

# Hooks (optional — shape output, not contract)
@bot.on_mydata_format
async def format_report(ctx, report):   # report is MappingProxyType — read-only
    return my_formatter(report)

@bot.on_forgetme_complete
async def after_erasure(ctx):           # called after erase, never before
    await my_db.delete_user(ctx.user_id)
```

Reserved commands `/mydata` and `/forgetme` are active in every Titan bot automatically.

## Planned / Under Investigation

- **Userbot Support** — deferred consciously; revisit only on real need or v2 milestone. See `docs/internal/investigations/userbot-support.md`.
- **Read-only Runtime Registries** — open API-design question (should `bot.commands`/`bot.handlers` become read-only?), deliberately not decided before launch — see ROADMAP.md
- **Test Isolation Improvement (#12)** — internal quality follow-up, not blocking any release — see ROADMAP.md

## Installation

```bash
pip install -e ".[dev]"
```

## User Preferences

- No web frontend; this is a Python library project.
- Answer the user in Arabic.
- This project is the development of Titan itself, not building a Telegram bot on top of it.
- Philosophy: explicit over implicit, minimal core, clean APIs, one responsibility per component, architecture first.
- Never redesign the architecture without discussion.
- Always investigate the existing implementation before proposing changes.
- Prefer documenting conventions over adding new APIs.
- Introduce new APIs only when a real problem cannot be solved by improving the existing design.
- Treat every feature as an architecture task first, then an implementation task.
- Work on one feature at a time — do not bundle multiple features together.
- If anything is unclear, stop and ask instead of guessing.
- Every feature must pass through: investigation → ADR (if non-trivial) → implementation.
- Do not start implementing features without completing the investigation phase first.
- Treat CONTRACT.md, ROADMAP.md, ADRs, and investigation docs as the source of truth.
