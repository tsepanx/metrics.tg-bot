import datetime
import pprint
from dataclasses import dataclass

from src.orm.base import ColumnDC
from src.orm.dataclasses import (
    ForeignKey,
    Table,
)
from src.tables.event import (
    EventDB,
)
from src.tables.question import (
    QuestionDB,
)


@dataclass(frozen=True, slots=True)
class AnswerDB(Table):
    pk: int

    date: datetime.date

    event_fk: int  # ForeignKey : 'EventDB'
    question_fk: int  # ForeignKey : 'QuestionDB'
    # lasting_event_fk: int  # ForeignKey : 'LastingEventDB'

    time: datetime.time
    text: str

    @property
    def question(self) -> QuestionDB | None:
        # return self.get_fk_value("question_fk")
        return self.get_fk_value(AnswerType.QUESTION.value)

    @property
    def event(self) -> EventDB | None:
        # return self.get_fk_value("event_fk")
        return self.get_fk_value(AnswerType.EVENT.value)

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

    class Meta(Table.Meta):
        # foreign_keys = AnswerType.values_list()
        tablename = "answer"

    class ForeignKeys(Table.ForeignKeys):
        QUESTION = ForeignKey(QuestionDB, "question_fk", "pk")
        EVENT = ForeignKey(EventDB, "event_fk", "pk")


AnswerType = AnswerDB.ForeignKeys


if __name__ == "__main__":
    answers = AnswerDB.select(
        join_on_fkeys=True,
        order_by_columns=[ColumnDC(table_name="answer", column_name="date")],
    )

    pprint.pprint(answers)
    for answer in answers:
        assert answer.get_fk_value(AnswerType.QUESTION.value).pk == answer.question_fk
