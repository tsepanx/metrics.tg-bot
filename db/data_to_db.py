from questions import questions_objects
import psycopg2


def exists(pk: tuple, query: str):
    assert query.lower().startswith('select')
    cursor.execute(query)

    res = cursor.fetchall()
    res = list(map(lambda x: x[0], res))

    # r = res[0]
    for r in res:
        r = r[1:]
        r = r[:-1]
        rs = r.split(',')

        eq = list(pk) == list(rs)

        if eq:
            return True

    return False


def answers_df_to_db(cursor):
    import pandas as pd

    fname = 'answers_df_backups/325805942.csv'

    df = pd.read_csv(fname, index_col=0)

    cols = list(df.columns)
    index = list(df.index)

    for day in cols:
        for i in range(len(index)):
            col = df[day]
            # print('{:20} {:20} {:10}'.format(day, index[i], col[i]))

            day: str
            question_name: str = index[i]
            answer_value: str | None = col[i]

            pk = (day, question_name)
            is_exists = exists(
                pk,
                'SELECT (day_fk, question_fk) FROM question_answer'
            )

            if is_exists:
                print('{:20} {:20}'.format('PK EXISTS', str(pk)))
            else:
                print('{:20} {:20}'.format('=== INSERTING', str(pk)))

                if pd.isnull(answer_value):
                    answer_value = None

                cursor.execute(
                    "INSERT INTO question_answer(day_fk, question_fk, answer_text) VALUES (%s, %s, %s);",
                    (day, question_name, answer_value)
                )


def questions_list_to_db(cursor):
    for q in questions_objects:
        cursor.execute(
            "INSERT INTO question(name, fulltext, suggested_answers_list, type_id) VALUES (%s, %s, %s, %s);",
            (q.name, q.text, q.inline_keyboard_answers, 1)
        )


if __name__ == "__main__":
    conn = psql_conn()
    cursor = conn.cursor()

    # questions_list_to_db()
    answers_df_to_db(cursor)

    conn.commit()
    conn.close()
