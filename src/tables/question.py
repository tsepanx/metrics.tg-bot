import datetime
from dataclasses import dataclass
from typing import Callable

from src.conversations.ask_constants import (
    BINARY_CHOICE_NO,
    BINARY_CHOICE_YES,
    TIME_CHOICE_NOW,
)
from src.orm.base import ColumnDC
from src.orm.dataclasses import (
    ForeignKey,
    Table,
)
from src.tables.tg_user import (
    TgUserDB,
)
from src.utils import (
    FormatException,
    MyEnum,
    get_now,
)


def binary(x: str) -> int:
    if x.lower() not in (BINARY_CHOICE_YES.lower(), BINARY_CHOICE_NO.lower(), "0", "1"):
        raise FormatException
    return 1 if x.lower() in (BINARY_CHOICE_YES.lower(), "yes", "1") else 0


def time_or_hours(s: str) -> datetime.time:
    try:
        t = datetime.time.fromisoformat(s)
        return t
    except ValueError:
        f = float(s)

        hrs = int(f) % 24
        mins = int((f - int(f)) * 60)

        return datetime.time(hour=hrs, minute=mins)


def timestamp(value: str) -> datetime.datetime:
    if value == TIME_CHOICE_NOW:
        return get_now()

    try:
        # format: 2023-03-23 01:02:03
        dt = datetime.datetime.fromisoformat(value)
        return dt
    except ValueError as exc:
        raise FormatException from exc


# not a table class
@dataclass
class QuestionTypeEntity:
    # name: str
    notation_str: str
    format_str: str

    apply_func: Callable = lambda x: x
    additional_keyboard_choices: list[list[str]] | None = None


class QuestionTypeEnum(MyEnum):
    TEXT = QuestionTypeEntity("[Text]", "text123")
    INT = QuestionTypeEntity("[Integer]", "1234", apply_func=int)
    BINARY = QuestionTypeEntity(
        "[0/1 Binary]",
        f"{BINARY_CHOICE_YES}/{BINARY_CHOICE_NO}/0/1",
        apply_func=binary,
        # fmt: off
        additional_keyboard_choices=[[
            # "Да", "Нет"
            BINARY_CHOICE_YES,
            BINARY_CHOICE_NO,
        ]],
        # fmt: on
    )
    HOURS = QuestionTypeEntity("[Hours (time)]", "04:35", apply_func=time_or_hours)

    # TODO To be removed, as it duplicates `Events` functionality
    TIMESTAMP = QuestionTypeEntity(
        "[Timestamp (datetime)]",
        "2000-01-23 04:56",
        apply_func=timestamp,
        additional_keyboard_choices=[[TIME_CHOICE_NOW]],
    )


@dataclass(frozen=True, slots=True)
class QuestionDB(Table):
    # pylint: disable=too-many-instance-attributes

    pk: int

    user_id: int  # ForeignKey: 'TgUserDB'

    name: str
    fulltext: str
    choices_list: tuple[str] | None

    is_activated: bool
    order_by: int

    type_id: int  # ForeignKey : 'QuestionTypeDB'

    @property
    def question_type(self) -> QuestionTypeEntity:
        return QuestionTypeEnum.values_list()[self.type_id]

    def html_short(self):
        return f"<code>{self.question_type.notation_str}</code> {self.fulltext if self.fulltext else self.name}"

    def html_full(self, existing_answer: str | None) -> str:
        key_len = 11
        lines = [
            f"{'Type':<{key_len}}: {self.question_type.notation_str}",
            f"{'Name':<{key_len}}: {self.name}",
            f"{'Fulltext':<{key_len}}: {self.fulltext}",
            "",
            f"{'Value in DB':<{key_len}}: {existing_answer}",
        ]

        return "<code>" + "\n".join(lines) + "</code>"

    @classmethod
    def select_all(cls):
        return cls.select(
            join_on_fkeys=True,
            where_clauses={
                ColumnDC(table_name=cls.Meta.tablename, column_name="is_activated"): True
            },
            order_by_columns=[ColumnDC(table_name=cls.Meta.tablename, column_name="order_by")],
        )

    class Meta(Table.Meta):
        tablename = "question"

    class ForeignKeys(Table.ForeignKeys):
        # TYPE_ID = ForeignKey(QuestionTypeDB, "type_id", "pk")
        USER_ID = ForeignKey(TgUserDB, "user_id", "user_id")
