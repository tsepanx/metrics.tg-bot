import datetime
import pprint
from dataclasses import dataclass
from typing import (
    Callable,
    Optional,
)

from src.orm.base import ColumnDC
from src.orm.dataclasses import (
    ForeignKeyRelation,
    Table,
)
from src.tables.tg_user import (
    TgUserDB,
)


@dataclass(frozen=True, slots=True)
class QuestionTypeDB(Table):
    # id: int
    pk: int
    name: str
    notation_str: str

    class Meta:
        tablename = "question_type"


@dataclass(frozen=True, slots=True)
class QuestionDB(Table):
    # pylint: disable=too-many-instance-attributes

    pk: int

    user_id: int  # ForeignKey: 'TgUserDB'

    name: str
    fulltext: str
    # TODO: Rename to "choices_list"
    choices_list: tuple[str]

    is_activated: bool
    order_by: int

    type_id: int  # ForeignKey : 'QuestionTypeDB'

    def html_notation(self):
        return f"<code>{self.question_type.notation_str}</code> {self.fulltext if self.fulltext else self.name}"

    @classmethod
    def select_all(cls):
        return cls.select(
            join_on_fkeys=True,
            where_clauses={
                ColumnDC(table_name=cls.Meta.tablename, column_name="is_activated"): True
            },
            order_by_columns=[ColumnDC(table_name=cls.Meta.tablename, column_name="order_by")],
        )

    @property
    def question_type(self) -> QuestionTypeDB | None:
        # return self.get_fk_value("type_id")
        return self.get_fk_value(self.ForeignKeys.TYPE_ID.value)

    @property
    def answer_apply_func(self) -> Optional[Callable]:
        def time_or_hours(s: str) -> datetime.time:
            try:
                # str_to_time
                t = datetime.time.fromisoformat(s)
                return t
                # return (t.hour * 60 + t.minute) / 60
            except Exception:
                # float_hrs_to_time
                f = float(s)

                hrs = int(f) % 24
                mins = int((f - int(f)) * 60)

                return datetime.time(hour=hrs, minute=mins)

        def choice(value: str) -> str:
            if value not in self.choices_list:
                raise Exception
            return value

        qtype_answer_func_mapping = {
            # id: func <Callable>
            0: None,  # text
            1: int,  # int
            2: lambda x: 1 if str(x).lower() in ("да", "yes", "1") else 0,  # binary
            3: time_or_hours,  # hours
            4: choice,
        }

        return qtype_answer_func_mapping[self.type_id]

    class Meta(Table.Meta):
        # foreign_keys = QuestionFKs.values_list()
        tablename = "question"

    class ForeignKeys(Table.ForeignKeys):
        TYPE_ID = ForeignKeyRelation(QuestionTypeDB, "type_id", "pk")
        USER_ID = ForeignKeyRelation(TgUserDB, "user_id", "user_id")


if __name__ == "__main__":
    # get_questions_with_type_fk(["walking", "x_small", "x_big"])

    rows = QuestionDB.select(
        join_on_fkeys=True,
        where_clauses={ColumnDC(column_name="is_activated"): True},
        order_by_columns=[ColumnDC(column_name="order_by")],
    )

    for i in rows:
        pprint.pprint(i)

        fk_obj = i.get_fk_value(QuestionDB.ForeignKeys.TYPE_ID.value)
        print(i.type_id, fk_obj.pk)

        assert i.type_id == fk_obj.pk
