"""
titan.migration._data

بيانات Migration Knowledge API — private.

لا تُستورد مباشرةً. تُقرأ فقط من titan.migration.__init__.
"""

from __future__ import annotations

from titan.migration.models import ConceptMapping


# ---------------------------------------------------------------------------
# PTB — python-telegram-bot
# ---------------------------------------------------------------------------

_PTB: dict[str, ConceptMapping] = {
    "command": ConceptMapping(
        framework="ptb",
        concept="command",
        source_name="CommandHandler('start', fn)",
        titan_equivalent="@bot.command('start')",
        difference=(
            "PTB registers handlers via app.add_handler(CommandHandler(...)) imperatively. "
            "Titan uses a decorator directly on the function. "
            "PTB allows multiple handlers for the same command via priorities; "
            "Titan enforces exactly one handler per command and raises TitanError on conflict."
        ),
        note=(
            "If you relied on PTB's priority system to chain handlers, "
            "redesign using bot.middleware() or a single handler that branches internally."
        ),
    ),
    "handler": ConceptMapping(
        framework="ptb",
        concept="handler",
        source_name="MessageHandler(filters.TEXT, fn)",
        titan_equivalent="@bot.on('message')",
        difference=(
            "PTB uses Filter objects (filters.TEXT, filters.PHOTO, etc.) to narrow handler scope. "
            "Titan uses event strings ('message', 'new_member', 'channel', ...). "
            "Filtering within the event is done inside the handler body using ctx properties."
        ),
        note=(
            "Titan does not have a filter system. If your PTB code relies heavily on "
            "MessageHandler(filters.Regex(...), fn), move that logic into the handler body: "
            "check ctx.text with a condition before acting."
        ),
    ),
    "middleware": ConceptMapping(
        framework="ptb",
        concept="middleware",
        source_name="Application.post_init / TypeHandler",
        titan_equivalent="@bot.middleware",
        difference=(
            "PTB does not have a true middleware system. "
            "Pre/post processing is done via Application lifecycle hooks or TypeHandler ordering. "
            "Titan has an explicit middleware chain: each function receives ctx and next(); "
            "calling next() continues, not calling it stops the update."
        ),
    ),
    "context": ConceptMapping(
        framework="ptb",
        concept="context",
        source_name="update: Update, context: ContextTypes.DEFAULT_TYPE",
        titan_equivalent="ctx: Context",
        difference=(
            "PTB passes two separate objects to every handler: update (the raw Telegram update) "
            "and context (PTB's own context with bot, args, user_data, etc.). "
            "Titan unifies everything into a single ctx object: data (ctx.text, ctx.user_id, ...) "
            "and actions (ctx.reply(), ctx.ban_user(), ...) are on the same object."
        ),
        note=(
            "PTB's context.user_data and context.chat_data (in-memory persistence) "
            "have no direct equivalent in Titan. Use your own storage solution."
        ),
    ),
    "callback": ConceptMapping(
        framework="ptb",
        concept="callback",
        source_name="CallbackQueryHandler(fn, pattern=r'^yes$')",
        titan_equivalent="@bot.callback('yes')",
        difference=(
            "PTB matches callback_data using regex patterns via CallbackQueryHandler(pattern=...). "
            "Titan matches by exact string: @bot.callback('yes') handles only 'yes'. "
            "Titan also provides @bot.on('callback') as a fallback for unmatched callback_data."
        ),
        note=(
            "If you used PTB patterns like pattern=r'^menu_' to group related buttons, "
            "redesign: either use exact data strings per button, or route via on('callback') "
            "and branch on ctx.callback_data inside the handler."
        ),
    ),
    "routing": ConceptMapping(
        framework="ptb",
        concept="routing",
        source_name="ConversationHandler",
        titan_equivalent="No direct equivalent — use AskManager (titan.extras.ask)",
        difference=(
            "PTB's ConversationHandler manages multi-step conversations with state machines. "
            "Titan does not have a conversation state machine. "
            "For simple ask/reply flows, use titan.extras.ask.AskManager. "
            "For complex FSM-style conversations, maintain state in your own storage."
        ),
        note=(
            "This is a redesign, not a translation. ConversationHandler is a PTB-specific "
            "abstraction. AskManager handles the common case; complex flows need explicit state."
        ),
    ),
    "error_handler": ConceptMapping(
        framework="ptb",
        concept="error_handler",
        source_name="app.add_error_handler(fn)",
        titan_equivalent="@bot.error_handler",
        difference=(
            "PTB registers error handlers via app.add_error_handler(fn) imperatively. "
            "Titan uses a decorator: @bot.error_handler. "
            "Titan supports exactly one error handler; PTB allows multiple. "
            "The signature is the same concept: (ctx, exception)."
        ),
    ),
    "startup": ConceptMapping(
        framework="ptb",
        concept="startup",
        source_name="app.run_polling() / Application.post_init",
        titan_equivalent="bot.run() / bot.run_async()",
        difference=(
            "PTB uses app.run_polling() which manages the event loop internally, "
            "or run_async with manual loop management. "
            "Titan provides bot.run() (sync, manages loop) and bot.run_async() (async). "
            "PTB's post_init/post_shutdown lifecycle hooks have no Titan equivalent — "
            "run initialization code before calling bot.run()."
        ),
    ),
}


# ---------------------------------------------------------------------------
# aiogram
# ---------------------------------------------------------------------------

_AIOGRAM: dict[str, ConceptMapping] = {
    "command": ConceptMapping(
        framework="aiogram",
        concept="command",
        source_name="@dp.message(Command('start'))",
        titan_equivalent="@bot.command('start')",
        difference=(
            "aiogram uses filters on @dp.message() to match commands: @dp.message(Command('start')). "
            "Titan has a dedicated decorator: @bot.command('start'). "
            "aiogram allows multiple handlers for the same command via filter priority; "
            "Titan enforces exactly one handler per command and raises TitanError on conflict."
        ),
    ),
    "handler": ConceptMapping(
        framework="aiogram",
        concept="handler",
        source_name="@dp.message(F.text)",
        titan_equivalent="@bot.on('message')",
        difference=(
            "aiogram handlers receive a typed object directly: async def fn(message: Message). "
            "The type in the signature determines which updates the handler receives. "
            "Titan handlers always receive ctx: Context regardless of update type. "
            "aiogram's Magic Filter (F.text, F.photo, ...) narrows scope at registration. "
            "In Titan, filtering is done inside the handler body using ctx properties."
        ),
        note=(
            "The biggest mental shift from aiogram to Titan: you no longer use the type "
            "to express 'what this handler handles'. Use @bot.on('message') for messages, "
            "@bot.on('new_member') for joins, etc."
        ),
    ),
    "middleware": ConceptMapping(
        framework="aiogram",
        concept="middleware",
        source_name="dp.update.outer_middleware() / dp.message.middleware()",
        titan_equivalent="@bot.middleware",
        difference=(
            "aiogram has outer middleware (runs before routing) and inner middleware "
            "(runs after routing, per-handler type). This allows different behavior per update type. "
            "Titan has one update-level middleware chain only — no per-type or per-handler granularity."
        ),
        note=(
            "If you used aiogram inner middleware to inject per-handler dependencies (e.g. db session), "
            "in Titan: create the dependency in middleware and attach it to ctx using setattr, "
            "or manage it in your handler directly. "
            "If you need different behavior per update type, branch inside one middleware using "
            "ctx.callback_data is None or ctx.text checks."
        ),
    ),
    "context": ConceptMapping(
        framework="aiogram",
        concept="context",
        source_name="message: Message / query: CallbackQuery (typed injection)",
        titan_equivalent="ctx: Context",
        difference=(
            "aiogram uses dependency injection: the handler signature declares what it needs "
            "(message: Message, bot: Bot, state: FSMContext), and aiogram provides them. "
            "Titan uses a single unified ctx object for all update types. "
            "ctx.text, ctx.user_id, ctx.callback_data, ctx.reply(), etc. — all in one place."
        ),
        note=(
            "aiogram's FSMContext (state machine) has no equivalent in Titan. "
            "Use titan.extras.ask.AskManager for simple ask/reply flows, "
            "or manage state yourself with an external store."
        ),
    ),
    "callback": ConceptMapping(
        framework="aiogram",
        concept="callback",
        source_name="@dp.callback_query(F.data == 'yes')",
        titan_equivalent="@bot.callback('yes')",
        difference=(
            "aiogram matches callback queries with Magic Filters: F.data == 'yes', "
            "F.data.startswith('menu_'), F.data.regexp(r'^item_\\d+$'). "
            "Titan matches by exact string only: @bot.callback('yes'). "
            "No prefix matching, no regex. Use @bot.on('callback') + branching in handler "
            "for dynamic data patterns."
        ),
        note=(
            "If your aiogram code uses prefix-based callback data (e.g. 'item_42', 'item_17'), "
            "route through on('callback') and parse ctx.callback_data in the handler body."
        ),
    ),
    "routing": ConceptMapping(
        framework="aiogram",
        concept="routing",
        source_name="Router() with nested routers and filters",
        titan_equivalent="Router() via bot.include(router)",
        difference=(
            "aiogram Router supports nesting: routers inside routers, each with its own filters. "
            "Titan Router is a flat organization tool only — no nesting, no filters on the router. "
            "bot.include(router) merges all handlers into the bot with conflict detection."
        ),
        note=(
            "If you used aiogram's nested routers to apply group-level filters "
            "(e.g. 'all handlers in this router only run in private chats'), "
            "move that logic into middleware or into each handler's body."
        ),
    ),
    "error_handler": ConceptMapping(
        framework="aiogram",
        concept="error_handler",
        source_name="@dp.errors()",
        titan_equivalent="@bot.error_handler",
        difference=(
            "aiogram uses @dp.errors() decorator. Titan uses @bot.error_handler. "
            "Both receive (context, exception). "
            "Titan supports exactly one error handler; aiogram can have multiple via filters."
        ),
    ),
    "startup": ConceptMapping(
        framework="aiogram",
        concept="startup",
        source_name="await dp.start_polling(bot) / dp.startup.register(fn)",
        titan_equivalent="bot.run() / bot.run_async()",
        difference=(
            "aiogram requires creating a Bot object and a Dispatcher separately, "
            "then calling await dp.start_polling(bot). "
            "Titan combines both: Titan(token) creates the bot, bot.run() starts polling. "
            "aiogram's startup/shutdown signals (@dp.startup, @dp.shutdown) have no equivalent — "
            "run initialization before bot.run() and cleanup after."
        ),
    ),
}


# ---------------------------------------------------------------------------
# telebot — pyTelegramBotAPI
# ---------------------------------------------------------------------------

_TELEBOT: dict[str, ConceptMapping] = {
    "command": ConceptMapping(
        framework="telebot",
        concept="command",
        source_name="@bot.message_handler(commands=['start'])",
        titan_equivalent="@bot.command('start')",
        difference=(
            "telebot uses @bot.message_handler(commands=['start', 'help']) "
            "which accepts a list — one handler for multiple commands. "
            "Titan registers one command at a time: @bot.command('start'), @bot.command('help'). "
            "Titan raises TitanError if the same command is registered twice."
        ),
    ),
    "handler": ConceptMapping(
        framework="telebot",
        concept="handler",
        source_name="@bot.message_handler(content_types=['text'])",
        titan_equivalent="@bot.on('message')",
        difference=(
            "telebot filters handlers at registration via content_types, func=lambda, etc. "
            "Titan uses event strings: @bot.on('message'). "
            "Filtering by content type or other conditions is done inside the handler "
            "using ctx.text, ctx.message.raw, etc."
        ),
    ),
    "context": ConceptMapping(
        framework="telebot",
        concept="context",
        source_name="message: types.Message (passed directly)",
        titan_equivalent="ctx: Context",
        difference=(
            "telebot passes the raw Telegram object directly to handlers: "
            "async def fn(message: types.Message). "
            "Titan wraps everything in ctx: ctx.text, ctx.user_id, ctx.reply(), etc. "
            "Actions in telebot are bot.send_message(chat_id, ...). "
            "In Titan, actions are ctx.reply(), ctx.send(), ctx.edit(), etc."
        ),
    ),
    "callback": ConceptMapping(
        framework="telebot",
        concept="callback",
        source_name="@bot.callback_query_handler(func=lambda c: c.data == 'yes')",
        titan_equivalent="@bot.callback('yes')",
        difference=(
            "telebot uses @bot.callback_query_handler(func=lambda c: ...) with an arbitrary filter. "
            "Titan uses exact string matching: @bot.callback('yes'). "
            "telebot allows regex-like filters via the func parameter. "
            "Titan: use @bot.on('callback') + branch on ctx.callback_data for dynamic patterns."
        ),
    ),
    "routing": ConceptMapping(
        framework="telebot",
        concept="routing",
        source_name="No built-in module system",
        titan_equivalent="Router() via bot.include(router)",
        difference=(
            "telebot has no built-in way to split handlers across files — "
            "developers import the bot object and register handlers on it directly. "
            "Titan provides Router: create a Router in each file, register handlers on it, "
            "then bot.include(router) to merge. No global bot object import needed."
        ),
    ),
    "error_handler": ConceptMapping(
        framework="telebot",
        concept="error_handler",
        source_name="try/except inside each handler",
        titan_equivalent="@bot.error_handler",
        difference=(
            "telebot has no global error handler. Errors must be caught manually in each handler. "
            "Titan provides @bot.error_handler: one function catches all unhandled exceptions "
            "from any handler, receiving (ctx, exception)."
        ),
    ),
    "startup": ConceptMapping(
        framework="telebot",
        concept="startup",
        source_name="bot.polling() / asyncio_helper.polling()",
        titan_equivalent="bot.run() / bot.run_async()",
        difference=(
            "telebot uses bot.polling() (sync) or asyncio_helper.polling() (async). "
            "Titan: bot.run() is sync, bot.run_async() is async. "
            "telebot's non-stop=True polling option maps to Titan's built-in backoff retry. "
            "Titan automatically retries with exponential backoff on polling errors."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

FRAMEWORKS: dict[str, dict[str, ConceptMapping]] = {
    "ptb": _PTB,
    "aiogram": _AIOGRAM,
    "telebot": _TELEBOT,
}
