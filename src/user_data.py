import datetime
import enum

import pandas as pd

from src.answer import AnswerDB
from src.event import EventDB
from src.question import QuestionDB


class UserDBCache:
    class AnswerEntityType(enum.Enum):
        EVENT = "event_fk"
        QUESTION = "question_fk"

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

    def _common_answers_df(self, entity_type: AnswerEntityType, include_empty_cols=False) -> pd.DataFrame:
        if entity_type is UserDBCache.AnswerEntityType.EVENT:
            index = self.events_names()
        elif entity_type is UserDBCache.AnswerEntityType.QUESTION:
            index = self.questions_names()
        else:
            raise Exception

        df = pd.DataFrame(index=index)

        # <day (date)> : tuple(<question_name>, <answer_text>)
        day_answers_mapping: dict[datetime.date, list[tuple[str, str]]] = {}

        for answer in self.answers:
            # One of QuestionDB / EventDB
            answer_fk_object = answer.get_fk_value(entity_type.value)

            if answer_fk_object:
                if not day_answers_mapping.get(answer.date, None):
                    day_answers_mapping[answer.date] = []

                if entity_type is UserDBCache.AnswerEntityType.EVENT:
                    # answer_text = f"({answer.time} {answer.text})"
                    answer_text = (answer.time.isoformat(), answer.text)
                elif entity_type is UserDBCache.AnswerEntityType.QUESTION:
                    answer_text = answer.text
                else:
                    raise Exception

                day_answers_mapping[answer.date].append((answer_fk_object.name, answer_text))

        for day in day_answers_mapping:
            qnames_and_texts = day_answers_mapping[day]
            day_col = pd.DataFrame(qnames_and_texts).set_index(0)

            if not include_empty_cols:
                if day_col.isnull().all().bool():
                    continue

            df = df.assign(**{day.isoformat(): day_col})

        return df

    def questions_answers_df(self, **kwargs) -> pd.DataFrame:
        return self._common_answers_df(
            UserDBCache.AnswerEntityType.QUESTION,
            **kwargs
        )

    def events_answers_df(self, **kwargs) -> pd.DataFrame:
        return self._common_answers_df(
            UserDBCache.AnswerEntityType.EVENT,
            **kwargs
        )


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
