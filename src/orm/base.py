import enum
import os
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    Sequence,
)

import psycopg
import sqlparse
from psycopg.sql import (
    SQL,
    Composable,
    Identifier,
    Placeholder,
)

PG_DB = os.environ.get("PG_DB", "postgres")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "")

TableName = str
ValueType = Any


@dataclass(frozen=True)
class ColumnDC:
    column_name: str
    table_name: str | None = None

    def compose_by_dot(self) -> Identifier:
        # ("col") -> Composed("name")
        # ("table", "col") -> Composed("table"."name")
        if self.table_name:
            return Identifier(self.table_name, self.column_name)
        return Identifier(self.column_name)

    def underscore_notation(self) -> str:
        if not self.table_name:
            return self.column_name
        return f"{self.table_name}_{self.column_name}"

    def __repr__(self):
        return self.underscore_notation()

    def __str__(self):
        return self.underscore_notation()


class JoinTypes(enum.Enum):
    INNER = 0
    LEFT = 1
    RIGHT = 2
    FULL = 3


@dataclass(frozen=True)
class JoinByClauseDC:
    """
    @param table_name
        Name of table to JOIN

    Result subquery:
        JOIN <table_name> ON "<primary_table>"."<from_column>" "<table_name>"."<to_column>"
    """

    table_name: str
    from_column: str
    to_column: str

    join_type: JoinTypes = JoinTypes.INNER


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


def dict_cols_to_str(
        d: dict[ColumnDC, ValueType],
        prefix: str | None = None,
        column_apply_function: Callable[[ColumnDC], str] = ColumnDC.underscore_notation
) -> dict[str, Any]:
    """
    Builds new dict from old, rebuilding keys by some rule (ColumnDC -> str):
    Result type conversion:
        dict[ColumnDC, ValueType] -> dict[str, ValueType]
    """
    new_d = {}

    for column_dc in d:
        new_key = column_apply_function(column_dc)
        if prefix:
            new_key = prefix + new_key

        new_d[new_key] = d[column_dc]

    return new_d


def _query_get(query: str, params: Optional[dict | Sequence] = tuple()) -> Sequence:
    print(sqlparse.format(query, reindent=True,))
    print("Params:", params)

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


def _select(
    tablename: TableName,
    select_columns: list[ColumnDC] | None = None,
    join_clauses: list[JoinByClauseDC] | None = None,
    where_clauses: dict[ColumnDC, ValueType] | None = None,
    order_by_columns: list[ColumnDC] | None = None,
) -> Sequence:
    """
    Common parametrized function trying to fully imitate "SELECT" clause
        optionally added with "WHERE", "JOIN ON", "ORDER BY" clauses

    @param tablename: TableName (str)
        name of table goes after "FROM" clause

    @param select_columns: list[ColumnDC]
        List of columns identifiers, goes after "SELECT" clause

    @param join_clauses:
        List of "JoinByClauseDC" Dataclass, specifying single "JOIN ... ON ..." clause:

    @param where_clauses:
        Dict specifying key-value pairs for "WHERE (...) = (...)" clause:
            Format: { <col_name>: <col_value> }

    @param order_by_columns:
        List specifying columns after "ORDER BY" clause

    @return:
        List of rows, each length of @param<select_cols>, consisting of columns values
    """

    # TODO add option for "WHERE col1 IN (1, 2)" clause
    # TODO needed to search dict values for list, and add additional query string for those pairs

    format_list: list[Composable] = []
    template_query = ""

    # "SELECT" clause
    if select_columns:
        template_query += "SELECT {}"

        format_list.extend([SQL(", ").join(map(lambda x: x.compose_by_dot(), select_columns))])
    else:
        template_query += "SELECT *"

    # "FROM" clause
    template_query += " FROM {}"
    format_list.append(Identifier(tablename))

    # "JOIN" clause
    if join_clauses:
        join_clause: JoinByClauseDC
        for join_clause in join_clauses:
            # template_query += "JOIN question_type ON question.type_id = question_type.pk;"
            # template_query += "JOIN {question_type} ON {question}.{type_id} = {question_type}.{pk}"
            # template_query += f"JOIN {join_tablename} ON {tablename}.{from_col} = {join_tablename}.{to_col}"
            template_subquery = " JOIN {} ON {}.{} = {}.{}"

            if join_clause.join_type:
                if isinstance(join_clause.join_type, JoinTypes):
                    template_subquery = " {}" + template_subquery
                    format_list.append(
                        SQL(join_clause.join_type.name)
                    )

            template_query += template_subquery
            format_list.extend(
                map(
                    Identifier,
                    [
                        join_clause.table_name,
                        tablename,
                        join_clause.from_column,
                        join_clause.table_name,
                        join_clause.to_column,
                    ],
                )
            )

    # "WHERE" clause
    if where_clauses:
        template_query += " WHERE ({}) = ({})"

        where_columns: list[ColumnDC] = list(where_clauses.keys())

        where_placeholders_params: dict[str, ValueType] | None = {
            k.underscore_notation(): v for k, v in where_clauses.items()
        }

        columns_identifiers: Iterable[Identifier] = map(ColumnDC.compose_by_dot, where_columns)
        values_placeholders: Iterable[Placeholder] = map(Placeholder, where_placeholders_params.keys())

        format_list.extend(
            [
                SQL(", ").join(columns_identifiers),
                SQL(", ").join(values_placeholders),
            ]
        )
    else:
        where_placeholders_params = None

    # "ORDER BY" clause
    if order_by_columns:
        template_query += " ORDER BY {}"
        format_list.append(SQL(", ").join(map(ColumnDC.compose_by_dot, order_by_columns)))

    query = SQL(template_query).format(*format_list).as_string(get_psql_conn())

    return _query_get(query=query, params=where_placeholders_params)


def _exists(
        tablename: TableName,
        where_clauses: dict[ColumnDC, ValueType],
):
    return len(_select(tablename=tablename, where_clauses=where_clauses)) > 0


def _insert_row(
        tablename: TableName,
        row_dict: dict[ColumnDC, Any]
):
    names = tuple(row_dict.keys())

    # ColumnDC -> str placeholder
    # placeholder_apply_func = ColumnDC.underscore_notation
    placeholder_apply_func = lambda x: x.column_name

    query = (
        SQL("INSERT INTO {} ({}) VALUES ({})").format(
            # tablename
            Identifier(tablename),
            # (col1, col2)
            SQL(", ").join(map(ColumnDC.compose_by_dot, names)),
            # (%(col1)s, %(col1)s) -> ('val1', 'val2')
            SQL(", ").join(map(Placeholder, map(placeholder_apply_func, names))),
        )
        .as_string(get_psql_conn())
    )

    try:
        prefixed_row_dict = dict_cols_to_str(
            row_dict,
            prefix=None,
            column_apply_function=placeholder_apply_func
        )
        _query_set(query, prefixed_row_dict)
    except psycopg.errors.UniqueViolation as e:
        raise e


def _update_row(
        tablename: TableName,
        where_clauses: dict[ColumnDC, ValueType],
        set_dict: dict[ColumnDC, ValueType],
):
    where_names = tuple(where_clauses.keys())
    set_names = tuple(set_dict.keys())

    # This is done to avoid duplicate placeholder names in template query:
    # UPDATE table SET "col1" = %(set_col1)s WHERE ("col1", "col2") = (%(where_col1)s, %(where_col2)s)
    prefixed_where_dict = dict_cols_to_str(where_clauses, prefix="where_")
    prefixed_set_dict = dict_cols_to_str(set_dict, prefix="set_")

    prefixed_where_names = tuple(prefixed_where_dict.keys())
    prefixed_set_names = tuple(prefixed_set_dict.keys())

    if len(set_names) == 1:
        # "UPDATE {tablename} SET answer_text = '66664' WHERE (day_fk, question_fk) = ('2023-02-23', 'weight')"
        template_query = "UPDATE {} SET {} = {} WHERE ({}) = ({})"
    elif len(set_names) > 1:
        template_query = "UPDATE {} SET ({}) = ({}) col3, col4WHERE ({}) = ({})"
    else:
        raise Exception

    # query = SQL("SELECT * FROM {} WHERE ({}) = ({})").format(
    query = (
        SQL(template_query)
        .format(
            # tablename     "question_answer"
            Identifier(tablename),
            # set columns   (col3, col4)
            SQL(", ").join(map(ColumnDC.compose_by_dot, set_names)),
            # set values    ('val1', 'val2')
            SQL(", ").join(map(Placeholder, prefixed_set_names)),
            # where columns (col1, col2)
            SQL(", ").join(map(ColumnDC.compose_by_dot, where_names)),
            # where values  (%s, %s)
            SQL(", ").join(map(Placeholder, prefixed_where_names)),
        )
        .as_string(get_psql_conn())
    )

    placeholder_values = {**prefixed_set_dict, **prefixed_where_dict}

    _query_set(query, placeholder_values)


def update_or_insert_row(
        tablename: TableName,
        where_clauses: dict[ColumnDC, ValueType],
        set_dict: dict[ColumnDC, ValueType],
):
    # Ensure that full row values as passed neither in filter_dict nor set_dict
    # columns_set = ...
    # assert set(where_dict).union(set(set_dict)) == columns_set

    if _exists(tablename, where_clauses):
        _update_row(tablename, where_clauses, set_dict)
    else:
        row_dict = {**where_clauses, **set_dict}
        _insert_row(tablename, row_dict)


if __name__ == "__main__":
    pass
    # questions_list = get_questions_names()
    # print(questions_list)

    # "UPDATE {tablename} SET answer_text = '66664' WHERE (day_fk, question_fk) = ('2023-02-23', 'weight')"
    # _update_row(
    #     {"day_fk": "2023-02-23", "question_fk": "weight"},
    #     # {'answer_text': '2345'},
    #     {"answer_text": "new_2345"},
    #     "question_answer",
    # )
    #
    # _insert_row(
    #     {
    #         "day_fk": "2023-02-24",
    #         "question_fk": "x_small"
    #     },
    #     "question_answer"
    # )
    #
    # update_or_insert_row(
    #     {"day_fk": "2023-02-25", "answer_text": "walkn1"}, {"question_fk": "vegetables_eat"}, "question_answer"
    # )
