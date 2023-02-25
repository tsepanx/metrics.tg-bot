import os
from typing import (
    Any,
    Optional,
    Sequence,
)

import psycopg
from psycopg.sql import (
    SQL,
    Identifier,
    Placeholder,
)

PG_DB = os.environ.get("PG_DB", "postgres")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "")


def _psql_conn():
    conn = psycopg.connect(dbname=PG_DB, user=PG_USER, password=PG_PASSWORD, host=PG_HOST)
    return conn


_pg_conn = None


def get_psql_conn():
    # pylint: disable=global-statement
    global _pg_conn

    if not _pg_conn or _pg_conn.closed:
        _pg_conn = _psql_conn()

    return _pg_conn


def prefix_keys(d: dict[str, Any], pref: str) -> dict[str, Any]:
    new_d = {}
    for key in d:
        new_key = f"{pref}{key}"
        new_d[new_key] = d[key]

    return new_d


def _query_get(query: str, params: Optional[dict | Sequence] = tuple()) -> Sequence:
    print(query, params)

    conn = get_psql_conn()
    cur = conn.cursor()

    try:
        cur.execute(query, params)
    except psycopg.errors.InFailedSqlTransaction:
        conn.close()
        conn = get_psql_conn()
        cur = conn.cursor()

        cur.execute(query, params)

    results = cur.fetchall()
    return results


def _query_set(query: str, params: Optional[dict | Sequence] = tuple()):
    print(query, params)

    conn = get_psql_conn()
    with conn.cursor() as cur:
        try:
            cur.execute(query, params)
        except psycopg.errors.InFailedSqlTransaction:
            conn.close()
            conn = get_psql_conn()
            cur = conn.cursor()
            cur.execute(query, params)

        conn.commit()


def get_where(where_dict: dict, tablename: str, select_cols: Sequence[str] | None = None) -> Sequence:
    # TODO add possibility for "WHERE col1 IN (1, 2)" clause
    # TODO needed to search dict values for list, and add additional query string for those pairs

    where_names = tuple(where_dict.keys())

    format_list = [
        Identifier(tablename),
        SQL(", ").join(map(Identifier, where_names)),
        SQL(", ").join(map(Placeholder, where_names)),
    ]

    if select_cols:
        template_query = "SELECT {} FROM {} WHERE ({}) = ({})"
        format_list.insert(0, SQL(", ").join(map(Identifier, select_cols)))
    else:
        template_query = "SELECT * FROM {} WHERE ({}) = ({})"

    query = SQL(template_query).format(*format_list).as_string(get_psql_conn())

    return _query_get(query=query, params=where_dict)


def _exists(where_dict: dict[str, Any], tablename: str):
    return len(get_where(where_dict, tablename)) > 0


def exists(where_dict: dict[str, Any], tablename: str):
    return _exists(where_dict, tablename)


def _insert_row(row_dict: dict[str, Any], tablename: str):
    names = tuple(row_dict.keys())

    query = (
        SQL("INSERT INTO {} ({}) VALUES ({});")
        .format(
            Identifier(tablename),  # tablename
            SQL(", ").join(map(Identifier, names)),  # (col1, col2)
            SQL(", ").join(map(Placeholder, names)),  # (%(col1)s, %(col1)s) -> ('val1', 'val2')
        )
        .as_string(get_psql_conn())
    )

    try:
        _query_set(query, row_dict)
    except psycopg.errors.UniqueViolation as e:
        raise e


def _update_row(where_dict: dict[str, Any], set_dict: dict[str, Any], tablename: str):
    where_names = tuple(where_dict.keys())
    set_names = tuple(set_dict.keys())

    # This is done to avoid duplicate placeholder names in template query:
    # UPDATE table SET "col1" = %(set_col1)s WHERE ("col1", "col2") = (%(where_col1)s, %(where_col2)s)
    prefixed_where_dict = prefix_keys(where_dict, "where_")
    prefixed_set_dict = prefix_keys(set_dict, "set_")

    prefixed_where_names = tuple(prefixed_where_dict.keys())
    prefixed_set_names = tuple(prefixed_set_dict.keys())

    if len(set_names) == 1:
        # "UPDATE {tablename} SET answer_text = '66664' WHERE (day_fk, question_fk) = ('2023-02-23', 'weight')"
        template_query = "UPDATE {} SET {} = {} WHERE ({}) = ({})"
    elif len(set_names) > 1:
        template_query = "UPDATE {} SET ({}) = ({}) WHERE ({}) = ({})"
    else:
        raise Exception

    # query = SQL("SELECT * FROM {} WHERE ({}) = ({})").format(
    query = (
        SQL(template_query)
        .format(
            Identifier(tablename),  # tablename     "question_answer"
            SQL(", ").join(map(Identifier, set_names)),  # set columns   (col3, col4)
            SQL(", ").join(map(Placeholder, prefixed_set_names)),  # set values    ('val1', 'val2')
            SQL(", ").join(map(Identifier, where_names)),  # where columns (col1, col2)
            SQL(", ").join(map(Placeholder, prefixed_where_names)),  # where values  (%s, %s)
        )
        .as_string(get_psql_conn())
    )

    placeholder_values = {**prefixed_set_dict, **prefixed_where_dict}

    _query_set(query, placeholder_values)


def update_or_insert_row(where_dict: dict[str, Any], set_dict: dict[str, Any], tablename: str):
    # Ensure that full row values as passed neither in filter_dict nor set_dict
    # columns_set = ...
    # assert set(where_dict).union(set(set_dict)) == columns_set

    if _exists(where_dict, tablename):
        _update_row(where_dict, set_dict, tablename)
    else:
        row_dict = {**where_dict, **set_dict}
        _insert_row(row_dict, tablename)


if __name__ == "__main__":
    # answers_df = build_answers_df()
    # print(answers_df)

    # questions_list = get_questions_names()
    # print(questions_list)

    # "UPDATE {tablename} SET answer_text = '66664' WHERE (day_fk, question_fk) = ('2023-02-23', 'weight')"
    _update_row(
        {"day_fk": "2023-02-23", "question_fk": "weight"},
        # {'answer_text': '2345'},
        {"answer_text": "new_2345"},
        "question_answer",
    )

    _insert_row({"day_fk": "2023-02-24", "question_fk": "x_small"}, "question_answer")

    update_or_insert_row(
        {"day_fk": "2023-02-25", "answer_text": "walkn1"}, {"question_fk": "vegetables_eat"}, "question_answer"
    )
