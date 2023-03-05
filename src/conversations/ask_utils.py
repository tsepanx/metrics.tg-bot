import collections
import copy
import datetime
from io import BytesIO
from typing import Callable

import pandas as pd
import telegram
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import (
    ParseMode,
)

from src.conversations.ask_constants import (
    ADD_TIME_TO_QUESTIONS,
    CHOOSE_ENTITY_TYPE_REPLY_KEYBOARD,
    DEFAULT_PARSE_MODE,
    DEFAULT_REPLY_KEYBOARD,
    DIR_EVENT_REPR,
    DURABLE_EVENT_REPR,
    EVENT_TEXT_ASK_MSG,
    EVENT_TIME_ASK_MSG,
    EVENT_TIME_CHOICE_NOW,
    QUESTION_TEXT_CHOICE_SKIP_QUEST,
    QUESTION_TEXT_CHOICE_STOP_ASKING,
    SINGLE_EVENT_REPR,
    EventType,
    SelectEventButtons,
    SelectEventCallback,
    SelectQuestionButtons,
    SelectQuestionCallback,
)
from src.orm.base import (
    ColumnDC,
    ValueType,
    _insert_row,
    update_or_insert_row,
)
from src.tables.answer import (
    AnswerType,
)
from src.tables.event import (
    EventDB,
)
from src.tables.question import (
    QuestionDB,
)
from src.user_data import (
    ASKEventConvStorage,
    ASKQuestionsConvStorage,
    UserData,
)
from src.utils import (
    data_to_bytesio,
    get_now_time,
    get_today,
    text_to_png,
)
from src.utils_pd import (
    df_to_markdown,
)
from src.utils_tg import (
    wrapped_send_text,
)


def get_entity_type_reply_keyboard():
    reply_markup = ReplyKeyboardMarkup(
        CHOOSE_ENTITY_TYPE_REPLY_KEYBOARD,
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    return reply_markup


def get_questions_list_html(include_names: list[str]):
    new_text = "Questions list:\n\n" + "`"
    for name in include_names:
        new_text += f"- {name}\n"

    new_text += "`"


class ExactPathMatched(Exception):
    i: int
    e: EventDB

    def __init__(self, i: int, e: EventDB):
        self.i = i
        self.e = e


def get_event_select_keyboard(events: list[EventDB], cur_path: list[str]):
    def path_is_subpath(subpath: list[str], fullpath: list[str]) -> bool:
        return all(subpath[i] == fullpath[i] for i in range(len(subpath)))

    subpath_events: collections.OrderedDict[str, list[int, EventDB]] = collections.OrderedDict()

    for i, event in enumerate(events):
        e_path: list[str] = event.name_path()

        if e_path == cur_path:
            raise ExactPathMatched(i, event)

        if path_is_subpath(cur_path, e_path):
            subdir = e_path[len(cur_path)]

            subpath_events.setdefault(subdir, [0, event])
            subpath_events[subdir][0] += 1

    buttons_column = []

    if cur_path:
        buttons_column.append(
            SelectEventButtons.GO_UP,
        )

    event: EventDB
    for subdir, (cnt, event) in subpath_events.items():
        if subdir == "":
            text = "/"
            callback_data = SelectEventCallback.END
        else:
            callback_data = subdir
            text = f"{subdir}"
            if cnt > 1:
                text = DIR_EVENT_REPR(cnt, text)

        if cnt == 1:
            if event.type == EventType.DURABLE:
                text = DURABLE_EVENT_REPR(text)
            elif event.type == EventType.SINGLE:
                text = SINGLE_EVENT_REPR(text)

        button = InlineKeyboardButton(text, callback_data=callback_data)
        buttons_column.append(button)

    reply_markup = InlineKeyboardMarkup.from_column(buttons_column)
    return reply_markup


def get_questions_select_keyboard(
    questions: list[QuestionDB],
    selected_indices: list[int] = None,
    emoji_str: str = "☑️",
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            SelectQuestionButtons.ALL,
            SelectQuestionButtons.UNANSWERED,
        ],
        [SelectQuestionButtons.CLEAR, SelectQuestionButtons.OK_PARAMETRIZED(selected_indices)],
    ]

    for i, q in enumerate(questions):
        if selected_indices is not None and i in selected_indices:
            butt_text = f"{emoji_str} {q.name}"
            butt_data = f"{i} {SelectQuestionCallback.ACTION_REMOVE}"
        else:
            butt_text = f"{q.name}"
            butt_data = f"{i} {SelectQuestionCallback.ACTION_ADD}"

        butt_text = f"{butt_text} ❓"

        new_button = InlineKeyboardButton(text=butt_text, callback_data=butt_data)
        keyboard.append([new_button])

    return InlineKeyboardMarkup(keyboard)


async def send_ask_question(q: QuestionDB, send_text_func: Callable, existing_answer: str = None):
    buttons = [
        list(map(str, q.choices_list)),
        [QUESTION_TEXT_CHOICE_SKIP_QUEST, QUESTION_TEXT_CHOICE_STOP_ASKING],
    ]

    reply_markup = telegram.ReplyKeyboardMarkup(
        buttons, one_time_keyboard=True, resize_keyboard=True
    )

    text = q.html_full(existing_answer)

    await wrapped_send_text(
        send_message_func=send_text_func,
        text=text,
        reply_markup=reply_markup,
        parse_mode=DEFAULT_PARSE_MODE,
    )


def get_event_info_text(
    event: EventDB, answered_time: datetime.time | None = None, answered_text: str | None = None
):
    lines = [
        "=== Event ===",
        f"Name: {event.name}",
        "",
        f"Time: {answered_time}" if answered_time else "",
        f"Text: {answered_text}" if answered_text is not None else "",
    ]

    text = "<code>" + "\n".join(lines) + "</code>"
    return text


async def edit_info_msg(ud: UserData, e: EventDB):
    assert isinstance(ud.conv_storage, ASKEventConvStorage)

    try:
        await ud.conv_storage.info_msg.edit_text(
            text=get_event_info_text(
                event=e,
                answered_time=ud.conv_storage.event_time,
                answered_text=ud.conv_storage.event_text,
            ),
            parse_mode=DEFAULT_PARSE_MODE,
        )
    except telegram.error.BadRequest:
        pass


async def send_ask_event_time(send_text_func: Callable):
    buttons = [[EVENT_TIME_CHOICE_NOW]]

    await wrapped_send_text(
        send_message_func=send_text_func,
        text=EVENT_TIME_ASK_MSG,
        reply_markup=DEFAULT_REPLY_KEYBOARD(buttons),
        parse_mode=ParseMode.MARKDOWN,
    )


async def send_ask_event_text(e: EventDB, send_text_func: Callable):
    buttons = []

    if e.type == "Durable":
        buttons.append(["start", "end"])

    buttons.append(["None"])

    await wrapped_send_text(
        send_message_func=send_text_func,
        text=EVENT_TEXT_ASK_MSG,
        reply_markup=DEFAULT_REPLY_KEYBOARD(buttons),
        parse_mode=ParseMode.MARKDOWN,
    )


def build_transpose_callback_data(answer_type: AnswerType) -> str:
    return f"transpose {answer_type.name}"


async def send_entity_answers_df(
    update: Update, ud: UserData, answers_entity: AnswerType, **kwargs
):
    file_name = f"{answers_entity.name.lower()}s.csv"

    if answers_entity is AnswerType.QUESTION:
        transpose_callback_data = build_transpose_callback_data(answers_entity)
        answers_df = ud.db_cache.questions_answers_df()
    elif answers_entity is AnswerType.EVENT:
        transpose_callback_data = None
        answers_df = ud.db_cache.events_answers_df()
    else:
        raise Exception

    if answers_df is None:
        return await update.message.reply_text(f"No {answers_entity.name} records")
    else:
        return await send_dataframe(
            update=update,
            df=answers_df,
            transpose_button_callback_data=transpose_callback_data,
            file_name=file_name,
            **kwargs,
        )


async def send_dataframe(
    update: Update,
    df: pd.DataFrame,
    send_csv=False,
    send_img=True,
    send_text=False,
    transpose_table=False,
    transpose_button_callback_data: str = None,
    with_question_indices=True,
    file_name: str = "dataframe.csv",
):
    # Fix dirty function applying changes directly to passed DataFrame
    df = df.copy()

    # [0, 1, 2, 3, ...]
    i_column = list(range(len(df.index)))
    # noinspection PyTypeChecker
    df.insert(0, "i", i_column)

    # if sort_by_quest_indices:
    #     answers_df = answers_df.sort_values("i")

    # 'i' column was used just for sorting
    if not with_question_indices:
        df = df.drop("i", axis=1)

    md_text = df_to_markdown(df, transpose=transpose_table)
    csv_text = df.to_csv()

    if not transpose_table:
        assert update.message is not None
        message_object = update.message
    else:
        assert update.callback_query is not None
        assert update.callback_query.message is not None
        message_object = update.callback_query.message

    if send_csv:
        bytes_io = data_to_bytesio(csv_text, file_name)
        await message_object.reply_document(document=bytes_io)

    if send_img:
        img = text_to_png(md_text)

        bio = BytesIO()
        bio.name = "screenshot1.png"

        img.save(bio, "png")
        bio.seek(0)

        bio2 = copy.copy(bio)

        if not transpose_table and transpose_button_callback_data:
            keyboard = [
                [
                    telegram.InlineKeyboardButton(
                        "transposed table IMG",
                        callback_data=transpose_button_callback_data,
                    )
                ]
            ]
            reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = None

        try:
            await message_object.reply_photo(bio, reply_markup=reply_markup)  # type: ignore
        except telegram.error.BadRequest:
            await message_object.reply_document(bio2, reply_markup=reply_markup)  # type: ignore
    if send_text:
        html_table_text = f"<pre>\n{md_text}\n</pre>"

        # fmt: off
        await wrapped_send_text(
            message_object.reply_text,
            text=html_table_text,
            parse_mode=DEFAULT_PARSE_MODE,
            reply_markup=ReplyKeyboardRemove()
        )
        # fmt: on


async def on_end_asking_questions(
    ud: UserData,
    update: Update,
):
    def update_db_with_answers():
        assert isinstance(ud.conv_storage, ASKQuestionsConvStorage)

        answers = ud.conv_storage.cur_answers

        for i, text in enumerate(answers):
            day = ud.conv_storage.day

            assert ud.conv_storage.include_indices is not None

            question_index: int = ud.conv_storage.include_indices[i]
            question: QuestionDB = ud.db_cache.questions[question_index]

            if text is None:
                continue

            set_dict: dict[ColumnDC, ValueType] = {ColumnDC(column_name="text"): text}

            if ADD_TIME_TO_QUESTIONS:
                answer_time = get_now_time()
                set_dict[ColumnDC(column_name="time")] = answer_time

            update_or_insert_row(
                tablename="answer",
                where_clauses={
                    ColumnDC(column_name="date"): day,
                    ColumnDC(column_name="question_fk"): question.pk,
                },
                set_dict=set_dict,
            )

    assert isinstance(ud.conv_storage, ASKQuestionsConvStorage)
    if any(map(lambda x: x is not None, ud.conv_storage.cur_answers)):
        update_db_with_answers()
        ud.db_cache.reload_all()

    await send_entity_answers_df(
        update=update, ud=ud, answers_entity=AnswerType.QUESTION, send_csv=True
    )


async def on_end_asking_event(ud: UserData, update: Update):
    def update_db_with_events():
        assert isinstance(ud.conv_storage, ASKEventConvStorage)
        # day = ud.conv_storage.day
        day = get_today()

        event: EventDB = ud.db_cache.events[ud.conv_storage.chosen_event_index]
        new_time: datetime.time = ud.conv_storage.event_time
        new_text: str | None = ud.conv_storage.event_text

        row_dict: dict[ColumnDC, ValueType] = {
            ColumnDC(column_name="date"): day,
            ColumnDC(column_name="event_fk"): event.pk,
        }

        if new_time:
            row_dict[ColumnDC(column_name="time")] = new_time

        if new_text:
            row_dict[ColumnDC(column_name="text")] = new_text

        _insert_row(tablename="answer", row_dict=row_dict)

    assert isinstance(ud.conv_storage, ASKEventConvStorage)

    update_db_with_events()
    ud.db_cache.reload_all()

    await send_entity_answers_df(
        update=update, ud=ud, answers_entity=AnswerType.EVENT, send_csv=True
    )
