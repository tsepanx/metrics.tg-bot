import asyncio
import dataclasses
import os
import datetime
import sys
from typing import Callable
import pandas as pd

import telegram
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, PicklePersistence

from questions import questions_list, questions_objects, Question
from utils import handler_decorator, wrapped_send_text, questions_to_str, merge_to_existing_column, State, \
    ASK_WRONG_FORMAT, get_nth_delta_day, STOP_ASKING, BACKUP_CSV_FNAME, SKIP_QUEST


async def ask_question(q: Question, send_message_f: Callable):
    # buttons = [
    #     *q.inline_keyboard_answers,
    #     SKIP_QUEST,
    #     STOP_ASKING
    # ]

    # reply_markup = telegram.ReplyKeyboardMarkup.from_row(
    #     list(map(str, buttons)),
    #     one_time_keyboard=True,
    #     resize_keyboard=True
    # )

    buttons = [
        q.inline_keyboard_answers,
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
        reply_markup=reply_markup
    )


def get_answers_df() -> pd.DataFrame:
    return pd.read_csv(BACKUP_CSV_FNAME, index_col=0)


async def send_answers_df(update: Update):
    await update.message.reply_document(document=BACKUP_CSV_FNAME)

    answers_df = get_answers_df()

    # Prettify table look by adding questions indexes
    indices = list()
    for ind_str in answers_df.index:
        question_num_id = 0
        for i in range(len(questions_objects)):
            if questions_objects[i].name == ind_str:
                indices.append(i)
                break

        # answers_df = answers_df.rename(index={
        #     ind_str: f'[{question_num_id}] {ind_str}'
        # })

    answers_df.insert(0, 'ind', indices)

    html_table_text = f'<pre>{answers_df.to_markdown()}</pre>'

    await wrapped_send_text(
        update.message.reply_text,
        text=html_table_text,
        parse_mode=ParseMode.HTML
    )

    # import imgkit
    #
    # imgkit.from_string(html_table_text, 'out.png')


async def on_end_asking(state: State, update: Update):
    # Ended question list
    day_index = state.cur_asking_day

    answers_df = get_answers_df()
    # answers_df = answers_df.T  # We transpose it to operate with columns

    # Create empty col if it does not exist
    if answers_df.get(day_index) is None:
        answers_df = answers_df.assign(**{day_index: pd.Series()})

    index_str: list[str] = list(map(
        lambda x: questions_objects[x].name,
        state.include_ids
    ))

    new_col = pd.Series(state.cur_answers, index=index_str)
    res_col = merge_to_existing_column(answers_df[day_index], new_col)

    answers_df = answers_df.reindex(answers_df.index.union(index_str))
    # Sort by columns
    answers_df = answers_df.reindex(sorted(answers_df.columns), axis=1)

    answers_df[day_index] = res_col

    # Writing back to file
    with open(BACKUP_CSV_FNAME, 'w') as file:
        df_csv = answers_df.to_csv()
        file.write(df_csv)

    await send_answers_df(update)
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


@handler_decorator
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.chat_data["state"]

    print('command: ask')

    parsed: AskParseResult = ask_parse_args(context.args)
    if parsed.questions_ids:
        state.include_ids = parsed.questions_ids
    else:
        state.include_ids = list(range(len(questions_list)))

    if parsed.day:
        state.cur_asking_day = str(parsed.day)
    else:
        state.cur_asking_day = str(get_nth_delta_day(0))  # today

    state.cur_id_ind = 0
    state.current_state = 'ask'
    # state.cur_answers = [None for _ in range(max(state.include_ids) + 1)]
    state.cur_answers = [None for _ in range(len(state.include_ids))]

    await wrapped_send_text(
        update.message.reply_text,
        text=f'Asking  questions\n'
             f'List: `{state.include_ids}`\n'
             f'Day: `{state.cur_asking_day}`',
        parse_mode=ParseMode.MARKDOWN
    )

    q = state.get_current_question(questions_objects)
    await ask_question(q, update.message.reply_text)


@handler_decorator
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_answers_df(update)

    quests_str: list[str] = questions_to_str(questions_objects)

    await wrapped_send_text(
        update.message.reply_text,
        text='<pre>' + '\n'.join(quests_str) + '</pre>',
        parse_mode=ParseMode.HTML
    )


@handler_decorator
async def exit_command(update: Update, _):
    await wrapped_send_text(update.message.reply_text, text='Exiting...')

    asyncio.get_event_loop().stop()


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
        "list": list_command,
        "exitt": exit_command
    }

    for command_string, func in commands_funcs_mapping.items():
        app.add_handler(CommandHandler(command_string, func))

    app.add_handler(MessageHandler(filters.TEXT, plaintext_handler))
    app.run_polling()
