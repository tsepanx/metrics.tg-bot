import datetime
import logging
from dataclasses import dataclass

import pandas as pd

from src.ics.generate import (
    gen_calendar_events_from_db_event,
)
from src.tables.answer import (
    AnswerDB,
)
from src.user_data import (
    UserDBCache,
)
from src.utils import (
    MyEnum,
    format_time,
    format_timedelta,
)

ALIGN_NAME_PREFIX_LEN = 10

SLEEP_DEFAULT_KWARGS = {
    "custom_dt_start_add": datetime.timedelta(hours=-3),  # from 21:00 of prev day
    "custom_dt_end_add": datetime.timedelta(hours=-10),  # till 14:00
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedMetricEvent:
    name: str

    target_event_id: int | None = None
    target_event_name: str | None = None

    custom_dt_start_add: datetime.timedelta = datetime.timedelta(0)
    custom_dt_end_add: datetime.timedelta = datetime.timedelta(0)

    prefix = "[PLN]"

    @property
    def fullname(self):
        return f"{self.prefix:{ALIGN_NAME_PREFIX_LEN}}" + self.name

    def get_value(self, answers: list[AnswerDB]):
        raise NotImplementedError

    def __repr__(self):
        return self.fullname


@dataclass(frozen=True)
class CumulativeDurationGenMetric(GeneratedMetricEvent):
    prefix = "[CUM]"

    def get_value(self, answers: list[AnswerDB]) -> datetime.timedelta | None:
        return self.cumulative_event_duration(answers)

    @staticmethod
    def cumulative_event_duration(matched_answers: list[AnswerDB]) -> datetime.timedelta | None:
        sum_timedelta: datetime.timedelta = datetime.timedelta(0)

        cal_events = gen_calendar_events_from_db_event(matched_answers)

        for c_event in cal_events:
            duration_delta = c_event.end_dt - c_event.start_dt
            sum_timedelta += duration_delta

        return sum_timedelta


@dataclass(frozen=True)
class CumulativeIntAnswersGenMetric(GeneratedMetricEvent):
    prefix = "[CUM INT]"

    def get_value(self, answers: list[AnswerDB]) -> int:
        return self.cumulative_event_answers_int(answers)

    @staticmethod
    def cumulative_event_answers_int(matched_answers: list[AnswerDB]) -> int:
        sum_val: int = 0

        for answer in matched_answers:
            try:
                sum_val += int(answer.text)
            except (ValueError, TypeError):
                continue

        return sum_val


@dataclass(frozen=True)
class FirstOnDayGenMetric(GeneratedMetricEvent):
    text_match: str | None = None

    prefix = "[FIRST]"

    @property
    def fullname(self):
        s = super().fullname

        if self.text_match:
            s += f" ({self.text_match})"

        return s

    def get_value(self, answers: list[AnswerDB]) -> datetime.datetime | None:
        return self.first_event_occurrence(answers)

    def first_event_occurrence(self, matched_answers: list[AnswerDB]) -> datetime.datetime | None:
        for answer in matched_answers:
            if self.text_match:
                if self.text_match == answer.text:
                    return answer.get_timestamp()


# TODO Think of moving to 'generated_metric' DB table
class GeneratedMetricsEnum(MyEnum):
    SLEEP_START = FirstOnDayGenMetric(
        target_event_id=46, name="sleep", text_match="start", **SLEEP_DEFAULT_KWARGS
    )
    SLEEP_END = FirstOnDayGenMetric(
        target_event_id=46, name="sleep", text_match="end", **SLEEP_DEFAULT_KWARGS
    )

    SLEEP_DURATION = CumulativeDurationGenMetric(
        target_event_id=46, name="sleep", **SLEEP_DEFAULT_KWARGS
    )
    AT_BED_DURATION = CumulativeDurationGenMetric(
        target_event_id=25, name="at_bed", **SLEEP_DEFAULT_KWARGS
    )

    KESHIY_SUM = CumulativeIntAnswersGenMetric(target_event_id=7, name="keshiuy")


def get_gen_metrics_event_df(
    db_cache: UserDBCache,
    gen_metrics_event: list[GeneratedMetricEvent],
) -> pd.DataFrame:
    days: list[datetime.date] = sorted(db_cache.answers_days_set)

    df = pd.DataFrame(columns=days, index=list(map(lambda x: x.fullname, gen_metrics_event)))

    for day in days:
        day_start = datetime.datetime.combine(date=day, time=datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)

        for metric in gen_metrics_event:
            start_dt = day_start + metric.custom_dt_start_add
            end_dt = day_end + metric.custom_dt_end_add

            bound_by_dt = lambda x: start_dt < x.get_timestamp() < end_dt

            def match_answer(answer: AnswerDB) -> bool:
                if answer.event:
                    if metric.target_event_id:
                        return metric.target_event_id == answer.event.pk
                    if metric.target_event_name:
                        return metric.target_event_name == answer.event.ascii_lower_name()
                    raise Exception(
                        "You need to either specify metric.target_event_name or metric.target_event_id"
                    )
                return False

            target_answers = list(
                filter(lambda x: bound_by_dt(x) and match_answer(x), db_cache.answers)
            )

            metric_value = metric.get_value(target_answers)

            if isinstance(metric_value, datetime.datetime):
                metric_value_str = format_time(metric_value.time())
            elif isinstance(metric_value, datetime.timedelta):
                metric_value_str = format_timedelta(metric_value)
            elif isinstance(metric_value, str):
                metric_value_str = metric_value
            elif metric_value is None:
                metric_value_str = ""
            else:
                metric_value_str = str(metric_value)
                logger.info(
                    f"Metric '{metric.name}': metric_value of unhandled type: {type(metric_value)}"
                )

            index = metric.fullname
            df[day][index] = metric_value_str

    return df
