import datetime
import pprint
from dataclasses import dataclass
from typing import (
    Callable,
    Optional,
)

import pandas as pd
from psycopg.sql import (
    SQL,
    Placeholder,
)

from src.orm.base import (
    ColumnDC,
    JoinByClauseDC,
    get_psql_conn,
    _select,
)
from src.orm.dataclasses import (
    ForeignKeyRelation,
    Table,
)


@dataclass(frozen=True)
class QuestionTypeDB(Table):
    # id: int
    pk: int
    name: str
    notation_str: str

    class Meta:
        tablename = "question_type"


@dataclass(frozen=True, repr=True, slots=True, unsafe_hash=True, match_args=True, kw_only=True)
class QuestionDB(Table):
    # pylint: disable=too-many-instance-attributes

    pk: int

    name: str
    fulltext: str
    suggested_answers_list: list[str]

    is_activated: bool
    order_by: int

    # ForeignKey : 'QuestionTypeDB'
    type_id: int

    class Meta:
        foreign_keys = [ForeignKeyRelation(QuestionTypeDB, "type_id", "pk")]
        tablename = "question"

    @classmethod
    def select_all(cls):
        return cls.select(
            join_on_fkeys=True,
            where_clauses={
                ColumnDC(column_name="is_activated"): True
            },
            order_by_columns=[
                ColumnDC(table_name=cls.Meta.tablename, column_name="order_by")
            ]
        )

    @property
    def question_type(self) -> QuestionTypeDB | None:
        return self.get_fk_value("type_id")

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
            if value not in self.suggested_answers_list:
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


# def get_ordered_questions_names() -> list[str]:
#     query = """SELECT name FROM question WHERE is_activated = True ORDER BY num_int;"""
#
#     query_results = _query_get(query)
#     first_col = list(map(lambda x: x[0], query_results))
#
#     return first_col


# def get_question_by_name(name: str) -> QuestionDB | None:
#     rows = _select(tablename="question", where_clauses={"name": name})
#     assert len(rows) == 1
#     row = rows[0]
#
#     obj = QuestionDB(*row)
#     return obj


def get_questions_with_type_fk(qnames: list[str]) -> list[QuestionDB] | None:
    template_query = """SELECT * FROM question AS q
        JOIN question_type qt
            ON q.type_id = qt.id
        WHERE q.name IN ({})
        ORDER BY q.num_int;
    """

    # fmt: off
    query = SQL(template_query).format(
        SQL(", ").join(Placeholder() * len(qnames))
    ).as_string(get_psql_conn())
    # fmt: on

    rows = _query_get(query=query, params=qnames)

    res_list: list[QuestionDB] = []

    for r in rows:
        # TODO research how to get it cleaner
        q_attrs_count = 6
        qt_attrs_count = 3

        row_q_attrs = r[:q_attrs_count]
        row_qt_attrs = r[q_attrs_count : q_attrs_count + qt_attrs_count]

        q_obj = QuestionDB(*row_q_attrs)
        qt_obj = QuestionTypeDB(*row_qt_attrs)

        q_obj.type_fk = qt_obj
        res_list.append(q_obj)

    return res_list


def get_answers_on_day(day: str | datetime.date) -> pd.Series | None:
    if isinstance(day, datetime.date):
        day = str(day.isoformat())

    rows = _select(
        tablename="answer",
        select_columns=[ColumnDC("date"), ColumnDC("text")],
        join_clauses=[JoinByClauseDC("question", from_column="question_fk", to_column="pk")],
        where_clauses={ColumnDC("date"): day},
        order_by_columns=[ColumnDC(table_name="question", column_name="order_by")],
    )

    if not rows:
        return None

    # Building pd.Series list of question_answer.answer_text with index as of question.name
    answers_column = pd.DataFrame(rows).set_index(0)  # .iloc[:, 0]
    return answers_column


def test_get_questions():
    # get_questions_with_type_fk(["walking", "x_small", "x_big"])

    l = QuestionDB.select(
        join_on_fkeys=True,
        where_clauses={ColumnDC(column_name="is_activated"): True},
        order_by_columns=[ColumnDC(column_name="order_by")],
    )

    for i in l:
        pprint.pprint(i)

        fk_obj = i.get_fk_value("type_id")
        print(i.type_id, fk_obj.pk)

        assert i.type_id == fk_obj.pk


def test_get_answers():
    res = get_answers_on_day("2023-02-25")
    print(res)


if __name__ == "__main__":
    test_get_answers()
    # test_get_questions()
