import os
import datetime
from typing import Callable
import pandas as pd

import telegram
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, PicklePersistence

from questions import questions_list, questions_objects, Question
from utils import handler_decorator, wrapped_send_text, questions_to_str, merge_to_existing_column, State

DEFAULT_TZ = datetime.timezone(datetime.timedelta(hours=3))
PERIODICAL_FETCHING_TIME = datetime.time(hour=18, tzinfo=DEFAULT_TZ)

MIN_TIME = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

BACKUP_CSV_FNAME = 'backup.csv'

STOP_ASKING = 'Stop asking'
SKIP_QUEST = 'Skip question'


async def ask_question(q: Question, send_message_f: Callable):
    buttons = [
        *q.inline_keyboard_answers,
        SKIP_QUEST,
        STOP_ASKING
    ]

    reply_markup = telegram.ReplyKeyboardMarkup.from_row(
        list(map(str, buttons)),
        one_time_keyboard=True
    )

    await wrapped_send_text(
        send_message_f,
        q.text,
        reply_markup=reply_markup
    )


async def on_end_asking(state: State, update: Update):
    # Ended question list

    today = str(datetime.date.today())  # index of target col

    answers_df = pd.read_csv(BACKUP_CSV_FNAME, index_col=0)
    # answers_df = answers_df.T  # We transpose it to operate with columns

    # Create empty col if it does not exist
    if answers_df.get(today) is None:
        answers_df = answers_df.assign(**{today: pd.Series()})

    index_str: list[str] = list(map(
        lambda x: questions_objects[x].name,
        state.include_ids
    ))

    new_col = pd.Series(state.cur_answers, index=index_str)
    res_col = merge_to_existing_column(answers_df[today], new_col)

    answers_df = answers_df.reindex(answers_df.index.union(index_str))
    answers_df[today] = res_col

    # Writing back to file
    with open(BACKUP_CSV_FNAME, 'w') as file:
        df_csv = answers_df.to_csv()
        file.write(df_csv)

    # Send this file
    await update.message.reply_document(document=BACKUP_CSV_FNAME)
    await wrapped_send_text(
        update.message.reply_text,
        text=f'<pre>{answers_df.to_markdown()}</pre>',
        parse_mode=ParseMode.HTML
    )

    state.reset()


@handler_decorator
async def plaintext_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.chat_data["state"]

    if state.current_state == 'ask':
        q: Question = state.get_current_question(questions_objects)

        user_ans = update.message.text

        if user_ans not in [SKIP_QUEST, STOP_ASKING]:
            if q.answer_mapping_func:
                user_ans = q.answer_mapping_func(user_ans)

        if user_ans == SKIP_QUEST:
            user_ans = None

        if user_ans == STOP_ASKING:
            await on_end_asking(state, update)
            return

        # state.cur_answers[state.include_ids[state.cur_id_ind]] = user_ans
        state.cur_answers[state.cur_id_ind] = user_ans
        print(q.text, ": ", user_ans)

        state.cur_id_ind += 1

        if state.cur_id_ind < len(state.include_ids):
            q = state.get_current_question(questions_objects)
            await ask_question(q, update.message.reply_text)
        else:
            await on_end_asking(state, update)


@handler_decorator
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.chat_data["state"]
    print('command: ask')

    # Set proper State attrs
    if len(context.args) > 0:
        state.include_ids = list(map(int, context.args))
    else:
        state.include_ids = list(range(len(questions_list)))

    state.cur_id_ind = 0
    state.current_state = 'ask'
    # state.cur_answers = [None for _ in range(max(state.include_ids) + 1)]
    state.cur_answers = [None for _ in range(len(state.include_ids))]

    q = state.get_current_question(questions_objects)
    await ask_question(q, update.message.reply_text)


@handler_decorator
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quests_str: list[str] = questions_to_str(questions_objects)

    return await wrapped_send_text(
        update.message.reply_text,
        text='<pre>' + '\n'.join(quests_str) + '</pre>',
        parse_mode=ParseMode.HTML
    )


if __name__ == "__main__":
    if not os.path.exists(BACKUP_CSV_FNAME):
        with open(BACKUP_CSV_FNAME, 'w') as f:
            init_answers_df = pd.DataFrame(
                index=list(map(lambda x: x.name, questions_objects))
            )
            f.write(init_answers_df.to_csv())

    TOKEN = open('.token').read()
    print(TOKEN)

    persistence = PicklePersistence(filepath='persitencebot', update_interval=1)

    app = ApplicationBuilder() \
        .persistence(persistence) \
        .token(TOKEN) \
        .build()

    commands_funcs_mapping = {
        "ask": ask_command,
        "list": list_command
    }

    for command_string, func in commands_funcs_mapping.items():
        app.add_handler(CommandHandler(command_string, func))

    app.add_handler(MessageHandler(filters.TEXT, plaintext_handler))
    app.run_polling()
