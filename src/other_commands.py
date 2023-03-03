from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
)

from src.conversations.utils_ask import (
    build_transpose_callback_data,
    send_entity_answers_df,
)
from src.tables.answer import (
    AnswerType,
)
from src.user_data import UserData
from src.utils_tg import (
    USER_DATA_KEY,
    handler_decorator,
)


@handler_decorator
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud: UserData = context.chat_data[USER_DATA_KEY]  # type: ignore

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


async def post_init(application: Application) -> None:
    for _, chat_data in application.chat_data.items():
        user_data: UserData = chat_data[USER_DATA_KEY]
        user_data.db_cache.reload_all()
        # user_data.db_cache = UserDBCache()

    commands_list = [
        # (k, v[1]) for k, v in commands_mapping.items() if v[1]
        ("ask", "Ask for Question[s] or Event"),
        ("stats", "Get stats"),
    ]
    await application.bot.set_my_commands(commands_list)
