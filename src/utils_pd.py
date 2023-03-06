import datetime
import re

import numpy as np
import pandas as pd

from src.tables.question import (
    QuestionDB,
)


def df_to_markdown(df: pd.DataFrame, transpose=False):
    def remove_emojis_with_space_prefix(data: str) -> str:
        emojis_regex = re.compile(
            " ["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002503-\U00002BEF"  # chinese char
            "\U00002702-\U000027B0"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001f926-\U0001f937"
            "\U00010000-\U0010ffff"
            "\u2640-\u2642"
            "\u2600-\u2B55"
            "\u200d"
            "\u23cf"
            "\u23e9"
            "\u231a"
            "\ufe0f"  # dingbats
            "\u3030"
            "]+",
            re.UNICODE,
        )
        return re.sub(emojis_regex, "", data)

    if transpose:
        df = df.T

    # Replace None with np.nan for consistency
    df = df.fillna(value=np.nan)

    text = df.to_markdown(
        tablefmt="rounded_grid",
        numalign="left",
        stralign="left",
    )
    text = text.replace(" nan ", " --- ")

    with open("1.txt", "wb") as f:
        f.write(text.encode("utf-8"))

    text = remove_emojis_with_space_prefix(text)

    with open("2.txt", "wb") as f:
        f.write(text.encode("utf-8"))

    # text = text.replace("00:00:00", "0       ")
    # text = text.replace(":00:00", ":0c0   ")
    # text = text.replace(":00:00", ":0c0   ")
    # text = text.replace(":00", "   ")
    # text = text.replace(":0c0", ":00")

    # 00:00:00 -> 0
    # 06:00:00 -> 06:00
    # 12:34:00 -> 12:34

    return text


def sort_answers_df_cols(df: pd.DataFrame) -> pd.DataFrame:
    columns_order = sorted(
        df.columns,
        key=lambda x: f"_{x}" if not isinstance(x, datetime.date) else x.isoformat(),
    )
    df = df.reindex(columns_order, axis=1)
    return df


def add_questions_sequence_num_as_col(df: pd.DataFrame, questions: list[QuestionDB]):
    """
    Generate
    Prettify table look by adding questions ids to index

    Assumes given @df has "questions names" as index
    """
    sequential_numbers = []

    for index_i in df.index:
        for i, question in enumerate(questions):
            if question.name == index_i:
                # s = str(i)
                sequential_numbers.append(i)
                break

    # Setting new index column
    # df = df.reset_index()
    # df = df.drop('index', axis=1)

    # new_index_name = 'i  | name'

    # df.insert(0, new_index_name, indices)
    # df = df.set_index(new_index_name)

    df = df.copy()
    # noinspection PyTypeChecker
    df.insert(0, "i", sequential_numbers)

    return df


def merge_to_existing_column(old_col: pd.Series, new_col: pd.Series) -> pd.Series:
    """
    Merge two pd.Series objects (with same length), replacing value with new, when possible
    """
    index = old_col.index.union(new_col.index)
    res_col = pd.Series(index=index).astype(object)

    for i_str in index:
        old_val = old_col.get(i_str, None)
        new_val = new_col.get(i_str, None)

        res_val = old_val if pd.isnull(new_val) else new_val
        res_col[i_str] = res_val

    return res_col
