import dataclasses
import datetime
from typing import (
    Callable,
    Optional
)

import pandas as pd
import psycopg

from db.base import (
    _get_where,
    _query_get,
    provide_conn
)
from questions import (
    binary_f,
    time_or_hours
)


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
        # conn = _psql_conn()
        # qtype_row = _get_row(conn, {'id': self.type_id}, 'question_type')
        # qtype = QuestionTypeDB(*qtype_row)

        qtype_answer_func_mapping = {
            # id: func <Callable>
            0: None,  # plain
            1: lambda x: int(x),  # int
            2: binary_f,
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
        res = _get_answers_on_day(conn, day)

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

    qnames = get_questions_names()
    df = df.reindex(qnames)

    return df


@provide_conn
def get_questions_names(
        conn: psycopg.connection,
) -> list[str]:
    query = """
        -- Print all questions list
        SELECT q.name FROM question AS q
            JOIN question_type qt
                ON qt.id = q.type_id
            ORDER BY q.num_int;
    """

    query_results = _query_get(conn, query)
    first_col = list(map(lambda x: x[0], query_results))

    return first_col


@provide_conn
def get_question(conn, name: str) -> QuestionDB | None:
    rows = _get_where(
        conn,
        where_dict={'name': name},
        tablename='question'
    )
    assert len(rows) == 1
    row = rows[0]

    obj = QuestionDB(*row)
    return obj


def _get_answers_on_day(conn: psycopg.connection, day: str | datetime.date):
    query = """
        -- Show all answers for given day, sorted by q.num_int
        SELECT qa.question_fk, qa.answer_text FROM question_answer AS qa
            JOIN question q on q.name = qa.question_fk
                WHERE
                    qa.day_fk = %s
            ORDER BY qa.day_fk, q.num_int;
    """

    res = _query_get(
        conn,
        query,
        params=(day,)
    )

    return res