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
    Placeholder, Composed,
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


def get_where(
        tablename: str,
        # select_cols: Sequence[str] | None = None,
        select_cols: dict[str, Sequence[str]] | None = None,
        join_dict: dict[str, tuple[str, str]] | None = None,
        where_dict: dict[str, Any] | None = None,
        order_by: Sequence[str] | None = None,
) -> Sequence:
    """
    Common parametrized function to execute "SELECT" clause
        possibly with "WHERE", "JOIN ON", "ORDER BY" clauses

    @param tablename:
        name of table from which to SELECT

    @param select_cols:
        Which columns to select from each of joined tables.

        Each key-value pair is described as:
            <table>         : (<columns_to_select>)
        F.e.
        {
            "question"      : ("pk", "name", "type_id"),
            "question_type" : ("pk", "name", "notation")
        }

    @param join_dict:
        Each key-value pair is described as:
            <table_to_join> : (<from_col>, <to_col>)
        F.e.
            {"question_type" : ("type_id",  "pk")}

    @param where_dict:
        A dict specifying key-value pairs for WHERE clause:
            <col_name>  :  <col_value>

    @param order_by:
        List of columns, by which to ORDER BY

    @return:
        List of rows, each length of @param<select_cols>, consisting columns values
    """

    # TODO add availability for "WHERE col1 IN (1, 2)" clause
    # TODO needed to search dict values for list, and add additional query string for those pairs

    format_list = []
    template_query = ""

    if select_cols:
        template_query += "SELECT {} FROM {}"

        def colnames_with_tablename(key_value: [str, Sequence[str]]) -> Composed:
            """
            Build comma (,) separated list of "table"."colname" for given table and corresponding columns
            This function is applied to every key-value pair dict_item of "select_cols" dict

            @param key_value:
                ( <tablename> , [<columns_names>] )
            """
            select_from_tablename, select_columns = key_value

            result_columns_identifiers = []

            for column in select_columns:
                single_identifier = SQL(".").join(map(Identifier, [
                    select_from_tablename, column
                ]))
                result_columns_identifiers.append(single_identifier)

            return SQL(", ").join(result_columns_identifiers)

        format_list.extend([
            SQL(", ").join(
                map(colnames_with_tablename, select_cols.items())
                # map(Identifier, select_cols)
                # Identifier ( "question"."col" )
            )
        ])
    else:
        template_query += "SELECT * FROM {}"

    format_list.append(
        Identifier(tablename)
    )

    if join_dict:
        # join_dict = {
        #     "table2": ["table.col", "table2.col"]
        # }

        for join_tablename in join_dict:
            from_col, to_col = join_dict[join_tablename]
            # template_query += "JOIN question_type ON question.type_id = question_type.pk;"
            # template_query += "JOIN {question_type} ON {question}.{type_id} = {question_type}.{pk}"
            # template_query += f"JOIN {join_tablename} ON {tablename}.{from_col} = {join_tablename}.{to_col}"
            template_query += " JOIN {} ON {}.{} = {}.{}"

            format_list.extend([
                Identifier(join_tablename),
                Identifier(tablename),
                Identifier(from_col),
                Identifier(join_tablename),
                Identifier(to_col)
            ])

    if where_dict:
        template_query += " WHERE ({}) = ({})"
        where_names = tuple(where_dict.keys())

        format_list.extend([
            SQL(", ").join(map(Identifier, where_names)),
            SQL(", ").join(map(Placeholder, where_names)),
        ])

    if order_by:
        template_query += " ORDER BY {}"
        format_list.append(
            SQL(", ").join(map(Identifier, order_by))
        )

    query = SQL(template_query).format(*format_list).as_string(get_psql_conn())

    return _query_get(query=query, params=where_dict)


def _exists(where_dict: dict[str, Any], tablename: str):
    return len(get_where(tablename, where_dict)) > 0


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
