from typing import Sequence

import pandas as pd

from src import orm
from src.question import QuestionDB
from src.utils import sort_answers_df_cols


class AskingState:
    include_questions: list[QuestionDB] | None
    asking_day: str

    cur_id_ind: int
    cur_answers: list[str | None]

    def __init__(self, include_qnames: list, asking_day: str):
        self.asking_day = asking_day

        self.cur_id_ind = 0
        self.cur_answers = [None for _ in range(len(include_qnames))]
        self.include_questions = orm.get_questions_with_type_fk(include_qnames)

    def get_current_question(self) -> orm.QuestionDB:
        if not self.include_questions:
            raise Exception

        return self.include_questions[self.cur_id_ind]


class UserData:
    state: AskingState | None
    answers_df: pd.DataFrame | None
    questions_names: list[str] | None

    def __init__(self):
        self.state = None  # AskingState(None)
        self.answers_df = None
        self.questions_names = None

    def reload_answers_df_from_db(self, cols: Sequence[str] | None = None):
        if cols:
            assert self.answers_df is not None

            new_cols = orm.build_answers_df(days_range=cols)

            assign_dict = {cols[i]: new_cols.iloc[:, 0] for i in range(len(cols))}
            self.answers_df = self.answers_df.assign(**assign_dict)
            self.answers_df = sort_answers_df_cols(self.answers_df)
        else:
            self.answers_df = orm.build_answers_df()

    def reload_qnames(self):
        self.questions_names = orm.get_ordered_questions_names()
