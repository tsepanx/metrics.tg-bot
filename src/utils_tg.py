import re
import traceback
from functools import wraps
from typing import Tuple

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.tables.question import QuestionDB
from src.user_data import UserData
from src.utils import MyException


def match_question_choice_callback_data(query: str) -> bool:
    return bool(
        re.compile("^[0-9]+ (add|remove)$").match(query)
    )


def get_questions_select_keyboard(
        questions: list[QuestionDB],
        include_indices_set: set[int] = None,
        emoji_str: str = "☑️",
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("All", callback_data="all"),
            InlineKeyboardButton("Unanswered", callback_data="unanswered"),
            InlineKeyboardButton("OK", callback_data="end_choosing"),
        ],
    ]

    for i, q in enumerate(questions):
        if include_indices_set is not None and i in include_indices_set:
            butt_text = f"{emoji_str} {q.name}"
            butt_data = f"{i} remove"
        else:
            butt_text = f"{q.name}"
            butt_data = f"{i} add"

        new_button = InlineKeyboardButton(text=butt_text, callback_data=butt_data)
        keyboard.append([new_button])

    return InlineKeyboardMarkup(keyboard)


USER_DATA_KEY = "user_data"
CHAT_DATA_KEYS_DEFAULTS = {
    # 'state': State(None),
    USER_DATA_KEY: UserData
}
RELOAD_DB_CACHE = False
MAX_MSG_LEN = 4096


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
        global RELOAD_DB_CACHE

        assert context.chat_data is not None

        # pylint: disable=consider-using-dict-items
        for KEY in CHAT_DATA_KEYS_DEFAULTS:
            if KEY not in context.chat_data or context.chat_data[KEY] is None:
                context.chat_data[KEY] = CHAT_DATA_KEYS_DEFAULTS[KEY]()

        ud: UserData = context.chat_data[USER_DATA_KEY]

        if RELOAD_DB_CACHE:
            print("DB Cache: RELOADING FROM DB")
            ud.db_cache.reload_all()
            RELOAD_DB_CACHE = False

        try:
            result = await func(update, context, *args, **kwargs)
            return result
        except MyException as e:
            await wrapped_send_text(update.effective_chat.send_message, text=str(e), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await wrapped_send_text(update.effective_chat.send_message, text=traceback.format_exc())

    return wrapper
