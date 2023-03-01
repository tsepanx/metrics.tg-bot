from dataclasses import (
    dataclass,
)

from src.orm.base import (
    ColumnDC,
)
from src.orm.dataclasses import (
    Table,
    get_dataclasses_where,
)


@dataclass(frozen=True)
class EventDB(Table):
    # pylint: disable=too-many-instance-attributes

    pk: int
    name: str
    order_by: str

    class Meta:
        tablename = "event"


def get_ordered_events_names() -> list[str]:
    class_ = EventDB

    rows: list[class_] = get_dataclasses_where(
        class_=class_, where_clauses=None, order_by_columns=[ColumnDC(column_name="order_by")]
    )

    return list(map(lambda x: x.name, rows))


if __name__ == "__main__":
    objs = get_dataclasses_where(
        EventDB,
        join_foreign_keys=False,
        where_clauses={
            ColumnDC(table_name="event", column_name="pk"): 1
        },
        order_by_columns=[
            ColumnDC(column_name="order_by")
        ]
    )
    print(objs)

    # print(get_ordered_events_names())
