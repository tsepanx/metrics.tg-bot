import datetime
import logging
import re

import pandas as pd
import telegram
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import (
    ParseMode,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.conversations.utils_ask import (
    SKIP_QUEST,
    STOP_ASKING,
    on_end_asking_event,
    on_end_asking_questions,
    send_ask_event_text,
    send_ask_event_time,
    send_ask_question,
)
from src.other_commands import (
    stats_command,
)
from src.tables.event import (
    EventDB,
)
from src.tables.question import (
    QuestionDB,
)
from src.user_data import (
    ASKConversationStorage,
    ASKEventConvStorage,
    ASKQuestionsConvStorage,
    UserData,
)
from src.utils import (
    MyException,
    get_nth_delta_day,
)
from src.utils_tg import (
    USER_DATA_KEY,
    get_questions_select_keyboard,
    handler_decorator,
    match_question_choice_callback_data,
    wrapped_send_text,
)

logger = logging.getLogger(__name__)

(
    ASK_CHOOSE_DAY,
    ASK_CHOOSE_ENTITY_TYPE,
    ASK_CHOOSE_QUESTION_OPTION,
    ASK_CHOOSE_EVENT_NAME,
    ASK_QUESTION_ANSWER,
    ASK_EVENT_TIME,
    ASK_EVENT_PREFIX,
    ASK_EVENT_TEXT,
    END_ASKING_QUESTIONS,
    END_ASKING_EVENT,
) = range(10)


# pylint: disable=too-many-statements
@handler_decorator
async def on_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]
    ud.conv_storage = ASKConversationStorage()

    reply_keyboard = [["-5", "-4", "-3", "-2", "-1", "+1"], ["Today"]]
    text = "Select day"

    await update.message.reply_text(
        text=text,
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ASK_CHOOSE_DAY


# ==== DAY ====


@handler_decorator
async def on_chosen_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    text = update.message.text  # 2023-01-01 / Today / +1

    try:
        if re.compile(isoformat_regex).match(text):
            day = datetime.date.fromisoformat(text)
        elif text == "Today":
            day = datetime.date.today()
        else:  # +1 / -1 / ...
            day = get_nth_delta_day(int(text))
    except Exception:
        await update.message.reply_text("Wrong message, try again")
        return ASK_CHOOSE_DAY

    ud.conv_storage.day = day

    reply_keyboard = [["Question", "Event"]]
    text = "Select entity type"

    await update.message.reply_text(
        text=text,
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ASK_CHOOSE_ENTITY_TYPE


# ==== ENTITY TYPE ====


@handler_decorator
async def on_chosen_type_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    # Down-casting
    ud.conv_storage = ASKQuestionsConvStorage(**ud.conv_storage.__dict__)

    text = update.message.text
    assert text == "Question"

    reply_markup = get_questions_select_keyboard(ud.db_cache.questions)

    await update.message.reply_text(
        text="Choose question names OR other option",
        reply_markup=reply_markup,
    )

    return ASK_CHOOSE_QUESTION_OPTION


@handler_decorator
async def on_chosen_type_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    # Down-casting
    ud.conv_storage = ASKEventConvStorage(**ud.conv_storage.__dict__)

    assert update.message.text == "Event"

    # events_names: list[str] = ud.db_cache.events_names()
    events = ud.db_cache.events

    buttons_column = []
    for i, event in enumerate(events):
        text = event.name
        buttons_column.append(InlineKeyboardButton(text, callback_data=i))

    reply_markup = InlineKeyboardMarkup.from_column(buttons_column)

    await update.message.reply_text(
        text="Choose event name",
        reply_markup=reply_markup,
    )

    return ASK_CHOOSE_EVENT_NAME


# ==== ENTITY NAME(S) ====


@handler_decorator
async def on_chosen_question_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]
    assert isinstance(ud.conv_storage, ASKQuestionsConvStorage)

    send_text_func = update.effective_chat.send_message

    # qnames = ud.db_cache.questions_names()
    answers_df: pd.DataFrame = ud.db_cache.questions_answers_df()

    await update.callback_query.answer()
    query: str = update.callback_query.data

    if query == "end_choosing":
        if len(ud.conv_storage.include_indices) == 0:
            raise MyException("You haven't selected any name")

        ud.conv_storage.cur_answers = [None for _ in range(len(ud.conv_storage.include_indices))]
        include_names = [ud.db_cache.questions[i].name for i in ud.conv_storage.include_indices]

        await wrapped_send_text(
            send_text_func,
            text="Questions list:\n`{}`\n".format("\n".join(include_names)),
            parse_mode=ParseMode.MARKDOWN,
        )

        first_question = ud.conv_storage.current_question(ud.db_cache.questions)

        # fmt: off
        await send_ask_question(
            first_question,
            send_text_func,
            existing_answer=ud.cur_question_existing_answer()
        )
        # fmt: on

        return ASK_QUESTION_ANSWER

    all_indices = list(range(len(ud.db_cache.questions)))
    old_len = len(ud.conv_storage.include_indices)

    if match_question_choice_callback_data(query):  # f.e. "10 add"
        include_indices_set: set = set(ud.conv_storage.include_indices)

        query_index, query_action = query.split()
        query_index = int(query_index)

        if query_action == "add":
            include_indices_set.add(query_index)
        elif query_action == "remove":
            include_indices_set.discard(query_index)
        else:
            raise Exception

        include_indices = sorted(include_indices_set)
    elif query == "all":
        include_indices = all_indices
    elif query == "unanswered":
        if ud.conv_storage.day not in answers_df.columns:
            include_indices = all_indices
        else:
            # Filter to get indices of only null values
            include_indices = list(
                answers_df[ud.conv_storage.day]
                .isnull()
                .reset_index()
                .drop("index", axis=1)
                .apply(lambda x: None if bool(x[0]) is False else 1, axis=1)
                .dropna()
                .index
            )

            if len(include_indices) == 0:
                include_indices = all_indices
    elif query == "clear":
        include_indices = []
    else:
        raise Exception

    is_changed = old_len != len(include_indices)
    if is_changed:
        new_ikm = get_questions_select_keyboard(
            questions=ud.db_cache.questions, include_indices=include_indices
        )
        try:
            await update.callback_query.message.edit_reply_markup(new_ikm)
        except telegram.error.BadRequest as exc:
            logger.error(f"TG SEND ERROR: {exc}")

    ud.conv_storage.include_indices = include_indices
    return ASK_CHOOSE_QUESTION_OPTION


@handler_decorator
async def on_chosen_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    assert isinstance(ud.conv_storage, ASKEventConvStorage)

    await update.callback_query.answer()
    query: str = update.callback_query.data

    send_text_func = update.effective_chat.send_message

    if not query.isdigit():
        raise Exception(f"query {query} is not digit-like")

    ud.conv_storage.chosen_event_index = int(query)
    event: EventDB = ud.db_cache.events[ud.conv_storage.chosen_event_index]

    await send_ask_event_time(event, send_text_func)
    return ASK_EVENT_TIME


# === ANSWER VALUE(S) ====


@handler_decorator
async def on_question_answered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    assert update.message is not None
    assert isinstance(ud.conv_storage, ASKQuestionsConvStorage)

    # state = ud.state

    # assert isinstance(state, QuestionsAskingState)
    # assert state.include_questions is not None

    # q: QuestionDB = state.get_current_question()
    q: QuestionDB = ud.conv_storage.current_question(ud.db_cache.questions)

    answer_text = update.message.text

    if answer_text == SKIP_QUEST:
        answer_text = None
    elif answer_text == STOP_ASKING:
        # return END_ASKING_QUESTIONS
        await on_end_asking_questions(ud, update)
        return ConversationHandler.END
    else:
        try:
            if q.answer_apply_func:
                answer_text = q.answer_apply_func(answer_text)
        except Exception as exc:
            raise MyException("Error parsing answer, try again") from exc

    ud.conv_storage.set_current_answer(answer_text)
    ud.conv_storage.cur_i += 1

    if ud.conv_storage.cur_i >= len(ud.conv_storage.include_indices):
        # return END_ASKING_QUESTIONS
        await on_end_asking_questions(ud, update)
        return ConversationHandler.END

    q = ud.conv_storage.current_question(ud.db_cache.questions)

    await send_ask_question(
        q=q,
        send_text_func=update.message.reply_text,
        existing_answer=ud.cur_question_existing_answer(),
    )

    return ASK_QUESTION_ANSWER


@handler_decorator
async def on_event_time_answered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    assert isinstance(ud.conv_storage, ASKEventConvStorage)

    assert update.message is not None
    text = update.message.text

    event: EventDB = ud.db_cache.events[ud.conv_storage.chosen_event_index]

    if text == "Now":
        time = datetime.datetime.now().time().replace(microsecond=0)
    else:
        try:
            time = datetime.time.fromisoformat(text)
        except ValueError:
            await update.message.reply_text(
                text="Wrong time format, try again", reply_markup=update.message.reply_markup
            )
            return ASK_EVENT_TIME

    ud.conv_storage.event_time = time
    # TODO reflect changes of Dataclass by class.values -> then .save(), instead of manually updating DB

    # await send_ask_event_prefix(event, update.message.reply_text)
    # return ASK_EVENT_PREFIX
    await send_ask_event_text(event, update.message.reply_text)
    return ASK_EVENT_TEXT


@handler_decorator
async def on_event_text_answered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    assert isinstance(ud.conv_storage, ASKEventConvStorage)

    assert update.message is not None
    text = update.message.text

    if text != "None":
        ud.conv_storage.event_text = None
    else:
        ud.conv_storage.event_text = text

    await on_end_asking_event(ud, update)
    return ConversationHandler.END


# === CONVERSATIONS LIST ====

isoformat_regex = r"^\d{4}-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$"
day_choice_regex = rf"(^\+|\-)[0-9]+$|(Today)|({isoformat_regex})"

# fmt: off
ask_conv_handler = ConversationHandler(
    name="Name",
    allow_reentry=True,
    persistent=True,
    # per_message=True,
    entry_points=[
        CommandHandler("ask", on_ask)
    ],
    states={
        ASK_CHOOSE_DAY: [MessageHandler(filters.Regex(day_choice_regex), on_chosen_day)],
        ASK_CHOOSE_ENTITY_TYPE: [
            MessageHandler(filters.Regex("Question"), on_chosen_type_question),
            MessageHandler(filters.Regex("Event"), on_chosen_type_event),
        ],
        ASK_CHOOSE_QUESTION_OPTION: [CallbackQueryHandler(on_chosen_question_option)],
        ASK_CHOOSE_EVENT_NAME: [CallbackQueryHandler(on_chosen_event_name)],
        ASK_QUESTION_ANSWER: [MessageHandler(filters.TEXT, on_question_answered)],
        ASK_EVENT_TIME: [MessageHandler(filters.TEXT, on_event_time_answered)],
        # ASK_EVENT_PREFIX: [MessageHandler(filters.TEXT, on_event_prefix_answered)],
        ASK_EVENT_TEXT: [MessageHandler(filters.TEXT, on_event_text_answered)],
    },
    fallbacks=[CommandHandler("stats", stats_command)],
)
# fmt: on
