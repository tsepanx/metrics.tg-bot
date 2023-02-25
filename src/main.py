import asyncio
import copy
import dataclasses
import datetime
from io import BytesIO
from typing import (
    Callable,
)

import pandas as pd
import telegram
from telegram import (
    Update,
)
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
    PicklePersistence,
    filters,
)

from src.db import (
    QuestionDB,
    update_or_insert_row,
)
from src.utils import (
    ASK_WRONG_FORMAT,
    SKIP_QUEST,
    STOP_ASKING,
    USER_DATA_KEY,
    AskingState,
    MyException,
    UserData,
    answers_df_backup_fname,
    get_nth_delta_day,
    handler_decorator,
    wrapped_send_text, text_to_png, data_to_bytesio, df_to_markdown,
)


async def send_ask_question(q: QuestionDB, send_message_f: Callable):
    buttons = [list(map(str, q.suggested_answers_list)), [SKIP_QUEST, STOP_ASKING]]

    reply_markup = telegram.ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)

    question_text = f"<code>{q.type_fk.notation_str}</code> {q.fulltext}"

    await wrapped_send_text(send_message_f, question_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


# pylint: disable=too-many-arguments, too-many-locals
async def send_answers_df(
    update: Update,
    answers_df: pd.DataFrame,
    send_csv=False,
    send_img=True,
    send_text=False,
    transpose_table=False,
    with_question_indices=True,
    sort_by_quest_indices=True,
):
    # Fix dirty function applying changes directly to passed DataFrame
    answers_df = answers_df.copy()

    # --- Adding temporary index column, to sort by it, and show it with table
    # Important thing is not to save this col to df, because question number is not hardly associated with question

    # answers_df = add_questions_sequence_num_as_col(
    #     answers_df,
    #     questions_objects
    # )

    i_col = list(range(len(answers_df.index)))
    # noinspection PyTypeChecker
    answers_df.insert(0, "i", i_col)

    if sort_by_quest_indices:
        answers_df = answers_df.sort_values("i")

    # 'i' column was used just for sorting
    if not with_question_indices:
        answers_df = answers_df.drop("i", axis=1)

    # --- ---

    # await send_df_in_formats(
    #     update, answers_df, send_csv=send_csv, send_img=send_img, send_text=send_text, transpose_table=transpose_table
    # )

    md_text = df_to_markdown(answers_df, transpose=transpose_table)
    csv_text = answers_df.to_csv()

    if not transpose_table:
        message_object = update.message
    else:
        message_object = update.callback_query.message

    if send_csv:
        bytes_io = data_to_bytesio(csv_text, "answers_df.csv")
        await message_object.reply_document(document=bytes_io)

    if send_img:
        img = text_to_png(md_text)

        bio = BytesIO()
        bio.name = "img.png"

        img.save(bio, "png")
        bio.seek(0)

        bio2 = copy.copy(bio)

        if not transpose_table:
            keyboard = [[telegram.InlineKeyboardButton("transposed table IMG", callback_data="transpose")]]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = None

        try:
            await message_object.reply_photo(bio, reply_markup=reply_markup)
        except telegram.error.BadRequest:
            await message_object.reply_document(bio2, reply_markup=reply_markup)
    if send_text:
        html_table_text = f"<pre>\n{md_text}\n</pre>"

        await wrapped_send_text(
            message_object.reply_text,
            text=html_table_text,
            parse_mode=ParseMode.HTML
        )


async def on_end_asking(user_data: UserData, update: Update, save_csv=True):
    def update_db(state: AskingState):
        answers = state.cur_answers

        for i, answer in enumerate(answers):
            answer: str
            day: str = state.asking_day
            qname = state.include_questions[i].name

            if answer is None:
                continue

            where_dict = {"day_fk": day, "question_fk": qname}

            update_or_insert_row(where_dict, {"answer_text": answer}, "question_answer")

    # Updating DataFrame is not needed anymore, as it will be restored from db: new_answers -> db -> build_answers_df
    update_db(user_data.state)

    # TODO grubber collector check
    user_data.reload_answers_df_from_db(cols=[user_data.state.asking_day])
    user_data.state = None

    if save_csv:
        fname_backup = answers_df_backup_fname(update.effective_chat.id)
        user_data.answers_df.to_csv(fname_backup)

    await send_answers_df(update, user_data.answers_df, send_csv=True)


@handler_decorator
async def plaintext_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # state = context.chat_data["state"]
    user_data: UserData = context.chat_data[USER_DATA_KEY]
    state = user_data.state
    # qnames = user_data.questions_names

    # if state.current_state == 'ask':
    if isinstance(state, AskingState):
        q: QuestionDB = state.get_current_question()

        user_ans = update.message.text

        if user_ans not in [SKIP_QUEST, STOP_ASKING]:
            try:
                if q.answer_apply_func:
                    user_ans = q.answer_apply_func(user_ans)
            except Exception as exc:
                raise MyException("Error parsing answer, try again") from exc

        if user_ans == SKIP_QUEST:
            user_ans = None

        if user_ans == STOP_ASKING:
            await on_end_asking(user_data, update)
            return

        # state.cur_answers[state.include_qnames[state.cur_id_ind]] = user_ans
        state.cur_answers[state.cur_id_ind] = user_ans
        print(q.fulltext, ": ", user_ans)

        state.cur_id_ind += 1

        if state.cur_id_ind < len(state.include_questions):
            q = state.get_current_question()
            await send_ask_question(q, update.message.reply_text)
        else:
            await on_end_asking(user_data, update)


# pylint: disable=too-many-statements
@handler_decorator
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    @dataclasses.dataclass
    class AskParseResult:
        questions_ids: list[int] | None
        day: datetime.date | None

    def ask_parse_args(context_args) -> AskParseResult:
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

    # state = context.chat_data["state"]
    user_data: UserData = context.chat_data[USER_DATA_KEY]

    if user_data.state is not None:
        pass  # Existing command is in action

    print("command: ask")
    parsed: AskParseResult = ask_parse_args(context.args)

    if parsed.day:
        asking_day = str(parsed.day)
    else:
        asking_day = str(get_nth_delta_day(0))  # today

    answers_df = user_data.answers_df
    qnames = user_data.questions_names

    if parsed.questions_ids:
        include_indices = parsed.questions_ids
    else:
        all_indices = list(range(len(qnames)))

        if asking_day in answers_df.columns:
            day_values = answers_df[asking_day].isnull().reset_index().drop("index", axis=1)

            # Filter to get index of only null values
            include_indices = list(
                day_values.apply(lambda x: None if bool(x[0]) is False else 1, axis=1).dropna().index
            )
        else:
            include_indices = all_indices

        if len(include_indices) == 0:
            include_indices = all_indices

    include_names = list(map(lambda x: qnames[x], include_indices))

    user_data.state = AskingState(include_qnames=include_names, asking_day=asking_day)

    await wrapped_send_text(
        update.message.reply_text,
        text=f"Asking  questions\n" f"List: `{include_indices}`\n" f"Day: `{asking_day}`",
        parse_mode=ParseMode.MARKDOWN,
    )

    q = user_data.state.get_current_question()
    await send_ask_question(q, update.message.reply_text)


@handler_decorator
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.chat_data[USER_DATA_KEY]

    await send_answers_df(update, user_data.answers_df)


def on_add_question(user_data: UserData):
    user_data.questions_names = None


@handler_decorator
async def add_question_command(_: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.chat_data[USER_DATA_KEY]

    on_add_question(user_data)


@handler_decorator
async def exit_command(update: Update, _):
    await wrapped_send_text(update.message.reply_text, text="Exiting...")

    asyncio.get_event_loop().stop()


@handler_decorator
async def on_inline_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.chat_data[USER_DATA_KEY]

    query = update.callback_query
    await query.answer()

    if query.data == "transpose":
        await send_answers_df(
            update,
            user_data.answers_df,
            send_csv=False,
            send_img=True,
            send_text=False,
            transpose_table=True,
            with_question_indices=False,
        )


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        list(
            filter(
                lambda x: x is not None,
                (map(lambda x: [x[0], x[1][1]] if len(x[1]) > 1 else None, commands_mapping.items())),
            )
        )
    )


if __name__ == "__main__":
    with open(".token", encoding='utf-8') as f:
        TOKEN = f.read()
        print(TOKEN)

    persistence = PicklePersistence(filepath="persitencebot", update_interval=1)

    app = ApplicationBuilder().persistence(persistence).token(TOKEN).post_init(post_init).build()

    commands_mapping = {
        "ask": (ask_command, "Start asking"),
        "stats": (stats_command, "Get stats"),
        "exitt": (exit_command,),
    }

    for command_string, value in commands_mapping.items():
        func = value[0]
        app.add_handler(CommandHandler(command_string, func))

    app.add_handler(MessageHandler(filters.TEXT, plaintext_handler))
    app.add_handler(CallbackQueryHandler(on_inline_button))
    app.run_polling()
