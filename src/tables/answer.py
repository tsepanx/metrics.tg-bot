import datetime
import enum
import pprint
from dataclasses import dataclass
from typing import Type

from src.orm.base import ColumnDC
from src.orm.dataclasses import (
    ForeignKeyRelation,
    Table,
)
from src.tables.event import (
    EventDB,
)
from src.tables.question import (
    QuestionDB,
)


class MyEnum(enum.Enum):
    @classmethod
    def values_list(cls):
        return list(map(lambda x: x.value, cls.__members__.values()))

    @classmethod
    def enum_by_name(cls, name: str) -> Type["MyEnum"] | None:
        return cls.__members__.get(name)


class AnswerType(MyEnum):
    # NAME = <ForeignKey object> in "answer" table
    QUESTION = ForeignKeyRelation(QuestionDB, "question_fk", "pk")
    EVENT = ForeignKeyRelation(EventDB, "event_fk", "pk")


@dataclass(frozen=True)
class AnswerDB(Table):
    pk: int

    date: datetime.date
    event_fk: int
    question_fk: int
    time: datetime.time
    text: str

    @property
    def question(self) -> QuestionDB | None:
        return self.get_fk_value("question_fk")

    @property
    def event(self) -> EventDB | None:
        return self.get_fk_value("event_fk")

    @classmethod
    def select_all(cls):
        return cls.select(
            join_on_fkeys=True,
            where_clauses=None,
            order_by_columns=[
                ColumnDC(table_name=cls.Meta.tablename, column_name="date"),
                ColumnDC(table_name="question", column_name="order_by"),
            ],
        )

    class Meta:
        foreign_keys = AnswerType.values_list()
        tablename = "answer"


if __name__ == "__main__":
    answers = AnswerDB.select(
        join_on_fkeys=True,
        order_by_columns=[ColumnDC(table_name="answer", column_name="date")],
    )

    pprint.pprint(answers)
    for answer in answers:
        assert answer.get_fk_value("question_fk").pk == answer.question_fk
