from dataclasses import dataclass

from src.orm.base import ColumnDC
from src.orm.dataclasses import (
    ForeignKeyRelation,
    Table,
)
from src.tables.tg_user import (
    TgUserDB,
)
from src.utils import MyEnum


@dataclass(frozen=True, slots=True)
class EventDB(Table):
    pk: int

    user_id: int  # ForeignKey: 'TgUserDB'

    name: str
    order_by: str

    type: str

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
        # foreign_keys = EventFKs.values_list()
        tablename = "event"

    class ForeignKeys(Table.ForeignKeys):
        USER_ID = ForeignKeyRelation(TgUserDB, "user_id", "user_id")
        # BACK_EVENT_PREFIX = BackForeignKeyRelation(
        #     EventPrefixDB, other_column="event_fk", my_column="pk"
        # )


if __name__ == "__main__":
    objs = EventDB.select(
        where_clauses={ColumnDC(table_name="event", column_name="pk"): 1},
        order_by_columns=[ColumnDC(column_name="order_by")],
    )
    print(objs)
