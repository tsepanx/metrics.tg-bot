from dataclasses import dataclass

from src.orm.base import ColumnDC
from src.orm.dataclasses import (
    Table,
)


@dataclass(frozen=True)
class EventDB(Table):
    pk: int
    name: str
    order_by: str

    class Meta:
        tablename = "event"


if __name__ == "__main__":
    # rows: list[EventDB] = EventDB.select(
    #     order_by_columns=[
    #         ColumnDC(column_name="order_by")
    #     ]
    # )

    objs = EventDB.select(
        where_clauses={
            ColumnDC(table_name="event", column_name="pk"): 1
        },
        order_by_columns=[
            ColumnDC(column_name="order_by")
        ]
    )
    print(objs)

    # print(get_ordered_events_names())
