import datetime
import logging
from dataclasses import dataclass
from typing import Any, TypeVar

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
class NameableMixin:
    name: str

    prefix = "[PLN]"

    @property
    def fullname(self):
        return f"{self.prefix:{ALIGN_NAME_PREFIX_LEN}}" + self.name

    def __repr__(self):
        return self.fullname


@dataclass(frozen=True)
class ValueMixin:
    def value_on_day(self, all_answers: list[AnswerDB], on_day: datetime.date) -> str:
        raise NotImplementedError


MetricType = TypeVar("MetricType", ValueMixin, NameableMixin)


@dataclass(frozen=True)
class GeneratedMetricEvent(NameableMixin, ValueMixin):
    target_event_id: int | None = None
    target_event_name: str | None = None

    custom_dt_start_add: datetime.timedelta = datetime.timedelta(0)
    custom_dt_end_add: datetime.timedelta = datetime.timedelta(0)

    def __match_answer(self, answer: AnswerDB) -> bool:
        if answer.event:
            if self.target_event_id:
                return self.target_event_id == answer.event.pk
            if self.target_event_name:
                return self.target_event_name == answer.event.ascii_lower_name()
            raise Exception(
                "You need to either specify metric.target_event_name or metric.target_event_id"
            )
        return False

    def __filter_answers(self, all_answers: list[AnswerDB], on_day: datetime.date):
        day_start = datetime.datetime.combine(date=on_day, time=datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)

        # metric: Union[ValueMixin, NameableMixin]
        # for metric in gen_metrics_event:
        start_dt = day_start + self.custom_dt_start_add
        end_dt = day_end + self.custom_dt_end_add

        bound_by_dt = lambda x: start_dt < x.get_timestamp() < end_dt
        apply_filter = lambda x: bound_by_dt(x) and self.__match_answer(x)

        return list(filter(apply_filter, all_answers))

    # @staticmethod
    def _value_on_target_answers(self, target_answers: list[AnswerDB]):
        raise NotImplementedError

    def value_on_day(self, all_answers: list[AnswerDB], on_day: datetime.date):
        target_answers = self.__filter_answers(all_answers, on_day)
        metric_value = self._value_on_target_answers(target_answers)

        return metric_value


@dataclass(frozen=True)
class CumulativeDurationGenMetric(GeneratedMetricEvent):
    prefix = "[CUM]"

    # @staticmethod
    def _value_on_target_answers(self, target_answers: list[AnswerDB]) -> datetime.timedelta | None:
        sum_timedelta: datetime.timedelta = datetime.timedelta(0)

        cal_events = gen_calendar_events_from_db_event(target_answers)

        for c_event in cal_events:
            duration_delta = c_event.end_dt - c_event.start_dt
            sum_timedelta += duration_delta

        return sum_timedelta


@dataclass(frozen=True)
class SumIntAnswersGenMetric(GeneratedMetricEvent):
    prefix = "[SUM INT]"

    # @staticmethod
    def _value_on_target_answers(self, target_answers: list[AnswerDB]) -> int:
        sum_val: int = 0

        for answer in target_answers:
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

    def _value_on_target_answers(self, matched_answers: list[AnswerDB]) -> datetime.datetime | None:
        for answer in matched_answers:
            if self.text_match:
                if self.text_match == answer.text:
                    return answer.get_timestamp()


@dataclass(frozen=True)
class DependentGeneratedMetric(NameableMixin, ValueMixin):
    """
    Depends on other's metrics values.
    Represents any relations between `GeneratedMetrics` on given day, i.e. '-', '+'

    TODO Add ability to depend on `Question` also (needs to rewrite forming table logic)
    """

    metrics_list: list[GeneratedMetricEvent]

    prefix = "[FIRST]"

    def value_on_day(self, all_answers: list[AnswerDB], on_day: datetime.date):
        metrics_values = list(map(lambda x: x.value_on_day(all_answers, on_day), self.metrics_list))

        if None in metrics_values:
            return None

        return self.apply_func(metrics_values)

    @staticmethod
    def apply_func(values):
        raise NotImplementedError


@dataclass(frozen=True)
class MetricsDifference(DependentGeneratedMetric):
    prefix = "[DIFF]"

    @staticmethod
    def apply_func(values):
        assert len(values) == 2
        return values[0] - values[1]


@dataclass(frozen=True)
class MetricsAddition(DependentGeneratedMetric):
    prefix = "[PLUS]"

    @staticmethod
    def apply_func(values):
        assert len(values) == 2
        return values[0] + values[1]


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

    AT_BED_START = FirstOnDayGenMetric(
        target_event_id=25, name="at bed", text_match="start", **SLEEP_DEFAULT_KWARGS
    )
    AT_BED_END = FirstOnDayGenMetric(
        target_event_id=25, name="at bed", text_match="end", **SLEEP_DEFAULT_KWARGS
    )

    AT_BED_DURATION = CumulativeDurationGenMetric(
        target_event_id=25, name="at_bed", **SLEEP_DEFAULT_KWARGS
    )

    KESHIY_SUM = SumIntAnswersGenMetric(target_event_id=7, name="keshiuy")

    SLEEP_START_WASTE = MetricsDifference("sleep [waste]", [SLEEP_START, AT_BED_START])


def format_metric_value(metric: MetricType, metric_value: Any) -> str:
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
        logger.info(f"Metric '{metric.name}': metric_value of unhandled type: {type(metric_value)}")

    return metric_value_str


def get_gen_metrics_event_df(
    db_cache: UserDBCache,
    gen_metrics: list[MetricType],
) -> pd.DataFrame:
    days: list[datetime.date] = sorted(db_cache.answers_days_set)

    df = pd.DataFrame(columns=days, index=list(map(lambda x: x.fullname, gen_metrics)))

    for day in days:
        for metric in gen_metrics:
            metric_value = metric.value_on_day(db_cache.answers, day)
            formatted_value: str = format_metric_value(metric, metric_value)

            index = metric.fullname
            df[day][index] = formatted_value
    return df
