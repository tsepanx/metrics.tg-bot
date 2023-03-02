from telegram import Update
from telegram.ext import ContextTypes, Application

from src.tables.answer import AnswerType
from src.user_data import UserData, UserDBCache
from src.utils import handler_decorator, USER_DATA_KEY
from src.utils_send import send_entity_answers_df


@handler_decorator
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data: UserData = context.chat_data[USER_DATA_KEY]  # type: ignore

    await send_entity_answers_df(
        update=update,
        user_data=user_data,
        answers_entity=AnswerType.QUESTION,
    )

    await send_entity_answers_df(
        update=update,
        user_data=user_data,
        answers_entity=AnswerType.EVENT,
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
