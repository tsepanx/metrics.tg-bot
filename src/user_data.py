import datetime

import pandas as pd

from src.orm.dataclasses import ForeignKeyRelation
from src.tables.answer import AnswerDB, AnswerType
from src.tables.event import EventDB
from src.tables.question import QuestionDB


class UserDBCache:
    questions: list[QuestionDB] | None = None
    events: list[EventDB] | None = None
    answers: list[AnswerDB] | None = None

    def __init__(self):
        if not self.questions or not self.answers:
            self.reload_all()

    def reload_all(self):
        self.questions = QuestionDB.select_all()
        self.events = EventDB.select_all()
        self.answers = AnswerDB.select_all()

    def questions_names(self) -> list[str]:
        return list(map(lambda x: x.name, self.questions))

    def events_names(self) -> list[str]:
        return list(map(lambda x: x.name, self.events))

    def questions_answers_df(self, include_empty_cols=False) -> pd.DataFrame:
        # answers_type.value: ForeignKeyRelation
        # answers_type.name: str

        # if answers_type is AnswerType.EVENT:
        #     index = self.events_names()
        # elif answers_type is AnswerType.QUESTION:
        index = self.questions_names()
        # else:
        #     raise Exception

        df = pd.DataFrame(index=index)

        # <day (date)> : tuple(<question_name>, <answer_text>)
        day_answers_mapping: dict[datetime.date, list[tuple[str, str]]] = {}

        for answer in self.answers:
            # One of QuestionDB / EventDB

            # fk_column: str = AnswerType.QUESTION.value.from_column
            # answer_fk_object = answer.get_fk_value(fk_column)

            # if answer_fk_object:
            if answer.question:
                if not day_answers_mapping.get(answer.date, None):
                    day_answers_mapping[answer.date] = []

                # if answers_type is AnswerType.EVENT:
                #     # answer_text = f"({answer.time} {answer.text})"
                #     answer_text = (answer.time.isoformat(), answer.text)
                # elif answers_type is AnswerType.QUESTION:
                answer_text = answer.text
                # else:
                #     raise Exception

                day_answers_mapping[answer.date].append((answer.question.name, answer_text))

        for day in day_answers_mapping:
            qnames_and_texts = day_answers_mapping[day]
            day_col = pd.DataFrame(qnames_and_texts).set_index(0)

            if not include_empty_cols:
                if day_col.isnull().all().bool():
                    continue

            df = df.assign(**{day.isoformat(): day_col})

        return df

    def events_answers_df(self, for_day: datetime.date = datetime.date.today()) -> pd.DataFrame:
        """
        A table consists of only 1 column
        Each row format is described as:
            Index   | Value
            <time>  | tuple(<event.name>, <answer_text>)
        """

        event_answers = sorted(filter(lambda x: x.event is not None, self.answers), key=lambda x: x.time)

        row_list = list(map(lambda x: [x.time, (x.event.name, x.text)], event_answers))
        df = pd.DataFrame(row_list).set_index(0)
        df.columns = [for_day]
        return df


class AskingState:
    include_questions: list[QuestionDB] | None
    asking_day: datetime.date

    cur_i: int
    cur_answers: list[str | None]

    def __init__(self, include_questions: list[QuestionDB], asking_day: datetime.date):
        self.asking_day = asking_day

        self.cur_i = 0
        self.cur_answers = [None for _ in range(len(include_questions))]
        self.include_questions = include_questions

    def get_current_question(self) -> QuestionDB:
        if not self.include_questions:
            raise Exception

        return self.include_questions[self.cur_i]


class UserData:
    state: AskingState | None
    db_cache: UserDBCache

    def __init__(self):
        self.state = None  # AskingState(None)
        self.db_cache = UserDBCache()


if __name__ == "__main__":
    uc = UserDBCache()
    df = uc.events_answers_df()

    print(df)
