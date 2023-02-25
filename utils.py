import copy
import datetime
import functools
import traceback
from functools import (
    wraps
)
from io import (
    BytesIO
)
from pprint import (
    pprint
)

import numpy as np
import pandas as pd
import telegram
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.constants import (
    ParseMode
)
from telegram.ext import (
    ContextTypes
)

import db
from db import (
    QuestionDB
)

answers_df_backup_fname = lambda chat_id: f"answers_df_backups/{chat_id}.csv"


class MyException(Exception):
    pass


def ask_format_example():
    return '\n'.join([
        'Examples:',
        '`{:18}` For today, all questions'.format('/ask'),
        '`{:18}` Specific day (isoformat)'.format('/ask -d=2023-01-01'),
        '`{:18}` Yesterday'.format('/ask -d=-1'),
        '`{:18}` Specify questions to ask'.format('/ask -q=1,2,3'),
        '`{:18}` Multiple args'.format('/ask -q=1,2,3 -d=2023-01-01'),
    ])


ASK_WRONG_FORMAT = MyException(
    '`=== /ask: wrong format ===`\n' +
    ask_format_example()
)

MAX_MSG_LEN = 7000


class AskingState:
    include_questions: list[QuestionDB] | None
    asking_day: str

    cur_id_ind: int
    cur_answers: list[str | None]

    def __init__(self, include_qnames: list, asking_day: str):
        self.asking_day = asking_day

        self.cur_id_ind = 0
        self.cur_answers = [None for _ in range(len(include_qnames))]
        self.include_questions = db.high_level_methods.get_questions_with_type_fk(include_qnames)

    def get_current_question(self) -> QuestionDB:
        return self.include_questions[self.cur_id_ind]


# @dataclass
class UserData:
    state: AskingState | None
    answers_df: pd.DataFrame | None
    questions_names: list[str] | None

    def __init__(self):
        self.state = None  # AskingState(None)
        self.answers_df = None
        self.questions_names = None

    def reload_answers_df_from_db(self):
        # TODO optionally reload only given list of columns
        self.answers_df = db.build_answers_df()

    def reload_qnames(self):
        self.questions_names = db.get_ordered_questions_names()


USER_DATA_KEY = 'data'

CHAT_DATA_KEYS_DEFAULTS = {
    # 'state': State(None),
    USER_DATA_KEY: lambda: UserData()
}


def add_questions_sequence_num_as_col(
        df: pd.DataFrame,
        questions: list[QuestionDB]
):
    """
    Generate
    Prettify table look by adding questions ids to index

    Assumes given @df has "questions names" as index
    """
    sequential_numbers = list()

    for index_i in df.index:
        for i in range(len(questions)):
            if questions[i].name == index_i:
                # s = str(i)
                sequential_numbers.append(i)
                break

    # Setting new index column
    # df = df.reset_index()
    # df = df.drop('index', axis=1)

    # new_index_name = 'i  | name'

    # df.insert(0, new_index_name, indices)
    # df = df.set_index(new_index_name)

    df = df.copy()
    # noinspection PyTypeChecker
    df.insert(0, 'i', sequential_numbers)

    return df


def merge_to_existing_column(old_col: pd.Series, new_col: pd.Series) -> pd.Series:
    """
    Merge two pd.Series objects (with same length), replacing value with new, when possible
    """
    index = old_col.index.union(new_col.index)
    res_col = pd.Series(index=index).astype(object)

    for i_str in index:
        old_val = old_col.get(i_str, None)
        new_val = new_col.get(i_str, None)

        res_val = old_val if pd.isnull(new_val) else new_val
        res_col[i_str] = res_val

    return res_col


def get_divided_long_message(text, max_size) -> [str, str]:
    """
    Cuts long message text with \n separator

    @param text: str - given text
    @param max_size: int - single text message max size

    return: text part from start, and the rest of text
    """
    subtext = text[:max_size]
    border = subtext.rfind('\n')

    subtext = subtext[:border]
    text = text[border:]

    return subtext, text


async def wrapped_send_text(send_message_func, text: str, *args, **kwargs):
    if len(text) > MAX_MSG_LEN:
        lpart, rpart = get_divided_long_message(text, MAX_MSG_LEN)

        await send_message_func(*args, text=lpart, **kwargs)
        await wrapped_send_text(send_message_func, *args, text=rpart, **kwargs)
    else:
        await send_message_func(*args, text=text, **kwargs)


def to_list(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> list:
        res = list(func(*args, **kwargs))
        return res

    return wrapper


def handler_decorator(func):
    """
    Wrapper over each handler
    @param func: handler func
    """

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        pprint(context.application.chat_data)
        pprint(context.bot_data)

        if update.message:
            for KEY in CHAT_DATA_KEYS_DEFAULTS:
                if KEY not in context.chat_data or context.chat_data[KEY] is None:
                    context.chat_data[KEY] = CHAT_DATA_KEYS_DEFAULTS[KEY].__call__()

        user_data: UserData = context.chat_data[USER_DATA_KEY]

        print('Chat id:', update.effective_chat.id)
        # answers_df_fname = answers_df_backup_fname(update.effective_chat.id)

        if user_data.answers_df is None:
            print(f'DB: Restoring answers_df')
            user_data.reload_answers_df_from_db()

        if not user_data.questions_names:
            user_data.reload_qnames()

        try:
            await func(update, context, *args, **kwargs)
        except MyException as e:
            await wrapped_send_text(update.message.reply_text, text=str(e), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await wrapped_send_text(update.message.reply_text, text=traceback.format_exc())

    return wrapper


def get_nth_delta_day(n: int = 0) -> datetime.date:
    date = datetime.date.today() + datetime.timedelta(days=n)
    return date


STOP_ASKING = 'Stop asking'
SKIP_QUEST = 'Skip question'


def df_to_markdown(df: pd.DataFrame, transpose=False):
    if transpose:
        df = df.T

    # Replace None with np.nan for consistency
    df = df.fillna(value=np.nan)

    text = df.to_markdown(
        tablefmt='rounded_grid',
        numalign='left',
        stralign='left',
    )
    text = text.replace(' nan ', ' --- ')

    text = text.replace('00:00:00', '0       ')
    text = text.replace(':00:00', ':0c0   ')
    text = text.replace(':00', '   ')
    text = text.replace(':0c0', ':00')

    # 00:00:00 -> 0
    # 06:00:00 -> 06:00
    # 12:34:00 -> 12:34

    return text


def create_default_answers_df() -> pd.DataFrame:
    # q_names = list(map(lambda x: x.name, questions_objects))
    # q_texts = list(map(lambda x: x.text, questions_objects))

    questions_names = db.get_ordered_questions_names()

    init_answers_df = pd.DataFrame(
        index=questions_names
    )

    # noinspection PyTypeChecker
    # init_answers_df.insert(0, 'fulltext', q_texts)

    # f.write(init_answers_df.to_csv())
    # init_answers_df.to_pickle(BACKUP_ANSWERS_FNAME)
    return init_answers_df


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
        indent_point = (indent, indent - 4)  # ...

        bg_color = (200, 200, 200)
        fg_color = (0, 0, 0)

        from PIL import (
            Image,
            ImageDraw,
            ImageFont
        )

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
        else:
            reply_markup = None

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
