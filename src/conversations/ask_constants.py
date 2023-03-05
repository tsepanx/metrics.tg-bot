from telegram import (
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.constants import (
    ParseMode,
)

ADD_TIME_TO_QUESTIONS = True

DEFAULT_PARSE_MODE = ParseMode.HTML
DEFAULT_REPLY_KEYBOARD = lambda buttons: ReplyKeyboardMarkup(
    keyboard=buttons,
    one_time_keyboard=True,
    resize_keyboard=True,
)

QUESTION_TEXT_CHOICE_STOP_ASKING = "Stop asking"
QUESTION_TEXT_CHOICE_SKIP_QUEST = "Skip question"

ENTITY_TYPE_QUESTION_STR = "Question"
ENTITY_TYPE_EVENT_STR = "Event"
CHOOSE_ENTITY_TYPE_REPLY_KEYBOARD = [[ENTITY_TYPE_QUESTION_STR, ENTITY_TYPE_EVENT_STR]]
CHOOSE_ENTITY_TYPE_MSG = "Select entity type"

CHOOSE_DAY_MSG = "Select day"

CHOOSE_DAY_OPTION_TODAY = "Today"

ISOFORMAT_REGEX = r"^\d{4}-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$"
DAY_CHOICE_REGEX = rf"(^\+|\-)[0-9]+$|({CHOOSE_DAY_OPTION_TODAY})|({ISOFORMAT_REGEX})"

CHOOSE_DAY_REPLY_KEYBOARD = [["-5", "-4", "-3", "-2", "-1", "+1"], [CHOOSE_DAY_OPTION_TODAY]]

SELECT_QUESTION_NAMES_MSG_TEXT = "Choose question names OR other option"
SELECT_QUESTION_ERROR_MSG = "You haven't selected any name"

SELECT_EVENT_NAME_MSG = "Choose event name"


class SelectQuestionCallback:
    END_CHOOSING = "end_choosing"
    ALL = "all"
    UNANSWERED = "unanswered"
    CLEAR = "clear"

    ACTION_ADD = "add"
    ACTION_REMOVE = "remove"


class SelectQuestionButtons:
    ALL = InlineKeyboardButton("All", callback_data=SelectQuestionCallback.ALL)
    UNANSWERED = InlineKeyboardButton("Unanswered", callback_data=SelectQuestionCallback.UNANSWERED)
    CLEAR = InlineKeyboardButton("Clear", callback_data=SelectQuestionCallback.CLEAR)

    OK_PARAMETRIZED = lambda ids: InlineKeyboardButton(  # noqa: E731
        f"{'✅ ' if ids else ''}OK", callback_data=SelectQuestionCallback.END_CHOOSING
    )


class SelectEventCallback:
    GO_UP = "go_up"
    END = "END"


class SelectEventButtons:
    GO_UP = InlineKeyboardButton("⬆️ Up ../", callback_data=SelectEventCallback.GO_UP)


class EventType:
    DURABLE = "Durable"
    SINGLE = "Single"


SINGLE_EVENT_REPR = lambda text: f"📍 {text}"  # noqa: E731
DURABLE_EVENT_REPR = lambda text: f"🕓 {text}"  # noqa: E731
DIR_EVENT_REPR = lambda cnt, text: f"🗂 [{cnt}] {text}"  # noqa: E731

ERROR_PARSING_ANSWER = "Error parsing answer, try again"

EVENT_TIME_ASK_MSG = "Now send event time in `isoformat` (01:02:03)"
EVENT_TIME_CHOICE_NOW = "Now"
EVENT_TIME_WRONG_FORMAT = "Wrong time format, try again"

EVENT_TEXT_ASK_MSG = "Also send `text` (optionally)"
EVENT_TEXT_CHOICE_NONE = "None"
