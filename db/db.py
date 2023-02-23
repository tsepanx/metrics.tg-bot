import datetime
import psycopg
import pandas as pd

from typing import Sequence, Optional


def _psql_conn():
    conn = psycopg.connect(
        dbname='postgres',
        user='postgres',
        password='',
        host='localhost'
    )
    return conn


def _query_get(
        conn: psycopg.connection,
        query: str,
        params: Optional[dict | Sequence] = tuple()
) -> Sequence:
    with conn.cursor() as cur:
        # if params:
        cur.execute(query, params)
        results = cur.fetchall()
        return results


def _query_change(
        conn: psycopg.connection,
        query: str,
        params: Optional[dict | Sequence] = tuple()
):
    with conn.cursor() as cur:
        cur.execute(query, params)
        conn.commit()


def _exists(conn: psycopg.connection, pk: tuple, query: str):
    assert query.lower().startswith('select')

    res = _query_get(conn, query)
    # res = list(map(lambda x: x[0], res))

    # r = res[0]
    for r in res:
        # r = r[1:]
        # r = r[:-1]
        # rs = r.split(',')

        eq = list(pk) == list(r)

        if eq:
            return True

    return False


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


def build_answers_df(
        conn: psycopg.connection,
        days_range=None,
        include_empty_cols=True
) -> pd.DataFrame:
    days = list()

    df = pd.DataFrame()

    if not days_range:
        query = "SELECT date FROM day ORDER BY date"
        query_results = _query_get(conn, query)

        days = list(map(lambda x: x[0], query_results))

    for day in days:
        # format: [('quest_name', 'answer_text'), ...]
        res = _get_answers_on_day(conn, day)

        if not len(res):
            if include_empty_cols:
                res = [('', '')]
            else:
                continue

        # Building pd.Series list of question_answer.answer_text with index as of question.name
        answers_column: pd.Series = pd.DataFrame(res).set_index(0).iloc[:, 0]
        questions_names = answers_column.index

        df = df.reindex(df.index.union(questions_names))
        # df = df.assign(**{'2023-02-02': answers_column})
        df[day] = answers_column

    return df


if __name__ == "__main__":
    conn = _psql_conn()

    answers_df = build_answers_df(conn)
    print(answers_df)

    conn.commit()
    conn.close()
