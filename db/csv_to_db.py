import datetime

import psycopg

from questions import questions_objects

from db import _psql_conn, _exists, _query_change


def answers_df_to_db(conn: psycopg.connection):
    import pandas as pd

    fname = 'answers_df_backups/325805942.csv'
    df = pd.read_csv(fname, index_col=0)

    cols = list(df.columns)
    index = list(df.index)

    for day_str in cols:
        for i in range(len(index)):
            col = df[day_str]
            # print('{:20} {:20} {:10}'.format(day, index[i], col[i]))

            question_name: str = index[i]
            answer_value: str | None = col[i]

            pk = (
                datetime.date.fromisoformat(day_str),
                question_name
            )
            is_exists = _exists(
                conn,
                pk,
                'SELECT day_fk, question_fk FROM question_answer'
            )

            if is_exists:
                print('{:20} {:20}'.format('PK EXISTS', str(pk)))
            else:
                print('{:20} {:20}'.format('=== INSERTING', str(pk)))

                if pd.isnull(answer_value):
                    answer_value = None

                _query_change(
                    conn,
                    "INSERT INTO question_answer(day_fk, question_fk, answer_text) VALUES (%s, %s, %s);",
                    (day_str, question_name, answer_value)
                )


def questions_list_to_db(cursor):
    for q in questions_objects:
        cursor.execute(
            "INSERT INTO question(name, fulltext, suggested_answers_list, type_id) VALUES (%s, %s, %s, %s);",
            (q.name, q.text, q.inline_keyboard_answers, 1)
        )


if __name__ == "__main__":
    conn = _psql_conn()

    # questions_list_to_db()
    answers_df_to_db(conn)

    conn.commit()
    conn.close()
