import datetime
from dataclasses import dataclass

import icalendar
from icalendar import (
    Calendar,
    Event,
)

from src.conversations.ask_constants import (
    EVENT_DURABLE_CHOICE_END,
    EVENT_DURABLE_CHOICE_START,
)
from src.tables.answer import (
    AnswerDB,
)
from src.tables.event import (
    EventDB,
)
from src.utils import DEFAULT_TZ


@dataclass(frozen=True)
class CalEventDC:
    # name: str
    event_obj: EventDB

    start_dt: datetime.datetime
    end_dt: datetime.datetime

    def ical_event(self) -> icalendar.Event:
        event = Event()
        # event.add("summary", self.summary)
        event.add("summary", self.event_obj.name)
        # if self.desc:
        #     event.add("description", self.desc)
        event.add("dtstart", self.start_dt.replace(tzinfo=DEFAULT_TZ))
        event.add("dtend", self.end_dt.replace(tzinfo=DEFAULT_TZ))

        return event


def gen_calendar_events_from_db_event(answers: list[AnswerDB]) -> list[CalEventDC]:
    cal_events_list: list[CalEventDC] = []

    tmp_event_start_timestamps: dict[str, datetime] = {}
    for answer_db in answers:
        if answer_db.event:
            event_db = answer_db.event

            if answer_db.text == EVENT_DURABLE_CHOICE_START:
                tmp_event_start_timestamps[event_db.name] = answer_db.get_timestamp()
            elif answer_db.text == EVENT_DURABLE_CHOICE_END:
                start_event_timestamp: datetime.datetime | None = tmp_event_start_timestamps.pop(
                    event_db.name, None
                )
                if start_event_timestamp:
                    cal_event = CalEventDC(
                        event_obj=event_db,
                        start_dt=start_event_timestamp,
                        end_dt=answer_db.get_timestamp(),
                    )
                    cal_events_list.append(cal_event)
    return cal_events_list


def gen_ics_from_answers_db(answers: list[AnswerDB]) -> bytes:
    cal_events = gen_calendar_events_from_db_event(answers)

    cal = Calendar()
    for e in cal_events:
        cal.add_component(e.ical_event())

    ics_file_bytes = cal.to_ical()
    return ics_file_bytes
