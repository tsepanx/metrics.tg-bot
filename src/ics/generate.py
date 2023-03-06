import datetime
from dataclasses import dataclass

import icalendar
from icalendar import (
    Calendar,
    Event,
)

from src.tables.answer import (
    AnswerDB,
)
from src.utils import DEFAULT_TZ


@dataclass
class CalEventDC:
    summary: str
    desc: str | None

    start_dt: datetime.datetime
    end_dt: datetime.datetime

    def ical_event(self) -> icalendar.Event:
        event = Event()
        event.add("summary", self.summary)
        if self.desc:
            event.add("description", self.desc)
        event.add("dtstart", self.start_dt.replace(tzinfo=DEFAULT_TZ))
        event.add("dtend", self.end_dt.replace(tzinfo=DEFAULT_TZ))

        return event


def gen_calendar_ics_str(events: list[CalEventDC]) -> bytes:
    cal = Calendar()
    for e in events:
        cal.add_component(e.ical_event())

    return cal.to_ical()


def gen_ics_from_answers_db(answers: list[AnswerDB]) -> bytes:
    cal_events_list: list[CalEventDC] = []

    tmp_event_start_timestamps: dict[str, datetime] = {}
    for answer_db in answers:
        if answer_db.event:
            event_db = answer_db.event

            if answer_db.text == "start":
                tmp_event_start_timestamps[event_db.name] = answer_db.get_timestamp()
            elif answer_db.text == "end":
                start_event_timestamp: datetime.datetime | None = tmp_event_start_timestamps.pop(
                    event_db.name, None
                )
                if start_event_timestamp:
                    cal_event = CalEventDC(
                        summary=event_db.name,
                        desc=None,
                        start_dt=start_event_timestamp,
                        end_dt=answer_db.get_timestamp(),
                    )
                    cal_events_list.append(cal_event)

    cal_str = gen_calendar_ics_str(cal_events_list)
    return cal_str
