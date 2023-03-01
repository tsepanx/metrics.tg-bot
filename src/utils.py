import datetime
import functools
import traceback
from functools import (
    wraps,
)
from io import (
    BytesIO,
)
from pprint import (
    pprint,
)
from typing import (
    Any,
    Sequence,
    Tuple,
)

import numpy as np
import pandas as pd
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
)
from telegram import (
    Update,
)
from telegram.constants import (
    ParseMode,
)
from telegram.ext import (
    ContextTypes,
)

from src import (
    orm,
)


class MyException(Exception):
    pass


def ask_format_example():
    n = 18
    return "\n".join(
        [
            "Examples:",
            f"`{'/ask':{n}}` For today, unanswered questions",
            f"`{'/ask -d=2023-01-01':{n}}` Specific day (isoformat)",
            f"`{'/ask -d=-1':{n}}` Yesterday",
            f"`{'/ask -q=1,2,3':{n}}` Specify questions to ask",
            f"`{'/ask -q=1,2,3 -d=2023-01-01':{n}}` Multiple args",
        ]
    )


def answers_df_backup_fname(chat_id: int) -> str:
    return f"answers_df_backups/{chat_id}.csv"


ASK_WRONG_FORMAT = MyException("`=== /ask: wrong format ===`\n" + ask_format_example())

STOP_ASKING = "Stop asking"
SKIP_QUEST = "Skip question"
MAX_MSG_LEN = 7000


class AskingState:
    include_questions: list[orm.QuestionDB] | None
    asking_day: str

    cur_id_ind: int
    cur_answers: list[str | None]

    def __init__(self, include_qnames: list, asking_day: str):
        self.asking_day = asking_day

        self.cur_id_ind = 0
        self.cur_answers = [None for _ in range(len(include_qnames))]
        self.include_questions = orm.get_questions_with_type_fk(include_qnames)

    def get_current_question(self) -> orm.QuestionDB:
        if not self.include_questions:
            raise Exception

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

    def reload_answers_df_from_db(self, cols: Sequence[str] | None = None):
        if cols:
            assert self.answers_df is not None

            new_cols = orm.build_answers_df(days_range=cols)

            assign_dict = {cols[i]: new_cols.iloc[:, 0] for i in range(len(cols))}
            self.answers_df = self.answers_df.assign(**assign_dict)
            self.answers_df = sort_answers_df_cols(self.answers_df)
        else:
            self.answers_df = orm.build_answers_df()

    def reload_qnames(self):
        self.questions_names = orm.get_ordered_questions_names()


USER_DATA_KEY = "data"

CHAT_DATA_KEYS_DEFAULTS = {
    # 'state': State(None),
    USER_DATA_KEY: UserData
}


def to_list(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> list:
        res = list(func(*args, **kwargs))
        return res

    return wrapper


def sort_answers_df_cols(df: pd.DataFrame) -> pd.DataFrame:
    columns_order = sorted(df.columns, key=lambda x: f"_{x}" if not isinstance(x, datetime.date) else x.isoformat())
    df = df.reindex(columns_order, axis=1)
    return df


def add_questions_sequence_num_as_col(df: pd.DataFrame, questions: list[orm.QuestionDB]):
    """
    Generate
    Prettify table look by adding questions ids to index

    Assumes given @df has "questions names" as index
    """
    sequential_numbers = []

    for index_i in df.index:
        for i, question in enumerate(questions):
            if question.name == index_i:
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
    df.insert(0, "i", sequential_numbers)

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


def get_divided_long_message(text, max_size) -> Tuple[str, str]:
    """
    Cuts long message text with \n separator

    @param text: str - given text
    @param max_size: int - single text message max size

    return: text part from start, and the rest of text
    """
    subtext = text[:max_size]
    border = subtext.rfind("\n")

    subtext = subtext[:border]
    text = text[border:]

    return subtext, text


async def wrapped_send_text(send_message_func, text: str, *args, **kwargs):
    if len(text) > MAX_MSG_LEN:
        lpart, rpart = get_divided_long_message(text, MAX_MSG_LEN)

        await send_message_func(*args, text=lpart, **kwargs)
        await wrapped_send_text(send_message_func, rpart, *args, **kwargs)
    else:
        await send_message_func(*args, text=text, **kwargs)


def handler_decorator(func):
    """
    Wrapper over each handler
    @param func: handler func
    """

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        pprint(context.application.chat_data)
        pprint(context.bot_data)

        assert context.chat_data is not None

        # pylint: disable=consider-using-dict-items
        for KEY in CHAT_DATA_KEYS_DEFAULTS:
            if KEY not in context.chat_data or context.chat_data[KEY] is None:
                context.chat_data[KEY] = CHAT_DATA_KEYS_DEFAULTS[KEY]()

        user_data: UserData = context.chat_data[USER_DATA_KEY]

        if user_data.answers_df is None:
            print("DB: Restoring answers_df")
            user_data.reload_answers_df_from_db()

        if not user_data.questions_names:
            user_data.reload_qnames()

        try:
            await func(update, context, *args, **kwargs)
        except MyException as e:
            assert update.message is not None
            await wrapped_send_text(update.message.reply_text, text=str(e), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            assert update.message is not None
            await wrapped_send_text(update.message.reply_text, text=traceback.format_exc())

    return wrapper


def get_nth_delta_day(n: int = 0) -> datetime.date:
    date = datetime.date.today() + datetime.timedelta(days=n)
    return date


def df_to_markdown(df: pd.DataFrame, transpose=False):
    if transpose:
        df = df.T

    # Replace None with np.nan for consistency
    df = df.fillna(value=np.nan)

    text = df.to_markdown(
        tablefmt="rounded_grid",
        numalign="left",
        stralign="left",
    )
    text = text.replace(" nan ", " --- ")

    text = text.replace("00:00:00", "0       ")
    text = text.replace(":00:00", ":0c0   ")
    text = text.replace(":00", "   ")
    text = text.replace(":0c0", ":00")

    # 00:00:00 -> 0
    # 06:00:00 -> 06:00
    # 12:34:00 -> 12:34

    return text


def text_to_png(text: str, bold=True):
    indent = 5
    indent_point = (indent, indent - 4)  # ...

    bg_color = (200, 200, 200)
    fg_color = (0, 0, 0)

    if bold:
        font = ImageFont.truetype("fonts/SourceCodePro-Bold.otf", 16)
    else:
        font = ImageFont.truetype("fonts/SourceCodePro-Regular.otf", 16)

    _, __, x2, y2 = ImageDraw.Draw(Image.new("RGB", (0, 0))).textbbox(indent_point, text, font)

    img = Image.new("RGB", (x2 + indent, y2 + indent), bg_color)
    d = ImageDraw.Draw(img)

    d.text(
        indent_point,
        text,
        font=font,
        fill=fg_color,
    )

    return img


def data_to_bytesio(data: Any, fname: str) -> BytesIO:
    bio = BytesIO()
    bio.name = fname

    if isinstance(data, str):
        bio.write(bytes(data, "utf-8"))
    else:
        bio.write(data)

    bio.seek(0)
    return bio
