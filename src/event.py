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


def get_ordered_events_names() -> list[str]:
    rows: list[EventDB] = EventDB.select(
        where_clauses=None,
        order_by_columns=[
            ColumnDC(column_name="order_by")
        ]
    )

    return list(map(lambda x: x.name, rows))


if __name__ == "__main__":
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
