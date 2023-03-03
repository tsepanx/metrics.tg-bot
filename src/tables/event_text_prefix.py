from dataclasses import dataclass

from src.orm.base import ColumnDC
from src.orm.dataclasses import (
    Table
)


@dataclass(frozen=True, slots=True)
class EventPrefixDB(Table):
    pk: int

    event_fk: int  # ForeignKey : 'EventDB'
    name: str  # TODO rename to text

    @classmethod
    def select_all(cls):
        return cls.select(
            join_on_fkeys=True,
            where_clauses={ColumnDC(table_name=cls.Meta.tablename, column_name="is_activated"): True},
            order_by_columns=[ColumnDC(table_name=cls.Meta.tablename, column_name="order_by")],
        )

    class Meta(Table.Meta):
        # Made to avoid circular imports with `event.py`
        # foreign_keys = [
        #     ForeignKeyRelation(EventDB, "event_fk", "pk")
        # ]
        tablename = "event_text_prefix"
