import datetime
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

ALIGN_NAME_PREFIX_LEN = 7


@dataclass(frozen=True)
class GeneratedMetricEvent:
    target_event_name: str

    custom_dt_start_add: datetime.timedelta = datetime.timedelta(0)
    custom_dt_end_add: datetime.timedelta = datetime.timedelta(0)

    @property
    def name(self):
        raise NotImplementedError

    def get_value(self, answers: list[AnswerDB]):
        raise NotImplementedError


@dataclass(frozen=True)
class CumulativeDurationGenMetric(GeneratedMetricEvent):
    @property
    def name(self):
        prefix = "[CUM]"

        return f"{prefix:{ALIGN_NAME_PREFIX_LEN}} {self.target_event_name}"

    def get_value(self, answers: list[AnswerDB]) -> datetime.timedelta:
        return self.cumulative_event_duration(answers)

    def cumulative_event_duration(self, answers: list[AnswerDB]) -> datetime.timedelta:
        sum_timedelta: datetime.timedelta = datetime.timedelta(0)

        cal_events = gen_calendar_events_from_db_event(answers)

        for c_event in cal_events:
            if c_event.ascii_name() == self.target_event_name:
                duration_delta = c_event.end_dt - c_event.start_dt
                sum_timedelta += duration_delta

        return sum_timedelta


@dataclass(frozen=True)
class FirstOnDayGenMetric(GeneratedMetricEvent):
    text_match: str | None = None

    @property
    def name(self):
        prefix = "[FIRST]"

        s = f"{prefix:<{ALIGN_NAME_PREFIX_LEN}} {self.target_event_name}"

        if self.text_match:
            s += f" ({self.text_match})"

        return s

    def __repr__(self):
        return self.name

    def get_value(self, answers: list[AnswerDB]) -> datetime.datetime:
        return self.first_event_occurrence(answers)

    def first_event_occurrence(self, answers: list[AnswerDB]) -> datetime.datetime:
        for answer in answers:
            if answer.event:
                if answer.event.ascii_name() == self.target_event_name:
                    if self.text_match:
                        if self.text_match == answer.text:
                            return answer.get_timestamp()


SLEEP_DEFAULT_KWARGS = {
    "custom_dt_start_add": datetime.timedelta(hours=-3),  # from 21:00 of prev day
    "custom_dt_end_add": datetime.timedelta(hours=-10),  # till 14:00
}


# TODO Think of moving to 'generated_metric' DB table
class GeneratedMetricsEnum(MyEnum):
    SLEEP_START = FirstOnDayGenMetric("sleep", text_match="start", **SLEEP_DEFAULT_KWARGS)
    SLEEP_END = FirstOnDayGenMetric("sleep", text_match="end", **SLEEP_DEFAULT_KWARGS)

    SLEEP_DURATION = CumulativeDurationGenMetric("sleep", **SLEEP_DEFAULT_KWARGS)
    AT_BED_DURATION = CumulativeDurationGenMetric("at_bed", **SLEEP_DEFAULT_KWARGS)


def get_gen_metrics_event_df(
    db_cache: UserDBCache,
    gen_metrics_event: list[GeneratedMetricEvent],
) -> pd.DataFrame:
    days: list[datetime.date] = sorted(db_cache.answers_days_set)

    df = pd.DataFrame(columns=days, index=list(map(lambda x: x.name, gen_metrics_event)))

    for day in days:
        day_start = datetime.datetime.combine(date=day, time=datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)

        for metric in gen_metrics_event:
            start_dt = day_start + metric.custom_dt_start_add
            end_dt = day_end + metric.custom_dt_end_add

            target_answers = list(
                filter(lambda x: start_dt < x.get_timestamp() < end_dt, db_cache.answers)
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
                raise Exception(
                    f"Metric '{metric.name}': metric_value of unhandled type: {type(metric_value)}"
                )

            df[day][metric.name] = metric_value_str

    return df
