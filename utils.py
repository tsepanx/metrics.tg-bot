import functools
import traceback
from dataclasses import dataclass, field
from functools import wraps
from pprint import pprint
from typing import Literal, Callable

from telegram import Update
from telegram.ext import ContextTypes


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

    def get_current_question(self, quests: list):
        try:
            q_id = self.include_ids[self.cur_id_ind]

            return list(filter(lambda x: x.num_id == q_id, quests))[0]
        except IndexError:
            to_raise = MyException(f'No such question with given index: {self.cur_id_ind}')
            self.cur_id_ind += 1

            raise to_raise


@dataclass
class Question:
    num_id: int
    text: str
    # Ел ли ты сегодня овсянку?
    # Сколько часов ты спал?
    inline_keyboard_answers: list[str | int]

    answer_mapping_func: Callable

    # Да, Нет -> 1 if x == 'Да' else 0
    # 0, 1, 2 ... 8, 8.5, 9... -> float(x)
    # 0, 1, 2 -> x * 5
    # 1, ... 10 -> (x - 1) / 9

    def __str__(self):
        return f'[{self.num_id}] {self.text}'


def questions_to_str(qs: list[Question], exclude_null=False, default_val='Unknown Quest') -> list[str]:
    if exclude_null:
        return list(map(str, qs))

    max_id = max(qs, key=lambda x: x.num_id).num_id

    str_list = [f'[{i}] {default_val}' for i in range(max_id + 1)]

    for q in qs:
        str_list[q.num_id] = q.__str__()

    return str_list


MAX_MSG_LEN = 7000

CHAT_DATA_KEYS_DEFAULTS = {
    'state': State(None),
    'cur_answers': list()
}


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
