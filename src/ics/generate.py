import datetime
import logging
from dataclasses import dataclass

import icalendar
from icalendar import (
    Calendar,
    Event,
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
        # event.add('dtstamp', datetime(2022, 10, 24, 0, 10, 0, tzinfo=pytz.utc))

        # organizer = vCalAddress('MAILTO:hello@example.com')
        # organizer.params['cn'] = vText('Sir Jon')
        # organizer.params['role'] = vText('CEO')
        # event['organizer'] = organizer
        # event['location'] = vText(LOCATION)

        return event


def gen_calendar_ics(events: list[CalEventDC]) -> bytes:
    cal = Calendar()
    for e in events:
        cal.add_component(e.ical_event())

    return cal.to_ical()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    cal_events_list: list[CalEventDC] = []

    from src.user_data import (
        UserDBCache,
    )

    db_cache = UserDBCache()

    tmp_event_start_timestamps: dict[str, datetime] = {}
    for answer_db in db_cache.answers:
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

    cal_str = gen_calendar_ics(cal_events_list)

    f = open("example.ics", "wb")
    f.write(cal_str)
    f.close()
