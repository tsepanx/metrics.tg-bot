import asyncio
import copy
import dataclasses
import datetime

import pandas as pd

from typing import Callable
from io import BytesIO

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, PicklePersistence, \
    CallbackQueryHandler

from questions import questions_list, questions_objects, Question
from utils import handler_decorator, wrapped_send_text, merge_to_existing_column, AskingState, \
    ASK_WRONG_FORMAT, get_nth_delta_day, STOP_ASKING, SKIP_QUEST, df_to_markdown, \
    add_question_indices_to_df_index, USER_DATA_KEY, UserData, answers_df_backup_fname


async def send_ask_question(q: Question, send_message_f: Callable):
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


async def send_df_in_formats(
        update: Update,
        df: pd.DataFrame,
        send_csv=False,
        send_img=True,
        send_text=False,
        transpose_table=False,
):
    async def send_img_func(text: str, bold=True):
        indent = 5
        indent_point = (indent, indent)

        bg_color = (200, 200, 200)
        fg_color = (0, 0, 0)

        from PIL import Image, ImageDraw, ImageFont
        if bold:
            font = ImageFont.truetype("fonts/SourceCodePro-Bold.otf", 16)
        else:
            font = ImageFont.truetype("fonts/SourceCodePro-Regular.otf", 16)

        x1, y1, x2, y2 = ImageDraw.Draw(Image.new('RGB', (0, 0))).textbbox(indent_point, text, font)

        img = Image.new('RGB', (x2 + indent, y2 + indent), bg_color)
        d = ImageDraw.Draw(img)

        d.text(
            indent_point,
            text,
            font=font,
            fill=fg_color,
        )

        bio = BytesIO()
        bio.name = 'img.png'

        img.save(bio, 'png')
        bio.seek(0)

        bio2 = copy.copy(bio)

        if not transpose_table:
            keyboard = [[InlineKeyboardButton("transposed table IMG", callback_data="transpose")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # message_object = update.message
        else:
            reply_markup = None
            # message_object = update.callback_query.message

        try:
            await message_object.reply_photo(bio, reply_markup=reply_markup)
        except telegram.error.BadRequest:
            await message_object.reply_document(bio2, reply_markup=reply_markup)

    async def send_text_func(text: str):
        html_table_text = f'<pre>\n{text}\n</pre>'

        await wrapped_send_text(
            message_object.reply_text,
            text=html_table_text,
            parse_mode=ParseMode.HTML
        )

    async def send_csv_func(csv_str: str):
        bio = BytesIO()
        bio.name = 'answers_df.csv'
        bio.write(bytes(csv_str, 'utf-8'))
        bio.seek(0)

        await message_object.reply_document(document=bio)

    md_text = df_to_markdown(df, transpose=transpose_table)
    csv_text = df.to_csv()

    if not transpose_table:
        message_object = update.message
    else:
        message_object = update.callback_query.message

    if send_csv:
        await send_csv_func(csv_text)
    if send_img:
        await send_img_func(md_text)
        # await send_img_func(table_text_transposed)
    if send_text:
        await send_text_func(md_text)


async def send_answers_df(
        update: Update,
        answers_df: pd.DataFrame,
        send_csv=False,
        send_img=True,
        send_text=False,
        # save_csv=True,
        transpose_table=False,
        with_question_indices=True,
        sort_by_quest_indices=True,
        with_fulltext=True,
):
    # Fix dirty function applying changes directly to passed DataFrame
    answers_df = answers_df.copy()

    if not with_fulltext:
        answers_df = answers_df.drop('fullname', axis=1)

    # --- Adding temporary index column, to sort by it, and show it with table
    # Important thing is not to save this col to df, because question number is not hardly associated with question

    # if with_question_indices:
    answers_df = add_question_indices_to_df_index(
        answers_df,
        questions_objects
    )

    if sort_by_quest_indices:
        answers_df = answers_df.sort_values('i')

    # 'i' column was used just for sorting
    if not with_question_indices:
        answers_df = answers_df.drop('i', axis=1)

    # --- ---

    await send_df_in_formats(
        update,
        answers_df,
        send_csv=send_csv,
        send_img=send_img,
        send_text=send_text,
        transpose_table=transpose_table
    )


def reconstruct_answers_df_with_new_answers(df: pd.DataFrame, state: AskingState) -> pd.DataFrame:
    # Ended question list
    day_index = state.asking_day

    # answers_df = get_answers_df()

    # Create empty col if it does not exist
    if df.get(day_index) is None:
        df = df.assign(**{day_index: pd.Series()})

    index_str: list[str] = list(map(
        lambda x: questions_objects[x].name,
        state.include_ids
    ))

    new_col = pd.Series(state.cur_answers, index=index_str)
    res_col = merge_to_existing_column(df[day_index], new_col)

    df = df.reindex(df.index.union(index_str))
    # Sort by columns
    columns_order = sorted(
        df.columns,
        key=lambda x: '!' + x if not x.startswith('20') else x
    )
    df = df.reindex(columns_order, axis=1)

    df[day_index] = res_col
    return df


@handler_decorator
async def plaintext_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def on_end_asking(user_data: UserData, update: Update, save_csv=True):
        user_data.answers_df = reconstruct_answers_df_with_new_answers(
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

    # state = context.chat_data["state"]
    user_data: UserData = context.chat_data[USER_DATA_KEY]
    state = user_data.state

    # if state.current_state == 'ask':
    if isinstance(state, AskingState):
        q: Question = state.get_current_question(questions_objects)

        user_ans = update.message.text

        if user_ans not in [SKIP_QUEST, STOP_ASKING]:
            if q.answer_mapping_func:
                user_ans = q.answer_mapping_func(user_ans)

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
    
    # user_data.state = AskingState()

    print('command: ask')

    parsed: AskParseResult = ask_parse_args(context.args)
    if parsed.questions_ids:
        include_ids = parsed.questions_ids
    else:
        include_ids = list(range(len(questions_list)))

    if parsed.day:
        asking_day = str(parsed.day)
    else:
        asking_day = str(get_nth_delta_day(0))  # today

    # state.cur_id_ind = 0
    # state.current_state = 'ask'
    # state.cur_answers = [None for _ in range(max(state.include_ids) + 1)]
    # state.cur_answers = [None for _ in range(len(state.include_ids))]
    
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
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.chat_data[USER_DATA_KEY]

    await send_answers_df(
        update,
        user_data.answers_df
    )


@handler_decorator
async def exit_command(update: Update, _):
    await wrapped_send_text(update.message.reply_text, text='Exiting...')

    asyncio.get_event_loop().stop()


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


if __name__ == "__main__":
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
    app.add_handler(CallbackQueryHandler(on_inline_button))
    app.run_polling()
