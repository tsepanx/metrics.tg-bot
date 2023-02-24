import os
from typing import (
    Optional,
    Sequence
)

import psycopg
from psycopg.sql import (
    SQL,
    Identifier,
    Placeholder
)

PG_DB = os.environ.get('PG_DB', 'postgres')
PG_USER = os.environ.get('PG_USER', 'postgres')
PG_HOST = os.environ.get('PG_HOST', 'localhost')
PG_PASSWORD = os.environ.get('PG_PASSWORD', '')


def prefix_keys(d: dict[str, any], pref: str) -> dict[str, any]:
    dd = dict()
    for key in d:
        new_key = f'{pref}{key}'
        dd[new_key] = d[key]

    return dd


def _psql_conn():
    conn = psycopg.connect(
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST
    )
    return conn


def provide_conn(func):
    # @functools.wraps
    def wrapper(*args, **kwargs):
        conn = _psql_conn()

        return func(conn, *args, **kwargs)

    return wrapper


def _query_get(
        conn: psycopg.connection,
        query: str,
        params: Optional[dict | Sequence] = tuple()
) -> Sequence:
    print(query)

    cur = conn.cursor()
    cur.execute(query, params)
    results = cur.fetchall()
    return results


def _query_set(
        conn: psycopg.connection,
        query: str,
        params: Optional[dict | Sequence] = tuple()
):
    print(query)
    with conn.cursor() as cur:
        cur.execute(query, params)
        conn.commit()


def get_where(
        conn: psycopg.connection,
        where_dict: dict,
        tablename: str,
        select_cols: Sequence[str] | None = None
) -> Sequence:
    where_names = tuple(where_dict.keys())

    format_values = [
        Identifier(tablename),
        SQL(', ').join(map(Identifier, where_names)),
        SQL(', ').join(map(Placeholder, where_names))
    ]

    if select_cols:
        template_query = "SELECT {} FROM {} WHERE ({}) = ({})"
        format_values = [
                            SQL(', ').join(map(Identifier, select_cols)),
                        ] + format_values
    else:
        template_query = "SELECT * FROM {} WHERE ({}) = ({})"

    query = SQL(template_query).format(
        *format_values
    ).as_string(conn)

    rows = _query_get(
        conn,
        query,
        where_dict
    )

    return rows


def _exists(conn: psycopg.connection, where_dict: dict[str, any], tablename: str):
    return len(get_where(conn, where_dict, tablename)) > 0


@provide_conn
def exists(where_dict: dict[str, any], tablename: str):
    return _exists(conn, where_dict, tablename)


def _insert_row(conn: psycopg.connection, row_dict: dict[str, any], tablename: str):
    names = tuple(row_dict.keys())

    query = SQL("INSERT INTO {} ({}) VALUES ({});").format(
        Identifier(tablename),  # tablename
        SQL(', ').join(map(Identifier, names)),  # (col1, col2)
        SQL(', ').join(map(Placeholder, names))  # (%(col1)s, %(col1)s) -> ('val1', 'val2')
    ).as_string(conn)

    try:
        _query_set(
            conn,
            query,
            row_dict
        )
    except psycopg.errors.UniqueViolation as e:
        raise e


def _update_row(conn: psycopg.connection,
                where_dict: dict[str, any],
                set_dict: dict[str, any],
                tablename: str):
    where_names = tuple(where_dict.keys())
    set_names = tuple(set_dict.keys())

    # This is done to avoid duplicate placeholder names in template query:
    # UPDATE table SET "col1" = %(set_col1)s WHERE ("col1", "col2") = (%(where_col1)s, %(where_col2)s)
    prefixed_where_dict = prefix_keys(where_dict, 'where_')
    prefixed_set_dict = prefix_keys(set_dict, 'set_')

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
    query = SQL(template_query).format(
        Identifier(tablename),  # tablename     "question_answer"
        SQL(', ').join(map(Identifier, set_names)),  # set columns   (col3, col4)
        SQL(', ').join(map(Placeholder, prefixed_set_names)),  # set values    ('val1', 'val2')
        SQL(', ').join(map(Identifier, where_names)),  # where columns (col1, col2)
        SQL(', ').join(map(Placeholder, prefixed_where_names))  # where values  (%s, %s)
    ).as_string(conn)

    placeholder_values = {**prefixed_set_dict, **prefixed_where_dict}

    _query_set(
        conn,
        query,
        placeholder_values
    )


@provide_conn
def update_or_insert_row(conn: psycopg.connection,
                         where_dict: dict[str, any],
                         set_dict: dict[str, any],
                         tablename: str):
    # Ensure that full row values as passed neither in filter_dict nor set_dict
    # columns_set = ...
    # assert set(where_dict).union(set(set_dict)) == columns_set

    if _exists(conn, where_dict, tablename):
        print(f"ROW {where_dict} IS UPDATED")
        _update_row(conn, where_dict, set_dict, tablename)
    else:
        row_dict = {**where_dict, **set_dict}

        print(f"ROW {row_dict} IS CREATED")
        _insert_row(conn, row_dict, tablename)


if __name__ == "__main__":
    conn = _psql_conn()

    # answers_df = build_answers_df()
    # print(answers_df)

    # questions_list = get_questions_names()
    # print(questions_list)

    # "UPDATE {tablename} SET answer_text = '66664' WHERE (day_fk, question_fk) = ('2023-02-23', 'weight')"
    _update_row(
        conn,
        {'day_fk': '2023-02-23', 'question_fk': 'weight'},
        # {'answer_text': '2345'},
        {'answer_text': 'new_2345'},
        'question_answer'
    )

    _insert_row(
        conn,
        {'day_fk': '2023-02-24', 'question_fk': 'x_small'},
        'question_answer'
    )

    update_or_insert_row(
        conn,
        {'day_fk': '2023-02-25', 'answer_text': 'walkn1'},
        {'question_fk': 'vegetables_eat'},
        'question_answer'
    )
