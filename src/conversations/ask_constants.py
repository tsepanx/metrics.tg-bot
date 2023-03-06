from telegram import (
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.constants import (
    ParseMode,
)

ADD_TIME_TO_QUESTIONS = True

DEFAULT_PARSE_MODE = ParseMode.HTML
DEFAULT_REPLY_KEYBOARD = lambda buttons: ReplyKeyboardMarkup(  # noqa: E731
    keyboard=buttons,
    one_time_keyboard=True,
    resize_keyboard=True,
)

# === Entity type ===

ENTITY_TYPE_CHOICE_QUESTION = "Question"
ENTITY_TYPE_CHOICE_EVENT = "Event"
ENTITY_TYPE_MSG = "Select entity type"

ENTITY_TYPE_KEYBOARD = [[ENTITY_TYPE_CHOICE_QUESTION, ENTITY_TYPE_CHOICE_EVENT]]
# REGEX_ENTITY_TYPE_KEYBOARD = any_of_buttons_regex(ENTITY_TYPE_KEYBOARD)

# === Day ===

DAY_MSG = "Select day"
DAY_CHOICE_TODAY = "Today"


QUESTION_DAY_KEYBOARD = [["-5", "-4", "-3", "-2", "-1", "+1"], [DAY_CHOICE_TODAY]]

ISOFORMAT_REGEX = r"^\d{4}-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$"
REGEX_QUESTION_DAY_KEYBOARD = rf"(^\+|\-)[0-9]+$|({DAY_CHOICE_TODAY})|({ISOFORMAT_REGEX})"
# REGEX_QUESTION_DAY_KEYBOARD = any_of_buttons_regex(QUESTION_DAY_KEYBOARD)


# === Question names ===


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


QUESTION_NAMES_MSG = "Choose question names OR other option"
QUESTION_ERROR_MSG = "You haven't selected any name"

EVENT_NAME_MSG = "Choose event name"


# === Event names ===


class EventType:
    DURABLE = "Durable"
    SINGLE = "Single"


class SelectEventCallback:
    GO_UP = "go_up"
    END = "END"


class SelectEventButtons:
    GO_UP = InlineKeyboardButton("⬆️ Up ../", callback_data=SelectEventCallback.GO_UP)


SINGLE_EVENT_REPR = lambda text: f"📍 {text}"  # noqa: E731
DURABLE_EVENT_REPR = lambda text: f"🕓 {text}"  # noqa: E731
DIR_EVENT_REPR = lambda cnt, text: f"🗂 [{cnt}] {text}"  # noqa: E731

# === Question answer ===

ERROR_PARSING_ANSWER = "Error parsing answer, try again"

QUESTION_TEXT_CHOICE_STOP_ASKING = "Stop asking"
QUESTION_TEXT_CHOICE_SKIP_QUEST = "Skip question"

# === Event time answer ===

EVENT_TIME_ASK_MSG = "Now send event time in `isoformat` (01:02:03)"
EVENT_TIME_CHOICE_NOW = "Now"
EVENT_TIME_CHOICES_DELTA = ["-10m", "-5m", "-1m", "+1m", "+5m", "+10m"]
EVENT_TIME_WRONG_FORMAT = "Wrong time format, try again"

EVENT_TIME_KEYBOARD = [EVENT_TIME_CHOICES_DELTA, [EVENT_TIME_CHOICE_NOW]]
# REGEX_EVENT_TIME_KEYBOARD = any_of_buttons_regex(EVENT_TIME_KEYBOARD)
REGEX_EVENT_TIME_KEYBOARD = rf"^([-+]?[0-9]+[smh]|({EVENT_TIME_CHOICE_NOW}))$"

# === Event text answer ===

EVENT_TEXT_ASK_MSG = "Also send `text` (optionally)"
EVENT_TEXT_CHOICE_NONE = "None"
EVENT_TEXT_KEYBOARD = [[EVENT_TEXT_CHOICE_NONE]]
# REGEX_EVENT_TEXT_KEYBOARD = any_of_buttons_regex(EVENT_TEXT_KEYBOARD)
