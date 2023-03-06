import datetime
from dataclasses import dataclass
from typing import Callable

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
)


def binary(x: str) -> int:
    if x.lower() not in ("да", "нет", "0", "1"):
        raise FormatException
    return 1 if str(x).lower() in ("да", "yes", "1") else 0


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


class QuestionTypeEnum(MyEnum):
    TEXT = QuestionTypeEntity("[Text]", "text123")
    INT = QuestionTypeEntity("[Integer]", "1234", apply_func=int)
    BINARY = QuestionTypeEntity("[0/1 Binary]", "Да/Нет/0/1", apply_func=binary)
    HOURS = QuestionTypeEntity("[Hours (time)]", "04:35", apply_func=time_or_hours)
    TIMESTAMP = QuestionTypeEntity(
        "[Timestamp (datetime)]", "2023-03-23 04:35", apply_func=timestamp
    )


@dataclass(frozen=True, slots=True)
class QuestionDB(Table):
    # pylint: disable=too-many-instance-attributes

    pk: int

    user_id: int  # ForeignKey: 'TgUserDB'

    name: str
    fulltext: str
    choices_list: tuple[str]

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
