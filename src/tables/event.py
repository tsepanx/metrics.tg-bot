from dataclasses import dataclass

from src.orm.base import ColumnDC
from src.orm.dataclasses import (
    BackForeignKeyRelation,
    ForeignKeyRelation,
    Table,
)
from src.tables.event_text_prefix import (
    EventPrefixDB,
)
from src.tables.tg_user import (
    TgUserDB,
)
from src.utils import MyEnum


class EventFKs(MyEnum):
    USER_ID = ForeignKeyRelation(TgUserDB, "user_id", "user_id")
    BACK_EVENT_PREFIX = BackForeignKeyRelation(
        EventPrefixDB, other_column="event_fk", my_column="pk"
    )


@dataclass(frozen=True, slots=True)
class EventDB(Table):
    pk: int

    user_id: int  # ForeignKey: 'TgUserDB'

    name: str
    order_by: str

    type: str

    # List of prefixes back-referencing this entry
    @property
    def prefixes_list(self) -> list[EventPrefixDB] | None:
        return self.get_back_fk_value(EventFKs.BACK_EVENT_PREFIX.value)

    def sub_dirs(self, cur_subprefix: list[str]) -> list[str]:
        text_choices_set = set()

        for pref in self.prefixes_list:
            if not cur_subprefix:
                text = pref.path_dirs()[0]
                text_choices_set.add(text)
            else:
                if pref.is_subpath(cur_subprefix):
                    relative_path: list[str] = pref.path_dirs()[len(cur_subprefix) :]
                    if relative_path:
                        text = relative_path[0]
                        text_choices_set.add(text)

        return sorted(text_choices_set)

    @classmethod
    def select_all(cls):
        return cls.select(
            join_on_fkeys=True,
            where_clauses={
                ColumnDC(table_name=cls.Meta.tablename, column_name="is_activated"): True
            },
            order_by_columns=[ColumnDC(table_name=cls.Meta.tablename, column_name="order_by")],
        )

    class Meta(Table.Meta):
        foreign_keys = EventFKs.values_list()
        tablename = "event"


if __name__ == "__main__":
    objs = EventDB.select(
        where_clauses={ColumnDC(table_name="event", column_name="pk"): 1},
        order_by_columns=[ColumnDC(column_name="order_by")],
    )
    print(objs)
