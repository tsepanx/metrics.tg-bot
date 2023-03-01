import datetime
import pprint
from dataclasses import dataclass

from src.event import EventDB
from src.orm.base import ColumnDC
from src.orm.dataclasses import Table, ForeignKeyRelation
from src.question import QuestionDB


@dataclass(frozen=True)
class AnswerDB(Table):
    pk: int

    date: datetime.date
    event_fk: int
    question_fk: int
    time: datetime.time
    text: str

    class Meta:
        foreign_keys = [
            ForeignKeyRelation(QuestionDB, "question_fk", "pk"),
            ForeignKeyRelation(EventDB, "event_fk", "pk"),
        ]
        tablename = "answer"


if __name__ == "__main__":
    answers = AnswerDB.select(
        join_on_fkeys=True,
        where_clauses=None,
        order_by_columns=[
            ColumnDC(table_name="answer", column_name="date")
        ]
    )

    pprint.pprint(answers)
    for answer in answers:
        assert answer.get_fk_value("question_fk").pk == answer.question_fk
