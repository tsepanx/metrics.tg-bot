import pprint
from dataclasses import dataclass
import datetime
from typing import (
    Callable,
    Optional,
)

import pandas as pd
from psycopg.sql import (
    SQL,
    Placeholder,
)

from src.db.base import (
    _query_get,
    get_psql_conn,
    get_where,
)
from src.db.classes import get_dataclasses_where, Table, ForeignKey


@dataclass(frozen=True)
class QuestionTypeDB(Table):
    # id: int
    pk: int
    name: str
    notation_str: str

    class Meta:
        tablename = "question_type"


@dataclass(frozen=True)
class QuestionDB(Table):
    # pylint: disable=too-many-instance-attributes

    # def __post_init__(self):
    #     # object.__setattr__(self, 'value', None)
    #     columns = self.__annotations__
    #
    #     for col in columns.items():
    #         col_type = col[1]
    #
    #         if issubclass(col_type, Table):
    #             print(col)
    #         print(col)
    #
    #     rows: list[QuestionTypeDB] = get_dataclasses_where(
    #         QuestionTypeDB,
    #         where_dict={"id": self.type_id},
    #     )
    #     assert len(rows) == 1
    #     self.__type_fk = rows[0]
    #     return self.__type_fk

    name: str
    fulltext: str
    suggested_answers_list: list[str]

    is_activated: bool
    order_by: int

    # ForeignKey : 'QuestionTypeDB'
    type_id: int
    # type_fk: ForeignKey(QuestionTypeDB, "type_id", int)

    class Meta:
        foreign_keys: dict = {
            "type_id": ForeignKey(QuestionTypeDB, "pk")
        }
        tablename = "question"

    @property
    def question_type(self) -> QuestionTypeDB:
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


def build_answers_df(days_range=None, include_empty_cols=True) -> pd.DataFrame:
    df = pd.DataFrame()

    if not days_range:
        query = "SELECT date FROM day ORDER BY date"
        rows = _query_get(query)

        days = list(map(lambda x: x[0].isoformat(), rows))
    else:
        days = days_range

    for day in days:
        # format: [('quest_name', 'answer_text'), ...]
        col_from_db = get_answers_on_day(day)

        if col_from_db is None:
            if include_empty_cols:
                df[day] = pd.Series()
            continue

        questions_names = col_from_db.index
        df = df.reindex(df.index.union(questions_names))
        df[day] = col_from_db

    qnames = get_ordered_questions_names()
    df = df.reindex(qnames)

    return df


def get_ordered_questions_names() -> list[str]:
    query = """SELECT name FROM question WHERE is_activated = True ORDER BY num_int;"""

    query_results = _query_get(query)
    first_col = list(map(lambda x: x[0], query_results))

    return first_col


def get_question_by_name(name: str) -> QuestionDB | None:
    rows = get_where(
        tablename="question",
        where_dict={"name": name}
    )
    assert len(rows) == 1
    row = rows[0]

    obj = QuestionDB(*row)
    return obj


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
    rows = get_where(
        tablename="question_answer",
        select_cols=("question_fk", "answer_text"),
        where_dict={"day_fk": day},
    )

    if not rows:
        return None

    # Building pd.Series list of question_answer.answer_text with index as of question.name
    answers_column = pd.DataFrame(rows).set_index(0).iloc[:, 0]
    return answers_column


if __name__ == "__main__":
    # get_questions_with_type_fk(["walking", "x_small", "x_big"])

    l = get_dataclasses_where(
        class_=QuestionDB,
        join_foreign_keys=True,
        # where_dict={QuestionDB.is_activated: True},
        where_dict={'is_activated': True},
        order_by=['order_by']
    )

    for i in l:
        pprint.pprint(i)

        fk_obj = i.get_fk_value('type_id')
        print(i.type_id, fk_obj.pk)

        assert i.type_id == fk_obj.pk

