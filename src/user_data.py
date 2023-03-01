import datetime
from typing import Sequence

import pandas as pd

from src import orm
from src.answer import AnswerDB
from src.question import QuestionDB


class AskingState:
    # include_questions: list[QuestionDB] | None
    asking_day: str

    cur_id_ind: int
    cur_answers: list[str | None]

    def __init__(self, include_qnames: list, asking_day: str):
        self.asking_day = asking_day

        self.cur_id_ind = 0
        self.cur_answers = [None for _ in range(len(include_qnames))]
        # self.include_questions = orm.get_questions_with_type_fk(include_qnames)

    def get_current_question(self) -> QuestionDB:
        if not self.include_questions:
            raise Exception

        return self.include_questions[self.cur_id_ind]


class UserData:
    state: AskingState | None
    answers_df: pd.DataFrame | None
    # questions_names: list[str] | None

    def __init__(self):
        self.state = None  # AskingState(None)
        self.answers_df = None
        self.questions_names = None

    # def reload_answers_df_from_db(self, cols: Sequence[str] | None = None):
    #     if cols:
    #         assert self.answers_df is not None
    #
    #         new_cols = orm.build_answers_df(days_range=cols)
    #
    #         assign_dict = {cols[i]: new_cols.iloc[:, 0] for i in range(len(cols))}
    #         self.answers_df = self.answers_df.assign(**assign_dict)
    #         self.answers_df = sort_answers_df_cols(self.answers_df)
    #     else:
    #         self.answers_df = orm.build_answers_df()

    # def reload_qnames(self):
    #     self.questions_names = orm.get_ordered_questions_names()


class UserDBCache:
    questions: list[QuestionDB] = None
    answers: list[AnswerDB] = None

    def __init__(self):
        if not self.questions or not self.answers:
            self.reload_all()

    def reload_all(self):
        self.questions = QuestionDB.select_all()
        self.answers = AnswerDB.select_all()

    @property
    def question_names(self) -> list[str]:
        return list(map(lambda x: x.name, self.questions))

    def question_answers_df(self, include_empty_cols=False) -> pd.DataFrame:
        df = pd.DataFrame()

        # days = sorted(set(map(lambda x: x.date.isoformat(), self.answers)))

        # <day (date)> : tuple(<question_name>, <answer_text>)
        day_answers_mapping: dict[datetime.date, list[tuple[str, str]]] = {}

        for answer in self.answers:
            if answer.question:
                if not day_answers_mapping.get(answer.date, None):
                    day_answers_mapping[answer.date] = []

                day_answers_mapping[answer.date].append((answer.question.name, answer.text))

        for day in day_answers_mapping:
            qnames_and_texts = day_answers_mapping[day]
            day_col = pd.DataFrame(qnames_and_texts).set_index(0)

            if not include_empty_cols:
                if day_col.isnull().all().bool():
                    continue

            df = df.assign(**{day.isoformat(): day_col})

        return df


if __name__ == "__main__":
    uc = UserDBCache()
    df = uc.question_answers_df()

    print(df)