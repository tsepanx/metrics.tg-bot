import functools
import traceback
from dataclasses import dataclass, field
from functools import wraps
from pprint import pprint
from typing import Literal, Sequence

import pandas
import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes

from questions import Question

MAX_MSG_LEN = 7000


@dataclass
class State:
    current_state: Literal['ask'] | None
    include_ids: list[int] = field(default_factory=list)
    cur_id_ind: int | None = None
    cur_answers: list[str] = field(default_factory=list)

    def reset(self):
        self.current_state = None
        self.include_ids = list()
        self.cur_answers = list()
        self.cur_id_ind = 0

    def get_current_question(self, quests: list[Question]):
        try:
            q_id = self.include_ids[self.cur_id_ind]

            return quests[q_id]
            # return list(filter(lambda x: x.number == q_id, quests))[0]
        except IndexError:
            to_raise = MyException(f'No such question with given index: {self.cur_id_ind}')
            self.cur_id_ind += 1

            raise to_raise


CHAT_DATA_KEYS_DEFAULTS = {
    'state': State(None),
    'cur_answers': list()
}


def questions_to_str(
        qs: list[Question],
        # exclude_null=False,
        # default_val='Unknown Quest'
) -> list[str]:
    # if exclude_null:
    #     return list(map(str, qs))

    str_list = ['{} {}'.format(i, str(qs[i])) for i in range(len(qs))]

    # for q in qs:
    #     str_list[q.number] = q.__str__()

    # str_list = list(map(str, qs))
    return str_list


def merge_to_existing_column(old_col: pd.Series, new_col: pd.Series) -> pd.Series:
    # res_col = pd.DataFrame(
    #     new_col,
    #     # index=df.index[:len(state.cur_answers)],
    #     index=index_str,
    #     columns=[col_index]
    # )

    index = old_col.index.union(new_col.index)
    res_col = pd.Series(index=index)

    for i_str in index:
        old_val = old_col.get(i_str, None)
        new_val = new_col.get(i_str, None)

        res_val = old_val if pd.isnull(new_val) else new_val
        res_col[i_str] = res_val

        # res_col.iloc[:, 0][i_str] = res_val

    return res_col


def fill_index(df: pd.DataFrame, new_index: list[str]):
    raise DeprecationWarning('In favor of pd.reindex')
    # res_df = df
    #
    # for row_name in new_index:
    #     if res_df.T.get(row_name) is None:
    #         res_df = res_df.T.assign(**{
    #             row_name: pd.Series()
    #         }).T
    #
    # return res_df


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


class MyException(Exception):
    pass


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
                    context.chat_data[KEY] = CHAT_DATA_KEYS_DEFAULTS[KEY]

        try:
            await func(update, context, *args, **kwargs)
        except MyException as e:
            await wrapped_send_text(update.message.reply_text, text=str(e))
        except Exception:
            await wrapped_send_text(update.message.reply_text, text=traceback.format_exc())

    return wrapper
