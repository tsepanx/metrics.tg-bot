import asyncio
import dataclasses
import datetime
from typing import (
    Sequence,
)

from telegram import Update
from telegram.constants import (
    ParseMode,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters, PicklePersistence,
)

from src.conversations import (
    conv_handler, on_question_answered, )
from src.other_commands import stats_command
from src.utils2 import build_transpose_callback_data, send_entity_answers_df, send_ask_question
from src.tables.answer import (
    AnswerType,
)
from src.tables.question import (
    QuestionDB,
)
from src.user_data import (
    UserData,
)
from src.utils import (
    ASK_WRONG_FORMAT,
    USER_DATA_KEY,
    get_nth_delta_day,
    handler_decorator,
    wrapped_send_text,
)


# pylint: disable=too-many-arguments, too-many-locals


# pylint: disable=too-many-statements
# @handler_decorator
# async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     @dataclasses.dataclass
#     class AskParseResult:
#         questions_ids: list[int] | None
#         day: datetime.date | None
#
#     def ask_parse_args(context_args: Sequence[str]) -> AskParseResult:
#         res = AskParseResult(None, None)
#
#         if len(context_args) == 0:
#             return res
#
#         if len(context_args) > 2:
#             raise ASK_WRONG_FORMAT
#
#         for arg in context_args:
#             try:
#                 if arg.startswith("-d"):
#                     val = arg[3:]
#
#                     try:
#                         val = datetime.date.fromisoformat(val)
#                         res.day = val
#                     except Exception:
#                         val = int(val)
#                         res.day = get_nth_delta_day(val)
#
#                 elif arg.startswith("-q"):
#                     val = arg[3:]
#                     val = val.split(",")
#                     val = list(map(int, val))
#
#                     res.questions_ids = val
#                 else:
#                     raise Exception
#             except Exception as exc:
#                 raise ASK_WRONG_FORMAT from exc
#
#         return res
#
#     assert update.message is not None
#
#     print("command: ask")
#     parsed: AskParseResult = ask_parse_args(context.args)
#
#     if parsed.day:
#         asking_day = parsed.day
#     else:
#         asking_day = get_nth_delta_day(0)  # today
#
#     user_data: UserData = context.chat_data[USER_DATA_KEY]  # type: ignore
#     answers_df = user_data.db_cache.questions_answers_df()
#     qnames = user_data.db_cache.questions_names()
#     all_questions: list[QuestionDB] = user_data.db_cache.questions
#
#     assert answers_df is not None
#     assert qnames is not None
#
#     if parsed.questions_ids:
#         include_indices = parsed.questions_ids
#     else:
#         all_indices = list(range(len(qnames)))
#
#         if asking_day in answers_df.columns:
#             day_values_isnull = answers_df[asking_day].isnull().reset_index().drop("index", axis=1)
#
#             # Filter to get indices of only null values
#             include_indices = list(
#                 day_values_isnull
#                 .apply(lambda x: None if bool(x[0]) is False else 1, axis=1)
#                 .dropna()
#                 .index
#             )
#         else:
#             include_indices = all_indices
#
#         if len(include_indices) == 0:
#             include_indices = all_indices
#
#     include_questions = list(map(lambda i: all_questions[i], include_indices))
#     user_data.state = QuestionsAskingState(include_questions, asking_day)
#
#     await wrapped_send_text(
#         update.message.reply_text,
#         text=f"Asking  questions\n" f"List: `{include_indices}`\n" f"Day: `{asking_day}`",
#         parse_mode=ParseMode.MARKDOWN,
#     )
#
#     first_question = user_data.state.get_current_question()
#     await send_ask_question(first_question, update.message.reply_text)


@handler_decorator
async def exit_command(update: Update, _):
    assert update.message is not None

    await wrapped_send_text(update.message.reply_text, text="Exiting...")

    asyncio.get_event_loop().stop()


@handler_decorator
async def on_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data: UserData = context.chat_data[USER_DATA_KEY]  # type: ignore

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
            user_data=user_data,
            answers_entity=answers_type,
            send_csv=False,
            send_img=True,
            send_text=False,
            transpose_table=True,
            with_question_indices=False,
        )


async def post_init(application: Application) -> None:
    commands_list = [
        (k, v[1]) for k, v in commands_mapping.items() if v[1]
    ]

    for _, chat_data in application.chat_data.items():
        user_data: UserData = chat_data[USER_DATA_KEY]
        user_data.db_cache.reload_all()

    #     events_names: list[str] = user_data.db_cache.events_names()
    #     commands_list += list(map(lambda x: [f"event_{x}", x], events_names))
    #
    #     question_names: list[str] = user_data.db_cache.questions_names()
    #     commands_list += list(map(lambda x: [f"question_{x}", x], question_names))
    #
    # await application.bot.set_my_commands(commands_list)


if __name__ == "__main__":
    with open(".token", encoding="utf-8") as f:
        TOKEN = f.read()
        print(TOKEN)

    # persistence = PicklePersistence(filepath="persitencebot", update_interval=1)

        # .persistence(persistence)\
    app = ApplicationBuilder() \
        .token(TOKEN)\
        .post_init(post_init)\
        .build()

    commands_mapping = {
        # "ask": (ask_command, "Ask for 'Questions' on given day"),
        "stats": (stats_command, "Get statddds"),
        "exitt": (exit_command, ""),
    }

    for command_string, (func, _) in commands_mapping.items():
        app.add_handler(CommandHandler(command_string, func))

    # app.add_handler(MessageHandler(filters.TEXT, on_question_answered))
    # app.add_handler(CallbackQueryHandler(on_callback_query))
    app.add_handler(conv_handler)
    # app.add_handler(InlineQueryHandler(on_inline_query))
    app.run_polling()
