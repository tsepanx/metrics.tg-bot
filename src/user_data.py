import dataclasses
import datetime
from dataclasses import dataclass

import pandas as pd
import telegram

from src.tables.answer import (
    AnswerDB,
    AnswerType,
)
from src.tables.event import (
    EventDB,
)
from src.tables.question import (
    QuestionDB,
)
from src.utils import (
    get_now,
    get_today,
)


@dataclass
class ConversationsStorage:
    pass


@dataclass
class ASKConversationStorage(ConversationsStorage):
    day: datetime.date | None = None
    entity_type: AnswerType | None = None


@dataclass
class ASKQuestionsConvStorage(ASKConversationStorage):
    entity_type = AnswerType.QUESTION

    # day: datetime.date | None = None
    include_indices: list[int] = dataclasses.field(default_factory=list)

    cur_i: int = 0
    cur_answers: list[str | None] = None

    def current_question(self, questions: list[QuestionDB]) -> QuestionDB:
        index = self.include_indices[self.cur_i]
        return questions[index]

    def set_current_answer(self, val: str):
        self.cur_answers[self.cur_i] = val


@dataclass
class ASKEventConvStorage(ASKConversationStorage):
    entity_type = AnswerType.QUESTION

    chosen_event_index: int | None = None

    info_msg: telegram.Message | None = None

    event_name_prefix_path: list[str] | None = None
    event_time: datetime.time | None = None
    event_text: str | None = None


class UserDBCache:
    questions: list[QuestionDB] | None = None
    events: list[EventDB] | None = None
    answers: list[AnswerDB] | None = None

    question_answers_days_set: set[datetime.date] | None = set()

    LAST_RELOAD_TIME: datetime.datetime | None = None

    def __init__(self):
        if not self.questions or not self.answers:
            self.reload_all()

    def reload_all(self):
        self.LAST_RELOAD_TIME = get_now()

        self.questions = QuestionDB.select_all()
        self.events = EventDB.select_all()
        self.answers = AnswerDB.select_all()

        self.question_answers_days_set = set(
            map(lambda a: a.date, filter(lambda x: x.question is not None, self.answers))
        )

    def questions_names(self) -> list[str]:
        return list(map(lambda x: x.name, self.questions))

    def events_names(self) -> list[str]:
        return list(map(lambda x: x.name, self.events))

    def questions_answers_df(self, include_empty_cols=False) -> pd.DataFrame | None:
        index = self.questions_names()

        df = pd.DataFrame(index=index)

        # <day (date)> : tuple(<question_name>, <answer_text>)
        day_answers_mapping: dict[datetime.date, list[tuple[str, str]]] = {}

        for answer in self.answers:
            # One of QuestionDB / EventDB

            if answer.question:
                if not day_answers_mapping.get(answer.date, None):
                    day_answers_mapping[answer.date] = []

                answer_text = answer.text
                day_answers_mapping[answer.date].append((answer.question.name, answer_text))

        if not day_answers_mapping:
            return None

        for day in day_answers_mapping:
            qnames_and_texts = day_answers_mapping[day]
            day_col = pd.DataFrame(qnames_and_texts).set_index(0)

            if not include_empty_cols:
                if day_col.isnull().all().bool():
                    continue

            df[day] = day_col

        return df

    def events_answers_df(self) -> pd.DataFrame | None:
        """
        A table consists of only 1 column
        Each row format is described as:
            Index   | Value
            <time>  | tuple(<event.name>, <answer_text>)
        """

        def filter_answers(a: AnswerDB) -> bool:
            return a.event is not None and a.date == get_today()

        event_answers = sorted(filter(filter_answers, self.answers), key=lambda x: x.time)

        row_list = list(map(lambda x: [x.time, x.event.name, x.text], event_answers))

        if len(row_list) == 0:
            return None

        df = pd.DataFrame(row_list).set_index(0)
        df.columns = ("name", "text")
        return df

    def get_entity_answers_df(self, answers_entity: AnswerType):
        if answers_entity is AnswerType.QUESTION:
            # transpose_callback_data = build_transpose_callback_data(answers_entity)
            answers_df = self.questions_answers_df()
        elif answers_entity is AnswerType.EVENT:
            # transpose_callback_data = None
            answers_df = self.events_answers_df()
        else:
            raise Exception

        return answers_df


class UserData:
    conv_storage: ASKConversationStorage
    db_cache: UserDBCache

    DEBUG_SQL_OUTPUT = False
    DEBUG_ERRORS_OUTPUT = True

    def __init__(self):
        self.conv_storage = ASKConversationStorage()
        self.db_cache = UserDBCache()

    def cur_question_answer_in_db(self) -> str | None:
        assert isinstance(self.conv_storage, ASKQuestionsConvStorage)

        day = self.conv_storage.day
        question_name = self.conv_storage.current_question(self.db_cache.questions).name
        answers_df = self.db_cache.questions_answers_df()

        if answers_df is None or day not in answers_df.columns:
            return None

        existing_answer = answers_df[day][question_name]
        if pd.isnull(existing_answer):
            return None
        return existing_answer


if __name__ == "__main__":
    uc = UserDBCache()
    df = uc.events_answers_df()

    print(df)
