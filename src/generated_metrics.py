import datetime
from dataclasses import dataclass

import pandas as pd

from src.ics.generate import (
    gen_calendar_events_from_db_event,
)
from src.tables.answer import (
    AnswerDB,
)
from src.user_data import UserData
from src.utils import (
    format_timedelta,
)


@dataclass(frozen=True)
class GeneratedMetricEvent:
    target_event_name: str

    custom_dt_start_add: datetime.timedelta = datetime.timedelta(0)
    custom_dt_end_add: datetime.timedelta = datetime.timedelta(0)

    @property
    def name(self):
        return f"cum_{self.target_event_name}"

    def cumulative_event_duration(self, answers: list[AnswerDB]) -> datetime.timedelta:
        sum_timedelta: datetime.timedelta = datetime.timedelta(0)

        cal_events = gen_calendar_events_from_db_event(answers)

        for c_event in cal_events:
            if c_event.ascii_name() == self.target_event_name:
                duration_delta = c_event.end_dt - c_event.start_dt
                sum_timedelta += duration_delta

        return sum_timedelta


def get_gen_metrics_event_df(
    ud: UserData, gen_metrics_event: list[GeneratedMetricEvent]
) -> pd.DataFrame:
    days: list[datetime.date] = sorted(ud.db_cache.answers_days_set)

    df = pd.DataFrame(columns=days, index=list(map(lambda x: x.name, gen_metrics_event)))

    for day in days:
        day_start = datetime.datetime.combine(date=day, time=datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)

        for metric in gen_metrics_event:
            start_dt = day_start + metric.custom_dt_start_add
            end_dt = day_end + metric.custom_dt_end_add

            target_answers = list(
                filter(lambda x: start_dt < x.get_timestamp() < end_dt, ud.db_cache.answers)
            )

            # for answer in target_answers:
            cum_timedelta = metric.cumulative_event_duration(target_answers)
            df[day][metric.name] = format_timedelta(cum_timedelta)

    return df
