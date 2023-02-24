import dataclasses
import datetime
from typing import (
    Callable,
    Optional,
    Sequence
)

import pandas as pd
import psycopg

from db.base import (
    _query_get,
    get_where,
    provide_conn
)


def time_or_hours(s: str) -> datetime.time:
    def str_to_time(s: str) -> datetime.time:
        t = datetime.time.fromisoformat(s)
        return t
        # return (t.hour * 60 + t.minute) / 60

    def float_hrs_to_time(s: str) -> datetime.time:
        f = float(s)

        hrs = int(f) % 24
        mins = int((f - int(f)) * 60)

        return datetime.time(hour=hrs, minute=mins)

    try:
        t = str_to_time(s)
    except Exception:
        t = float_hrs_to_time(s)

    return t


@dataclasses.dataclass
class QuestionTypeDB:
    id: int
    name: str
    notation_str: str


@dataclasses.dataclass
class QuestionDB:
    name: str
    num_int: int
    fulltext: str
    suggested_answers_list: list[str]

    # type QuestionTypeDB
    # type ForeignKey
    type_id: int
    is_activated: bool = True

    @property
    def answer_apply_func(self) -> Optional[Callable]:

        qtype_answer_func_mapping = {
            # id: func <Callable>
            0: None,  # plain
            1: lambda x: int(x),  # int
            2: lambda x: 1 if str(x).lower() in ("да", "yes", "1") else 0,
            3: time_or_hours,
            4: None
        }

        return qtype_answer_func_mapping[self.type_id]


@provide_conn
def build_answers_df(
        conn: psycopg.connection,
        days_range=None,
        include_empty_cols=True
) -> pd.DataFrame:
    days = list()

    df = pd.DataFrame()

    if not days_range:
        query = "SELECT date FROM day ORDER BY date"
        rows = _query_get(conn, query)

        days = list(map(lambda x: x[0].isoformat(), rows))

    for day in days:
        # format: [('quest_name', 'answer_text'), ...]
        res = get_answers_on_day(conn, day)

        if not len(res):
            if include_empty_cols:
                df[day] = pd.Series()
            continue

        # Building pd.Series list of question_answer.answer_text with index as of question.name
        answers_column = pd.DataFrame(res).set_index(0).iloc[:, 0]
        questions_names = answers_column.index

        df = df.reindex(df.index.union(questions_names))
        # df = df.assign(**{'2023-02-02': answers_column})
        df[day] = answers_column

    qnames = get_ordered_questions_names()
    df = df.reindex(qnames)

    return df


@provide_conn
def get_ordered_questions_names(
        conn: psycopg.connection,
) -> list[str]:
    query = """SELECT name FROM question WHERE is_activated = True ORDER BY num_int;"""

    query_results = _query_get(conn, query)
    first_col = list(map(lambda x: x[0], query_results))

    return first_col


@provide_conn
def get_question_by_name(conn, name: str) -> QuestionDB | None:
    rows = get_where(
        conn,
        where_dict={'name': name},
        tablename='question'
    )
    assert len(rows) == 1
    row = rows[0]

    obj = QuestionDB(*row)
    return obj


def get_answers_on_day(conn: psycopg.connection, day: str | datetime.date) -> Sequence:
    rows = get_where(
        conn,
        where_dict={'day_fk': day},
        tablename='question_answer',
        select_cols=('question_fk', 'answer_text')
    )

    return rows

