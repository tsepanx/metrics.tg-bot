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
    Update,
)
from telegram.constants import (
    ParseMode,
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
    get_today,
    text_to_png,
)
from src.utils_pd import (
    df_to_markdown,
)
from src.utils_tg import (
    wrapped_send_text,
)

STOP_ASKING = "Stop asking"
SKIP_QUEST = "Skip question"


def get_entity_type_reply_keyboard():
    reply_keyboard = [["Question", "Event"]]
    reply_markup = ReplyKeyboardMarkup(
        reply_keyboard,
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    return reply_markup


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
            InlineKeyboardButton("⬆️ Up ../", callback_data="go_up"),
        )

    event: EventDB
    for subdir, (cnt, event) in subpath_events.items():
        if subdir == "":
            text = "/"
            callback_data = "END"
        else:
            callback_data = subdir
            text = f"{subdir}"
            if cnt > 1:
                text = f"🗂 [{cnt}] {text}"

        if cnt == 1:
            if event.type == "Durable":
                text = f"🕓 {text}"
            elif event.type == "Single":
                text = f"📍 {text}"

        button = InlineKeyboardButton(text, callback_data=callback_data)
        buttons_column.append(button)

    reply_markup = InlineKeyboardMarkup.from_column(buttons_column)
    return reply_markup


def get_questions_select_keyboard(
    questions: list[QuestionDB],
    include_indices: list[int] = None,
    emoji_str: str = "☑️",
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("All", callback_data="all"),
            InlineKeyboardButton("Unanswered", callback_data="unanswered"),
            InlineKeyboardButton("Clear", callback_data="clear"),
            InlineKeyboardButton(
                f"{'✅ ' if include_indices else ''}OK", callback_data="end_choosing"
            ),
        ],
    ]

    for i, q in enumerate(questions):
        if include_indices is not None and i in include_indices:
            butt_text = f"{emoji_str} {q.name}"
            butt_data = f"{i} remove"
        else:
            butt_text = f"{q.name}"
            butt_data = f"{i} add"

        new_button = InlineKeyboardButton(text=butt_text, callback_data=butt_data)
        keyboard.append([new_button])

    return InlineKeyboardMarkup(keyboard)


async def send_ask_question(q: QuestionDB, send_text_func: Callable, existing_answer: str = None):
    buttons = [list(map(str, q.choices_list)), [SKIP_QUEST, STOP_ASKING]]

    reply_markup = telegram.ReplyKeyboardMarkup(
        buttons, one_time_keyboard=True, resize_keyboard=True
    )

    text = f"{q.html_notation()}"
    if existing_answer:
        text += f"\n\nAnswer in DB: <code>{existing_answer}</code>"

    await wrapped_send_text(
        send_message_func=send_text_func,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )


async def send_ask_event_time(event: EventDB, send_text_func: Callable):
    buttons = [["Now"]]

    reply_markup = telegram.ReplyKeyboardMarkup(
        buttons, one_time_keyboard=True, resize_keyboard=True
    )

    text = f"Event: `{event.name}`\nwrite time (f.e. 05:04)"

    await wrapped_send_text(
        send_message_func=send_text_func,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN,
    )


async def send_ask_event_text(e: EventDB, send_text_func: Callable):
    text = f"Event: {e.name}\nwrite text value (optionally)"

    buttons = []

    if e.type == "Durable":
        buttons.append(["start", "end"])

    buttons.append(["None"])

    reply_markup = telegram.ReplyKeyboardMarkup(
        keyboard=buttons, one_time_keyboard=True, resize_keyboard=True
    )

    await wrapped_send_text(
        send_message_func=send_text_func,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
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
        bio.name = "img.png"

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
            parse_mode=ParseMode.HTML
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

            update_or_insert_row(
                tablename="answer",
                where_clauses={
                    ColumnDC(column_name="date"): day,
                    ColumnDC(column_name="question_fk"): question.pk,
                },
                set_dict={ColumnDC(column_name="text"): text},
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
