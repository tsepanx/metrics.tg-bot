import asyncio
import copy
import dataclasses
import datetime
from io import BytesIO
from typing import Callable, Sequence

import pandas as pd
import telegram
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
    InlineQueryHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from src.orm.base import update_or_insert_row, ColumnDC
from src.tables.answer import AnswerType
from src.tables.question import QuestionDB
from src.utils import (
    ASK_WRONG_FORMAT,
    SKIP_QUEST,
    STOP_ASKING,
    MyException,
    answers_df_backup_fname,
    data_to_bytesio,
    df_to_markdown,
    get_nth_delta_day,
    handler_decorator,
    text_to_png,
    wrapped_send_text, USER_DATA_KEY,
)
from src.user_data import UserData, AskingState


async def send_ask_question(q: QuestionDB, send_text_func: Callable):
    buttons = [
        list(map(str, q.suggested_answers_list)),
        [SKIP_QUEST, STOP_ASKING]
    ]

    reply_markup = telegram.ReplyKeyboardMarkup(
        buttons,
        one_time_keyboard=True,
        resize_keyboard=True
    )

    await wrapped_send_text(
        send_text_func,
        text=q.html_notation(),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


def build_transpose_callback_data(answer_type: AnswerType) -> str:
    return f"transpose {answer_type.name}"


async def send_entity_answers_df(answers_entity: AnswerType, *args, **kwargs):
    transpose_callback_data = build_transpose_callback_data(answers_entity)

    return await send_dataframe(
        *args,
        transpose_button_callback_data=transpose_callback_data,
        **kwargs
    )


# pylint: disable=too-many-arguments, too-many-locals
async def send_dataframe(
        update: Update,
        df: pd.DataFrame,
        send_csv=False,
        send_img=True,
        send_text=False,
        transpose_table=False,
        transpose_button_callback_data: str = None,
        with_question_indices=True,
):
    # Fix dirty function applying changes directly to passed DataFrame
    df = df.copy()

    # [0, 1, 2, 3, ...]
    i_column = list(range(len(df.index)))
    # noinspection PyTypeChecker
    df.insert(0, "i", i_column)

    # if sort_by_quest_indices:
    #     answers_df = answers_df.sort_values("i")

    # 'i' column was used just for sorting
    if not with_question_indices:
        df = df.drop("i", axis=1)

    md_text = df_to_markdown(df, transpose=transpose_table)
    csv_text = df.to_csv()

    if not transpose_table:
        assert update.message is not None
        message_object = update.message
    else:
        assert update.callback_query is not None
        assert update.callback_query.message is not None
        message_object = update.callback_query.message

    if send_csv:
        bytes_io = data_to_bytesio(csv_text, "dataframe.csv")
        await message_object.reply_document(document=bytes_io)

    if send_img:
        img = text_to_png(md_text)

        bio = BytesIO()
        bio.name = "img.png"

        img.save(bio, "png")
        bio.seek(0)

        bio2 = copy.copy(bio)

        if not transpose_table:
            keyboard = [[telegram.InlineKeyboardButton(
                "transposed table IMG",
                callback_data=transpose_button_callback_data
            )]]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = None

        try:
            await message_object.reply_photo(bio, reply_markup=reply_markup)  # type: ignore
        except telegram.error.BadRequest:
            await message_object.reply_document(bio2, reply_markup=reply_markup)  # type: ignore
    if send_text:
        html_table_text = f"<pre>\n{md_text}\n</pre>"

        # fmt: off
        await wrapped_send_text(
            message_object.reply_text,
            text=html_table_text,
            parse_mode=ParseMode.HTML
        )
        # fmt: on


async def on_end_asking(user_data: UserData, update: Update, save_csv=True):
    def update_db_with_answers(state: AskingState):
        answers = state.cur_answers

        for i, text in enumerate(answers):
            # answer: str
            day = state.asking_day

            assert state.include_questions is not None
            question_pk = state.include_questions[i].pk

            if text is None:
                continue

            update_or_insert_row(
                tablename="answer",
                where_clauses={
                    ColumnDC(column_name="date"): day,
                    ColumnDC(column_name="question_fk"): question_pk
                },
                set_dict={
                    ColumnDC(column_name="text"): text
                },
            )

    assert user_data.state is not None

    if any(user_data.state.cur_answers):
        update_db_with_answers(user_data.state)
        user_data.db_cache.reload_all()

    user_data.state = None
    answers_df = user_data.db_cache.questions_answers_df()

    if save_csv:
        fname_backup = answers_df_backup_fname(update.effective_chat.id)  # type: ignore
        answers_df.to_csv(fname_backup)

    await send_entity_answers_df(
        answers_entity=AnswerType.QUESTION,
        update=update,
        df=answers_df,
        send_csv=True
    )


@handler_decorator
async def plaintext_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message is not None

    # state = context.chat_data["state"]
    user_data: UserData = context.chat_data[USER_DATA_KEY]  # type: ignore
    state = user_data.state

    # if state.current_state == 'ask':
    if isinstance(state, AskingState):
        assert state.include_questions is not None

        q: QuestionDB = state.get_current_question()

        answer_text = update.message.text

        if answer_text == SKIP_QUEST:
            answer_text = None
        elif answer_text == STOP_ASKING:
            await on_end_asking(user_data, update)
            return
        else:
            try:
                if q.answer_apply_func:
                    answer_text = q.answer_apply_func(answer_text)
            except Exception as exc:
                raise MyException("Error parsing answer, try again") from exc

        state.cur_answers[state.cur_i] = answer_text
        state.cur_i += 1

        if state.cur_i >= len(state.include_questions):
            return await on_end_asking(user_data, update)

        q = state.get_current_question()
        await send_ask_question(q, update.message.reply_text)


# pylint: disable=too-many-statements
@handler_decorator
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    @dataclasses.dataclass
    class AskParseResult:
        questions_ids: list[int] | None
        day: datetime.date | None

    def ask_parse_args(context_args: Sequence[str]) -> AskParseResult:
        res = AskParseResult(None, None)

        if len(context_args) == 0:
            return res

        if len(context_args) > 2:
            raise ASK_WRONG_FORMAT

        for arg in context_args:
            try:
                if arg.startswith("-d"):
                    val = arg[3:]

                    try:
                        val = datetime.date.fromisoformat(val)
                        res.day = val
                    except Exception:
                        val = int(val)
                        res.day = get_nth_delta_day(val)

                elif arg.startswith("-q"):
                    val = arg[3:]
                    val = val.split(",")
                    val = list(map(int, val))

                    res.questions_ids = val
                else:
                    raise Exception
            except Exception as exc:
                raise ASK_WRONG_FORMAT from exc

        return res

    assert update.message is not None

    print("command: ask")
    parsed: AskParseResult = ask_parse_args(context.args)

    if parsed.day:
        asking_day = parsed.day
    else:
        asking_day = get_nth_delta_day(0)  # today

    user_data: UserData = context.chat_data[USER_DATA_KEY]  # type: ignore
    answers_df = user_data.db_cache.questions_answers_df()
    qnames = user_data.db_cache.questions_names()
    all_questions: list[QuestionDB] = user_data.db_cache.questions

    assert answers_df is not None
    assert qnames is not None

    if parsed.questions_ids:
        include_indices = parsed.questions_ids
    else:
        all_indices = list(range(len(qnames)))

        if asking_day in answers_df.columns:
            day_values_isnull = answers_df[asking_day].isnull().reset_index().drop("index", axis=1)

            # Filter to get indices of only null values
            include_indices = list(
                day_values_isnull
                .apply(lambda x: None if bool(x[0]) is False else 1, axis=1)
                .dropna()
                .index
            )
        else:
            include_indices = all_indices

        if len(include_indices) == 0:
            include_indices = all_indices

    include_questions = list(map(lambda i: all_questions[i], include_indices))
    user_data.state = AskingState(include_questions, asking_day)

    await wrapped_send_text(
        update.message.reply_text,
        text=f"Asking  questions\n" f"List: `{include_indices}`\n" f"Day: `{asking_day}`",
        parse_mode=ParseMode.MARKDOWN,
    )

    first_question = user_data.state.get_current_question()
    await send_ask_question(first_question, update.message.reply_text)


@handler_decorator
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data: UserData = context.chat_data[USER_DATA_KEY]  # type: ignore

    quest_answers_df = user_data.db_cache.questions_answers_df()
    event_answers_df = user_data.db_cache.events_answers_df()

    await send_entity_answers_df(
        answers_entity=AnswerType.QUESTION,
        update=update,
        df=quest_answers_df
    )

    await send_entity_answers_df(
        answers_entity=AnswerType.EVENT,
        update=update,
        df=event_answers_df
    )


def on_add_question(user_data: UserData):
    user_data.questions_names = None


@handler_decorator
async def add_question_command(_: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data: UserData = context.chat_data[USER_DATA_KEY]  # type: ignore

    on_add_question(user_data)


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
        answers_type: AnswerType | None = None
        if query.data == build_transpose_callback_data(AnswerType.QUESTION):
            answers_type = AnswerType.QUESTION
        elif query.data == build_transpose_callback_data(AnswerType.EVENT):
            answers_type = AnswerType.EVENT

        if answers_type is None:
            raise Exception(f"Wrong callback data: {query.data}")

        answers_df = user_data.db_cache.common_answers_df(answers_type=answers_type)

        await send_entity_answers_df(
            answers_type,
            update,
            answers_df,
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

    await application.bot.set_my_commands([
        (k, v[1]) for k, v in commands_mapping.items() if v[1]
    ])


if __name__ == "__main__":
    with open(".token", encoding="utf-8") as f:
        TOKEN = f.read()
        print(TOKEN)

    persistence = PicklePersistence(filepath="persitencebot", update_interval=1)

    app = ApplicationBuilder().persistence(persistence).token(TOKEN).post_init(post_init).build()

    commands_mapping = {
        "ask": (ask_command, "Ask for 'Questions' on given day"),
        "stats": (stats_command, "Get statddds"),
        "exitt": (exit_command, ""),
    }

    for command_string, (func, _) in commands_mapping.items():
        app.add_handler(CommandHandler(command_string, func))

    app.add_handler(MessageHandler(filters.TEXT, plaintext_handler))
    app.add_handler(CallbackQueryHandler(on_callback_query))
    # app.add_handler(InlineQueryHandler(on_inline_query))
    app.run_polling()
