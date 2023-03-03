from dataclasses import dataclass

from src.tables.event import (
    EventDB,
)

# @dataclass(frozen=True, slots=True)
# class LastingEventDB(EventDB):
#     is_started: bool
#
#     class Meta(EventDB.Meta):
#         # foreign_keys = [
#         #     ForeignKeyRelation(TgUserDB, "user_id", "user_id")
#         # ]
#         tablename = "lasting_event"
