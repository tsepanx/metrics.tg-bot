import datetime
import logging
import re
import time

import pandas as pd
import telegram
from telegram import (
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

from src.conversations.ask_constants import (
    CHOOSE_DAY_REPLY_KEYBOARD,
    DAY_CHOICE_REGEX,
    DEFAULT_PARSE_MODE,
    ERROR_PARSING_ANSWER,
    EVENT_TEXT_CHOICE_NONE,
    EVENT_TIME_CHOICE_NOW,
    EVENT_TIME_WRONG_FORMAT,
    ISOFORMAT_REGEX,
    QUESTION_TEXT_CHOICE_SKIP_QUEST,
    QUESTION_TEXT_CHOICE_STOP_ASKING,
    SELECT_EVENT_NAME_MSG,
    SELECT_QUESTION_ERROR_MSG,
    SELECT_QUESTION_NAMES_MSG_TEXT,
    SelectEventCallback,
    SelectQuestionCallback,
)
from src.conversations.ask_utils import (
    ExactPathMatched,
    edit_info_msg,
    get_entity_type_reply_keyboard,
    get_event_info_text,
    get_event_select_keyboard,
    get_questions_list_html,
    get_questions_select_keyboard,
    on_end_asking_event,
    on_end_asking_questions,
    send_ask_event_text,
    send_ask_event_time,
    send_ask_question,
)
from src.other_commands import (
    TgCommands,
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
    get_now,
    get_nth_delta_day,
    get_today,
)
from src.utils_tg import (
    USER_DATA_KEY,
    handler_decorator,
    match_question_choice_callback_data,
)

logger = logging.getLogger(__name__)

(
    ASK_CHOOSE_ENTITY_TYPE,
    ASK_CHOOSE_QUESTION_NAMES,
    ASK_CHOOSE_EVENT_NAME,
    ASK_QUESTION_ANSWER,
    ASK_EVENT_TIME,
    ASK_EVENT_TEXT,
    END_ASKING_QUESTIONS,
    END_ASKING_EVENT,
) = range(8)

# === ENTITY TYPE ===


@handler_decorator
async def choose_entity_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert context.chat_data is not None
    ud: UserData = context.chat_data[USER_DATA_KEY]
    # Reset convStorage
    ud.conv_storage = ASKConversationStorage()

    text = "Select entity type"

    assert update.message is not None

    await update.message.reply_text(
        text=text,
        reply_markup=get_entity_type_reply_keyboard(),
    )

    return ASK_CHOOSE_ENTITY_TYPE


# === DAY ===


# pylint: disable=too-many-statements
@handler_decorator
async def choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    # Down-casting
    ud.conv_storage = ASKQuestionsConvStorage(**ud.conv_storage.__dict__)

    text = update.message.text
    assert text == "Question"

    text = "Select day"

    await update.message.reply_text(
        text=text,
        reply_markup=ReplyKeyboardMarkup(
            CHOOSE_DAY_REPLY_KEYBOARD,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ASK_CHOOSE_QUESTION_NAMES


# === ENTITY NAME(s)


@handler_decorator
async def choose_question_names(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    text = update.message.text

    assert re.compile(DAY_CHOICE_REGEX).match(text)  # 2023-01-01 / Today / +1

    if re.compile(ISOFORMAT_REGEX).match(text):
        day = datetime.date.fromisoformat(text)
    elif text == "Today":
        day = get_today()
    else:  # +1 / -1 / ...
        day = get_nth_delta_day(int(text))

    ud.conv_storage.day = day

    reply_markup = get_questions_select_keyboard(ud.db_cache.questions)

    await update.message.reply_text(
        text=SELECT_QUESTION_NAMES_MSG_TEXT,
        reply_markup=reply_markup,
    )

    # return ASK_CHOOSE_QUESTION_OPTION
    # return ASK_CHOOSE_DAY
    return ASK_CHOOSE_QUESTION_NAMES


@handler_decorator
async def choose_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    # Down-casting
    ud.conv_storage = ASKEventConvStorage(**ud.conv_storage.__dict__)
    ud.conv_storage.event_name_prefix_path = []

    assert update.message.text == "Event"

    events = ud.db_cache.events

    reply_markup = get_event_select_keyboard(events, ud.conv_storage.event_name_prefix_path)

    await update.message.reply_text(
        text=SELECT_EVENT_NAME_MSG,
        reply_markup=reply_markup,
    )

    return ASK_CHOOSE_EVENT_NAME


@handler_decorator
async def on_chosen_question_name_option(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:  # noqa: C901
    ud: UserData = context.chat_data[USER_DATA_KEY]
    assert isinstance(ud.conv_storage, ASKQuestionsConvStorage)

    send_text_func = update.effective_chat.send_message

    # qnames = ud.db_cache.questions_names()
    answers_df: pd.DataFrame = ud.db_cache.questions_answers_df()

    await update.callback_query.answer()
    query: str = update.callback_query.data

    if query == SelectQuestionCallback.END_CHOOSING:
        if len(ud.conv_storage.include_indices) == 0:
            raise MyException(SELECT_QUESTION_ERROR_MSG)

        ud.conv_storage.cur_answers = [None for _ in range(len(ud.conv_storage.include_indices))]
        include_names = [ud.db_cache.questions[i].name for i in ud.conv_storage.include_indices]

        msg_with_keyboard = update.callback_query.message
        # await msg_with_keyboard.edit_reply_markup(None)

        new_text = get_questions_list_html(include_names)
        try:
            await msg_with_keyboard.edit_text(
                text=new_text, parse_mode=ParseMode.MARKDOWN, reply_markup=None
            )
        except telegram.error.BadRequest:
            pass

        time.sleep(0.8)

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

        if query_action == SelectQuestionCallback.ACTION_ADD:
            include_indices_set.add(query_index)
        elif query_action == SelectQuestionCallback.ACTION_REMOVE:
            include_indices_set.discard(query_index)
        else:
            raise Exception

        include_indices = sorted(include_indices_set)
    elif query == SelectQuestionCallback.ALL:
        include_indices = all_indices
    elif query == SelectQuestionCallback.UNANSWERED:
        if answers_df is not None:
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
        else:
            include_indices = all_indices
    elif query == SelectQuestionCallback.CLEAR:
        include_indices = []
    else:
        raise Exception

    is_changed = old_len != len(include_indices)
    if is_changed:
        new_ikm = get_questions_select_keyboard(
            questions=ud.db_cache.questions, selected_indices=include_indices
        )
        try:
            await update.callback_query.message.edit_reply_markup(new_ikm)
        except telegram.error.BadRequest as exc:
            logger.error(f"TG SEND ERROR: {exc}")

    ud.conv_storage.include_indices = include_indices
    return ASK_CHOOSE_QUESTION_NAMES


@handler_decorator
async def on_chosen_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    async def end_state(event_index: int, event: EventDB) -> int:
        ud.conv_storage.chosen_event_index = event_index
        assert isinstance(ud.conv_storage, ASKEventConvStorage)

        msg_with_keyboard = update.callback_query.message
        await msg_with_keyboard.edit_reply_markup(None)

        ud.conv_storage.info_msg = await update.effective_user.send_message(
            text=get_event_info_text(event, None, None), parse_mode=DEFAULT_PARSE_MODE
        )

        await send_ask_event_time(update.effective_user.send_message)

        return ASK_EVENT_TIME

    ud: UserData = context.chat_data[USER_DATA_KEY]

    assert isinstance(ud.conv_storage, ASKEventConvStorage)

    await update.callback_query.answer()
    query: str = update.callback_query.data

    cur_path = ud.conv_storage.event_name_prefix_path

    if query == SelectEventCallback.GO_UP:
        if cur_path:
            cur_path.pop(-1)
    elif query == SelectEventCallback.END:
        cur_path: list[str]
        event_name = "/".join(cur_path) + "/"

        found_e_index = None
        found_event: EventDB | None = None
        for i, e in enumerate(ud.db_cache.events):
            if e.name == event_name:
                found_e_index = i
                found_event = e
                break
        assert found_e_index is not None

        return await end_state(found_e_index, found_event)
    else:
        cur_path.append(query)

    try:
        reply_keyboard = get_event_select_keyboard(ud.db_cache.events, cur_path)
        new_text = f"Cur path: {cur_path}"

        await update.callback_query.message.edit_text(text=new_text, reply_markup=reply_keyboard)
        return ASK_CHOOSE_EVENT_NAME
    except ExactPathMatched as exc:
        found_event = exc.e
        found_e_index = exc.i

        return await end_state(found_e_index, found_event)


# === ANSWER VALUE(S) ====


@handler_decorator
async def on_question_answered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]

    assert update.message is not None
    assert isinstance(ud.conv_storage, ASKQuestionsConvStorage)

    q: QuestionDB = ud.conv_storage.current_question(ud.db_cache.questions)

    answer_text = update.message.text

    if answer_text == QUESTION_TEXT_CHOICE_SKIP_QUEST:
        answer_text = None
    elif answer_text == QUESTION_TEXT_CHOICE_STOP_ASKING:
        await on_end_asking_questions(ud, update)
        return ConversationHandler.END
    else:
        try:
            if q.answer_apply_func:
                answer_text = q.answer_apply_func(answer_text)
        except Exception as exc:
            raise MyException(ERROR_PARSING_ANSWER) from exc

    ud.conv_storage.set_current_answer(answer_text)
    ud.conv_storage.cur_i += 1

    if ud.conv_storage.cur_i >= len(ud.conv_storage.include_indices):
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
    event: EventDB = ud.db_cache.events[ud.conv_storage.chosen_event_index]

    assert update.message is not None
    text = update.message.text

    if text == EVENT_TIME_CHOICE_NOW:
        time_answer = get_now().time().replace(microsecond=0)
    else:
        try:
            time_answer = datetime.time.fromisoformat(text)
        except ValueError:
            await update.message.reply_text(
                text=EVENT_TIME_WRONG_FORMAT, reply_markup=update.message.reply_markup
            )
            return ASK_EVENT_TIME

    ud.conv_storage.event_time = time_answer

    await edit_info_msg(ud, event)

    await send_ask_event_text(event, update.message.reply_text)
    return ASK_EVENT_TEXT


@handler_decorator
async def on_event_text_answered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud: UserData = context.chat_data[USER_DATA_KEY]
    assert isinstance(ud.conv_storage, ASKEventConvStorage)
    event: EventDB = ud.db_cache.events[ud.conv_storage.chosen_event_index]

    assert update.message is not None
    text = update.message.text

    if text == EVENT_TEXT_CHOICE_NONE:
        ud.conv_storage.event_text = ""
    else:
        ud.conv_storage.event_text = text

    await edit_info_msg(ud, event)

    await on_end_asking_event(ud, update)
    return ConversationHandler.END


# === CONVERSATIONS LIST ====

# fmt: off
ask_conv_handler = ConversationHandler(
    name="Ask ConvHandler",
    allow_reentry=True,
    persistent=True,
    entry_points=[
        CommandHandler("ask", choose_entity_type)
    ],
    states={
        ASK_CHOOSE_ENTITY_TYPE: [
            MessageHandler(filters.Regex("Question"), choose_day),
            MessageHandler(filters.Regex("Event"), choose_event_name),
        ],
        ASK_CHOOSE_QUESTION_NAMES: [
            MessageHandler(filters.Regex(DAY_CHOICE_REGEX) & (~filters.COMMAND), choose_question_names),
            CallbackQueryHandler(on_chosen_question_name_option),
        ],
        ASK_CHOOSE_EVENT_NAME: [CallbackQueryHandler(on_chosen_event_name)],
        ASK_QUESTION_ANSWER: [MessageHandler(filters.TEXT & (~filters.COMMAND), on_question_answered)],
        ASK_EVENT_TIME: [MessageHandler(filters.TEXT & (~filters.COMMAND), on_event_time_answered)],
        ASK_EVENT_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), on_event_text_answered)],
    },
    fallbacks=[
        TgCommands.CANCEL.value.handler,
        TgCommands.RELOAD.value.handler,
    ],
)
# fmt: on
