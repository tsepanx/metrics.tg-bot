import datetime
import functools
import os.path
import traceback
from functools import wraps
from pprint import pprint

import pandas as pd
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from questions import Question, questions_objects


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


# @dataclass
class AskingState:
    include_ids: list[int]
    asking_day: str

    cur_id_ind: int
    cur_answers: list[str | None]

    def __init__(self, include_ids: list, asking_day: str):
        self.include_ids = include_ids
        self.asking_day = asking_day

        self.cur_id_ind = 0
        # self.cur_answers = list()
        self.cur_answers = [None for _ in range(len(include_ids))]

    def get_current_question(self, quests: list[Question]):
        try:
            q_id = self.include_ids[self.cur_id_ind]

            return quests[q_id]
            # return list(filter(lambda x: x.number == q_id, quests))[0]
        except IndexError:
            to_raise = MyException(f'No such question with given index: {self.cur_id_ind}')
            self.cur_id_ind += 1

            raise to_raise


# @dataclass
class UserData:
    state: AskingState | None
    answers_df: pd.DataFrame | None

    def __init__(self):
        self.state = None  # AskingState(None)
        self.answers_df = None
        # self.answers_df = create_default_answers_df()


USER_DATA_KEY = 'data'

CHAT_DATA_KEYS_DEFAULTS = {
    # 'state': State(None),
    USER_DATA_KEY: lambda: UserData()
}


def add_question_indices_to_df_index(df: pd.DataFrame, questions_objects: list[Question]):
    """
    Prettify table look by adding questions ids to index
    """
    indices = list()

    for ind_str in df.index:
        for i in range(len(questions_objects)):
            if questions_objects[i].name == ind_str:
                # s = str(i)
                indices.append(i)
                break

    # Setting new index column
    # df = df.reset_index()
    # df = df.drop('index', axis=1)

    # new_index_name = 'i  | name'

    # df.insert(0, new_index_name, indices)
    # df = df.set_index(new_index_name)

    # noinspection PyTypeChecker
    df.insert(0, 'i', indices)

    return df


def questions_to_str(
        qs: list[Question],
) -> list[str]:
    str_list = ['{:2} {}'.format(i, str(qs[i])) for i in range(len(qs))]

    return str_list


def merge_to_existing_column(old_col: pd.Series, new_col: pd.Series) -> pd.Series:
    index = old_col.index.union(new_col.index)
    res_col = pd.Series(index=index)

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

        if user_data.answers_df is None:
            fname = answers_df_backup_fname(update.effective_chat.id)

            if os.path.exists(fname):
                print(f'Restoring answers_df from file: {fname}')
                user_data.answers_df = pd.read_csv(fname, index_col=0)
            else:
                print(f'Creating default answers_df for user: {update.effective_chat.id}')
                user_data.answers_df = create_default_answers_df()
        else:
            print('answers_df is stored in Persistence data')

        print('answers_df shape:', user_data.answers_df.shape)
        print('answers_df cols:', list(user_data.answers_df.columns))

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

    # return str(date)


STOP_ASKING = 'Stop asking'
SKIP_QUEST = 'Skip question'


def df_to_markdown(df: pd.DataFrame, transpose=False):
    if transpose:
        df = df.T

    text = df.to_markdown(
        tablefmt='rounded_grid',
        numalign='left',
        stralign='left',
    )
    text = text.replace(' nan ', ' --- ')
    text = text.replace(':00', '   ')
    return text


# def write_df_to_csv(fname: str, df: pd.DataFrame):
#     with open(fname, 'w') as file:
#         df_csv = df.to_csv()
#         file.write(df_csv)


def create_default_answers_df() -> pd.DataFrame:
    q_names = list(map(lambda x: x.name, questions_objects))
    q_texts = list(map(lambda x: x.text, questions_objects))

    init_answers_df = pd.DataFrame(
        index=q_names
    )

    # noinspection PyTypeChecker
    init_answers_df.insert(0, 'fulltext', q_texts)

    # f.write(init_answers_df.to_csv())
    # init_answers_df.to_pickle(BACKUP_ANSWERS_FNAME)
    return init_answers_df
