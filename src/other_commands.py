from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from src.tables.answer import AnswerType
from src.user_data import UserData
from src.utils import handler_decorator, USER_DATA_KEY
from src.utils2 import send_entity_answers_df


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


@handler_decorator
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("On /cancel")
    return ConversationHandler.END
