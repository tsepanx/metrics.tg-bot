from dataclasses import dataclass
from typing import (
    Callable,
    Optional,
)

from telegram import Update
from telegram.constants import (
    ParseMode,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from src.conversations.utils_ask import (
    build_transpose_callback_data,
    send_entity_answers_df,
)
from src.tables.answer import (
    AnswerType,
)
from src.user_data import (
    UserData,
    UserDBCache,
)
from src.utils import (
    MyEnum,
    format_dt,
    get_now,
)
from src.utils_tg import (
    USER_DATA_KEY,
    handler_decorator,
)


@dataclass
class TgCommand:
    name: str
    handler_func: Optional[Callable]
    description: str

    handler: CommandHandler | None = None

    def __post_init__(self):
        if self.handler_func:
            self.handler = CommandHandler(self.name, self.handler_func)


@handler_decorator
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud: UserData = context.chat_data[USER_DATA_KEY]

    await send_entity_answers_df(
        update=update,
        ud=ud,
        answers_entity=AnswerType.QUESTION,
    )

    await send_entity_answers_df(
        update=update,
        ud=ud,
        answers_entity=AnswerType.EVENT,
    )


@handler_decorator
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud: UserData = context.chat_data[USER_DATA_KEY]

    cur_time: str = format_dt(get_now())

    values: list[tuple[str, str]] = [
        ("User id", update.effective_user.id),
        ("Time on server", cur_time),
        ("DB last reload", format_dt(ud.db_cache.LAST_RELOAD_TIME)),
        ("DEBUG_SQL_OUTPUT", ud.DEBUG_SQL_OUTPUT),
        ("DEBUG_ERRORS_OUTPUT", ud.DEBUG_ERRORS_OUTPUT),
        ("", ""),
        ("Questions entries", len(ud.db_cache.questions)),
        ("Events entries", len(ud.db_cache.events)),
        ("Answers entries", len(ud.db_cache.answers)),
    ]

    text_lines = [
        "=== BOT INFO ===",
        "",
    ]

    name_len = 20
    val_len = 20
    for name, value in values:
        if isinstance(value, bool):
            value = "True" if value else "False"

        text_lines.append(
            f"{name:<{name_len}}: {value:<{val_len}}",
        )

    text = "\n".join(text_lines)
    text = f"`{text}`"

    await update.message.reply_text(text=text, parse_mode=ParseMode.MARKDOWN)


@handler_decorator
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud: UserData = context.chat_data[USER_DATA_KEY]

    ud.conv_storage = None
    await update.message.reply_text(text="Cancelled...")


@handler_decorator
async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud: UserData = context.chat_data[USER_DATA_KEY]

    await update.message.reply_text(text="Reloading from DB...")
    ud.db_cache.reload_all()
    await update.message.reply_text(text="Done")


@handler_decorator
async def on_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud: UserData = context.chat_data[USER_DATA_KEY]

    query = update.callback_query
    assert query is not None

    await query.answer()

    if query.data.startswith("transpose"):
        # answers_type: AnswerType | None = None
        if query.data == build_transpose_callback_data(AnswerType.QUESTION):
            answers_type = AnswerType.QUESTION
        elif query.data == build_transpose_callback_data(AnswerType.EVENT):
            answers_type = AnswerType.EVENT
        else:
            raise Exception(f"Wrong callback data: {query.data}")

        await send_entity_answers_df(
            update,
            ud=ud,
            answers_entity=answers_type,
            send_csv=False,
            send_img=True,
            send_text=False,
            transpose_table=True,
            with_question_indices=False,
        )


class TgCommands(MyEnum):
    STATS = TgCommand("stats", stats_command, "Get questions/events stats")
    INFO = TgCommand("info", info_command, "Get bot debug info")
    ASK = TgCommand("ask", None, "Ask for Question[s] or Event")
    CANCEL = TgCommand("cancel", cancel_command, "Cancel current /ask conversation")
    RELOAD = TgCommand("reload", reload_command, "Reset cache and reload entries data from DB")


async def post_init(application: Application) -> None:
    for _, chat_data in application.chat_data.items():
        ud: UserData = chat_data[USER_DATA_KEY]
        # ud.db_cache.reload_all()
        ud.db_cache = UserDBCache()

    commands_names_desc = [(x.name, x.description) for x in TgCommands.values_list()]
    await application.bot.set_my_commands(commands_names_desc)
