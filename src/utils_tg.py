import re
import traceback
from functools import wraps
from typing import Tuple

from telegram import Update
from telegram.constants import (
    ParseMode,
)
from telegram.ext import (
    ContextTypes,
)

from src.user_data import UserData
from src.utils import MyException

USER_DATA_KEY = "user_data"
CHAT_DATA_KEYS_DEFAULTS = {USER_DATA_KEY: UserData}
MAX_MSG_LEN = 4096


async def wrapped_send_text(send_message_func, text: str, *args, **kwargs):
    def get_divided_long_message(long_text, max_size) -> Tuple[str, str]:
        """
        Cuts long message text with \n separator

        @param long_text: str - given text
        @param max_size: int - single text message max size

        return: text part from start, and the rest of text
        """
        subtext = long_text[:max_size]
        border = subtext.rfind("\n")

        subtext = subtext[:border]
        long_text = long_text[border:]

        return subtext, long_text

    if len(text) > MAX_MSG_LEN:
        l_part, r_part = get_divided_long_message(text, MAX_MSG_LEN)

        await send_message_func(*args, text=l_part, **kwargs)
        await wrapped_send_text(send_message_func, r_part, *args, **kwargs)
    else:
        await send_message_func(*args, text=text, **kwargs)


def match_question_choice_callback_data(query: str) -> bool:
    return bool(re.compile("^[0-9]+ (add|remove)$").match(query))


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

        try:
            return await func(update, context, *args, **kwargs)
        except MyException as e:
            await wrapped_send_text(
                update.effective_chat.send_message,
                text=str(e),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            if ud.DEBUG_ERRORS_OUTPUT:
                await wrapped_send_text(
                    update.effective_chat.send_message, text=traceback.format_exc()
                )

    return wrapper
