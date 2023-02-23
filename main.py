import asyncio
import dataclasses
import datetime
from typing import (
    Callable
)

import pandas as pd
import telegram
from telegram import (
    Update
)
from telegram.constants import (
    ParseMode
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters
)

from db.db import get_questions_names
from questions import (
    Question,
)
from utils import (  # add_questions_sequence_num_as_col,
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
    merge_to_existing_column,
    send_df_in_formats,
    wrapped_send_text
)


async def send_ask_question(q: Question, send_message_f: Callable):
    buttons = [
        list(map(str, q.inline_keyboard_answers)),
        [SKIP_QUEST, STOP_ASKING]
    ]

    reply_markup = telegram.ReplyKeyboardMarkup(
        buttons,
        one_time_keyboard=True,
        resize_keyboard=True
    )

    await wrapped_send_text(
        send_message_f,
        q.text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


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
    #
    # if sort_by_quest_indices:
    #     answers_df = answers_df.sort_values('i')
    #
    # # 'i' column was used just for sorting
    # if not with_question_indices:
    #     answers_df = answers_df.drop('i', axis=1)

    # --- ---

    await send_df_in_formats(
        update,
        answers_df,
        send_csv=send_csv,
        send_img=send_img,
        send_text=send_text,
        transpose_table=transpose_table
    )


async def on_end_asking(user_data: UserData, update: Update, save_csv=True):
    def update_answers_df(
            df: pd.DataFrame,
            state: AskingState,
            sort_columns=True,
            sort_rows_by_q_index=True,
    ) -> pd.DataFrame:

        old_shape = df.shape

        # Ended question list
        day_index = state.asking_day

        # Create empty col if it does not exist
        if df.get(day_index) is None:
            df = df.assign(**{day_index: pd.Series()})

        qnames = get_questions_names()
        included_qnames: list[str] = list(map(
            lambda x: qnames[x],
            state.include_ids
        ))

        new_col = pd.Series(state.cur_answers, index=included_qnames)
        # Needed to convert automatic conversion to numpy types (f.e. numpy.int64) to initial pythonic type back
        new_col = new_col.astype(object)

        res_col = merge_to_existing_column(df[day_index], new_col)

        df = df.reindex(df.index.union(included_qnames))

        if sort_columns:
            columns_order = sorted(
                df.columns,
                key=lambda x: '!' + x if not isinstance(x, datetime.date) else x
            )
            df = df.reindex(columns_order, axis=1)

        # if sort_rows_by_q_index:
        #     if 'i' not in df.columns:
        #         df = add_questions_sequence_num_as_col(df, questions_objects)
        #
        #     df = df.sort_values('i')
        #     df = df.drop('i', axis=1)

        df[day_index] = res_col

        new_shape = df.shape

        print('Updating answers_df')
        if old_shape == new_shape:
            print(f'shape not changed: {old_shape}')
        else:
            print(f'shape changed!\noldshape: {old_shape}\nnew shape: {new_shape}')

        return df

    user_data.answers_df = update_answers_df(
        user_data.answers_df,
        user_data.state
    )

    # TODO grubber collector check
    user_data.state = None

    if save_csv:
        fname_backup = answers_df_backup_fname(update.effective_chat.id)

        user_data.answers_df.to_csv(fname_backup)

    await send_answers_df(
        update,
        user_data.answers_df,
        send_csv=True
    )


@handler_decorator
async def plaintext_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # state = context.chat_data["state"]
    user_data: UserData = context.chat_data[USER_DATA_KEY]
    state = user_data.state

    # if state.current_state == 'ask':
    if isinstance(state, AskingState):
        q: Question = state.get_current_question(questions_objects)

        user_ans = update.message.text

        if user_ans not in [SKIP_QUEST, STOP_ASKING]:
            try:
                if q.answer_mapping_func:
                    user_ans = q.answer_mapping_func(user_ans)
            except Exception:
                raise MyException('Error parsing answer, try again')

        if user_ans == SKIP_QUEST:
            user_ans = None

        if user_ans == STOP_ASKING:
            await on_end_asking(user_data, update)
            return

        # state.cur_answers[state.include_ids[state.cur_id_ind]] = user_ans
        state.cur_answers[state.cur_id_ind] = user_ans
        print(q.text, ": ", user_ans)

        state.cur_id_ind += 1

        if state.cur_id_ind < len(state.include_ids):

            q = state.get_current_question(questions_objects)
            await send_ask_question(q, update.message.reply_text)
        else:
            await on_end_asking(user_data, update)


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
                if arg.startswith('-d'):
                    val = arg[3:]

                    try:
                        val = datetime.date.fromisoformat(val)
                        res.day = val
                    except Exception:
                        val = int(val)
                        res.day = get_nth_delta_day(val)

                elif arg.startswith('-q'):
                    val = arg[3:]
                    val = val.split(',')
                    val = list(map(int, val))

                    res.questions_ids = val
                else:
                    raise Exception
            except Exception:
                raise ASK_WRONG_FORMAT

        return res

    # state = context.chat_data["state"]
    user_data = context.chat_data[USER_DATA_KEY]

    if user_data.state is not None:
        pass  # Existing command is in action

    print('command: ask')
    parsed: AskParseResult = ask_parse_args(context.args)

    if parsed.day:
        asking_day = str(parsed.day)
    else:
        asking_day = str(get_nth_delta_day(0))  # today

    answers_df = user_data.answers_df

    if parsed.questions_ids:
        include_ids = parsed.questions_ids
    else:
        all_ids = list(range(len(questions_objects)))

        if asking_day in answers_df.columns:
            day_values = answers_df[asking_day].isnull().reset_index().drop('index', axis=1)

            # Filter to get index of only null values
            include_ids = list(day_values.apply(
                lambda x: None if bool(x[0]) is False else 1,
                axis=1).dropna().index
                               )
        else:
            include_ids = all_ids

        if len(include_ids) == 0:
            include_ids = all_ids

    user_data.state = AskingState(
        include_ids=include_ids,
        asking_day=asking_day
    )

    await wrapped_send_text(
        update.message.reply_text,
        text=f'Asking  questions\n'
             f'List: `{include_ids}`\n'
             f'Day: `{asking_day}`',
        parse_mode=ParseMode.MARKDOWN
    )

    q = user_data.state.get_current_question(questions_objects)
    await send_ask_question(q, update.message.reply_text)


@handler_decorator
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.chat_data[USER_DATA_KEY]

    await send_answers_df(
        update,
        user_data.answers_df
    )


@handler_decorator
async def exit_command(update: Update, _):
    await wrapped_send_text(update.message.reply_text, text='Exiting...')

    asyncio.get_event_loop().stop()


@handler_decorator
async def on_inline_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.chat_data[USER_DATA_KEY]

    query = update.callback_query
    await query.answer()

    if query.data == 'transpose':
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
        list(filter(
            lambda x: x is not None,
            (map(
                lambda x: [x[0], x[1][1]] if len(x[1]) > 1 else None,
                commands_mapping.items()
            ))
        ))
    )


if __name__ == "__main__":
    TOKEN = open('.token').read()
    print(TOKEN)

    persistence = PicklePersistence(filepath='persitencebot', update_interval=1)

    app = ApplicationBuilder() \
        .persistence(persistence) \
        .token(TOKEN) \
        .post_init(post_init) \
        .build()

    commands_mapping = {
        "ask": (ask_command, 'Start asking'),
        "stats": (stats_command, 'Get stats'),
        "exitt": (exit_command,)
    }

    for command_string, value in commands_mapping.items():
        func = value[0]
        app.add_handler(CommandHandler(command_string, func))

    app.add_handler(MessageHandler(filters.TEXT, plaintext_handler))
    app.add_handler(CallbackQueryHandler(on_inline_button))
    app.run_polling()
