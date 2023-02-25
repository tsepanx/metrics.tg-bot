import dataclasses
import datetime
from typing import (
    Callable,
    Optional,
    Sequence
)

import pandas as pd
import psycopg
from psycopg.sql import SQL, Identifier, Placeholder

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
    is_activated: bool

    __type_fk = None

    @property
    def answer_apply_func(self) -> Optional[Callable]:
        qtype_answer_func_mapping = {
            # id: func <Callable>
            0: None,  # text
            1: lambda x: int(x),  # int
            2: lambda x: 1 if str(x).lower() in ("да", "yes", "1") else 0,
            3: time_or_hours,
            4: None
        }

        return qtype_answer_func_mapping[self.type_id]

    @property
    def type_fk(self) -> QuestionTypeDB:
        if not self.__type_fk:
            rows = provide_conn(get_where)({'id': self.type_id}, 'question_type')

            obj = QuestionTypeDB(*rows[0])
            self.__type_fk = obj

        return self.__type_fk

    @type_fk.setter
    def type_fk(self, obj: QuestionTypeDB):
        if not isinstance(obj, QuestionTypeDB):
            raise Exception

        self.__type_fk = obj


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
    else:
        days = days_range

    for day in days:
        # format: [('quest_name', 'answer_text'), ...]
        col_from_db = get_answers_on_day(conn, day)

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


@provide_conn
def get_questions_with_type_fk(conn, qnames: list[str]) -> list[QuestionDB] | None:
    template_query = """SELECT * FROM question AS q
        JOIN question_type qt
            ON q.type_id = qt.id
        WHERE q.name IN ({})
        ORDER BY q.num_int;
    """

    query = SQL(template_query).format(
        SQL(', ').join(Placeholder() * len(qnames))
    ).as_string(conn)

    rows = _query_get(
        conn,
        query=query,
        params=qnames
    )

    res_list: list[QuestionDB] = []

    for r in rows:
        # TODO research how to get it cleaner
        q_attrs_count = 6
        qt_attrs_count = 3

        row_q_attrs = r[:q_attrs_count]
        row_qt_attrs = r[q_attrs_count:q_attrs_count + qt_attrs_count]

        q_obj = QuestionDB(*row_q_attrs)
        qt_obj = QuestionTypeDB(*row_qt_attrs)

        q_obj.type_fk = qt_obj
        res_list.append(q_obj)

    return res_list


def get_answers_on_day(conn: psycopg.connection, day: str | datetime.date) -> pd.Series | None:
    rows = get_where(
        conn,
        where_dict={'day_fk': day},
        tablename='question_answer',
        select_cols=('question_fk', 'answer_text')
    )

    if not len(rows):
        return None

    # Building pd.Series list of question_answer.answer_text with index as of question.name
    answers_column = pd.DataFrame(rows).set_index(0).iloc[:, 0]
    return answers_column


if __name__ == "__main__":
    get_questions_with_type_fk(['walking', 'x_small', 'x_big'])
