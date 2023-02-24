import datetime

import pandas

from db.high_level_methods import (
    get_ordered_questions_names
)
from utils import (
    merge_to_existing_column
)


def update_answers_df(
        df: pd.DataFrame,
        state: AskingState,
        sort_columns=True,
        sort_rows_by_q_index=True,
) -> pd.DataFrame:

    old_shape = df.shape

    # Ended question list
    day_index = state.asking_day

    # Create empty col if it does not exist
    if df.get(day_index) is None:
        df = df.assign(**{day_index: pd.Series()})

    qnames = get_ordered_questions_names()
    included_qnames: list[str] = list(map(
        lambda x: qnames[x],
        state.include_qnames
    ))

    new_col = pd.Series(state.cur_answers, index=included_qnames)
    # Needed to convert automatic conversion to numpy types (f.e. numpy.int64) to initial pythonic type back
    new_col = new_col.astype(object)

    res_col = merge_to_existing_column(df[day_index], new_col)

    df = df.reindex(df.index.union(included_qnames))

    if sort_columns:
        columns_order = sorted(
            df.columns,
            key=lambda x: f'_{x}' if not isinstance(x, datetime.date) else x.isoformat()
        )
        df = df.reindex(columns_order, axis=1)

    # if sort_rows_by_q_index:
    #     if 'i' not in df.columns:
    #         df = add_questions_sequence_num_as_col(df, questions_objects)
    #
    #     df = df.sort_values('i')
    #     df = df.drop('i', axis=1)

    df[day_index] = res_col

    new_shape = df.shape

    print('Updating answers_df')
    if old_shape == new_shape:
        print(f'shape not changed: {old_shape}')
    else:
        print(f'shape changed!\noldshape: {old_shape}\nnew shape: {new_shape}')

    return df