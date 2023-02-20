import os
import datetime
from typing import Callable
import pandas as pd

import telegram
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, PicklePersistence

from questions import questions_list, questions_objects
from utils import handler_decorator, wrapped_send_text, questions_to_str, Question

DEFAULT_TZ = datetime.timezone(datetime.timedelta(hours=3))
PERIODICAL_FETCHING_TIME = datetime.time(hour=18, tzinfo=DEFAULT_TZ)

MIN_TIME = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

BACKUP_CSV_FNAME = 'backup.csv'


async def ask_question(q: Question, send_message: Callable):
    reply_markup = telegram.ReplyKeyboardMarkup.from_row(
        list(map(lambda x: str(x), q.inline_keyboard_answers)),
        one_time_keyboard=True
    )

    await wrapped_send_text(
        send_message,
        q.text,
        reply_markup=reply_markup
    )


@handler_decorator
async def plaintext_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.chat_data["state"]

    if state.current_state == 'ask':
        q = state.get_current_question(questions_objects)

        user_ans = update.message.text

        # state.cur_answers.append(user_answer_text)
        state.cur_answers[q.num_id] = user_ans
        print(q.text, ": ", user_ans)

        state.cur_id_ind += 1

        if state.cur_id_ind < len(state.include_ids):
            q = state.get_current_question(questions_objects)
            await ask_question(q, update.message.reply_text)
        else:
            # Ended question list
            index_day = str(datetime.date.today())
            answers_pd = pd.read_csv(BACKUP_CSV_FNAME, index_col=0)
            answers_pd = answers_pd.T

            if answers_pd.get(index_day, None) is None:
                answers_pd = answers_pd.assign(**{index_day: pd.Series()})

            existing_day_col = answers_pd[index_day]
            new_col = pd.DataFrame(
                state.cur_answers,
                index=answers_pd.index[:len(state.cur_answers)],
                columns=[index_day]
            )  # .T.iloc[0]

            # new_col_list = list()
            for i in range(len(existing_day_col)):
                old_val = existing_day_col[i]
                new_val = new_col.iloc[:, 0][i]

                res_val = old_val if pd.isnull(new_val) else new_val
                # new_col_list.append(res_val)
                new_col.iloc[:, 0][i] = res_val

            # res_col = pd.DataFrame(new_col_list, index=questions_to_str, columns=[index_day])
            res_col = new_col

            # Adding new column to DataFrame
            answers_pd[index_day] = res_col
            answers_pd = answers_pd.T

            # Writing back to file
            with open(BACKUP_CSV_FNAME, 'w') as file:
                # df_csv = new_df.to_csv()
                df_csv = answers_pd.to_csv()
                file.write(df_csv)

            # Send this file
            await update.message.reply_document(document=BACKUP_CSV_FNAME)
            await wrapped_send_text(
                update.message.reply_text,
                text=f'<pre>{answers_pd.to_markdown()}</pre>',
                parse_mode=ParseMode.HTML
            )

            state.reset()


@handler_decorator
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.chat_data["state"]
    print('command: ask')

    if len(context.args) > 0:
        include_ids = list(map(int, context.args))
    else:
        include_ids = list(range(1, len(questions_list) + 1))

    state.include_ids = include_ids
    state.cur_id_ind = 0
    state.current_state = 'ask'
    state.cur_answers = [None for _ in range(max(state.include_ids) + 1)]

    q = state.get_current_question(questions_objects)
    await ask_question(q, update.message.reply_text)


@handler_decorator
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quests_str: list[str] = questions_to_str(questions_objects, default_val='-')

    return await wrapped_send_text(
        update.message.reply_text,
        text='\n'.join(quests_str)
    )


if __name__ == "__main__":
    if not os.path.exists(BACKUP_CSV_FNAME):
        with open(BACKUP_CSV_FNAME, 'w') as f:
            answers_pd = pd.DataFrame(
                columns=questions_to_str(questions_objects)
            )
            f.write(answers_pd.to_csv())

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
