import pprint
from dataclasses import dataclass
from typing import Sequence, Type, TypeVar

from src.db import base


class ForeignKey:
    dataclass_instance: 'DBClassType' = None

    def __init__(self, class_: 'DBClassType', mapped_on):
        assert mapped_on in class_.__annotations__

        self.class_ = class_
        self.mapped_on = mapped_on


class Table:
    def get_referenced_dataclass(self, fk_name) -> 'DBClassType':
        assert fk_name in self.Meta.foreign_keys
        fk: ForeignKey = self.Meta.foreign_keys[fk_name]

        if fk.dataclass_instance:
            return fk.dataclass_instance
        else:
            raise Exception(f"Class {self.__class__} was fetched without JOINing to {fk.class_.__class__}'s Table")

    class Meta:
        foreign_keys = {}
        tablename = None


DBClassType = TypeVar('DBClassType', Table, dataclass)


def get_dataclasses_where(
        class_: DBClassType,
        join_foreign_keys: bool = False,
        where_dict: dict | None = None,
        order_by: Sequence[str] | None = None,
) -> list[Type[DBClassType]]:
    primary_tablename = class_.Meta.tablename
    columns_names = list(class_.__annotations__.keys())

    select_columns = {
        primary_tablename: columns_names
    }

    # Stores mapping <join_tablename> : <ForeignKey obj>
    # Auxiliary dict for faster finding ForeignKey instance
    # Used on creating Dataclasses object on setting ForeignKey.dataclass_instance (at the end of func)
    foreign_keys_objs: dict[str, ForeignKey] = {}

    if join_foreign_keys and hasattr(class_.Meta, 'foreign_keys'):
        join_dict = {}

        fk_name: str
        fk_class: ForeignKey
        for fk_name, fk_class in class_.Meta.foreign_keys.items():
            # TODO Case: 2nd level of Foreign keys
            "JOIN question_type qt ON q.type_id = qt.pk;"

            join_tablename = fk_class.class_.Meta.tablename
            from_col = fk_name
            to_col = fk_class.mapped_on

            join_dict[join_tablename] = (from_col, to_col)

            join_table_columns = list(fk_class.class_.__annotations__.keys())
            select_columns[join_tablename] = join_table_columns

            foreign_keys_objs[join_tablename] = fk_class
    else:
        join_dict = None

    query_results = base.get_where(
        tablename=class_.Meta.tablename,
        select_cols=select_columns,
        join_dict=join_dict,
        where_dict=where_dict,
        order_by=order_by
    )

    return_obj: class_ = None

    row: list
    for row in query_results:

        offset = 0
        for table in select_columns:
            table_selected_colnames: list[str] = select_columns[table]

            left_bound = offset
            right_bound = offset + len(table_selected_colnames)

            row_values_for_table = row[left_bound:right_bound]

            # len(colnames) == len(values)
            assert len(table_selected_colnames) == len(row_values_for_table)

            def create_object(class_to_create: DBClassType) -> DBClassType:
                return class_to_create(**{
                    table_selected_colnames[i]: row_values_for_table[i]
                    for i in range(len(table_selected_colnames))
                })

            if table == primary_tablename:
                return_obj = create_object(class_)
            else:
                foreign_key_instance: ForeignKey = foreign_keys_objs[table]

                obj = create_object(foreign_key_instance.class_)
                foreign_key_instance.dataclass_instance = obj

            offset += len(table_selected_colnames)

    assert return_obj is not None
    return return_obj


@dataclass(frozen=True)
class EventDB(Table):
    # pylint: disable=too-many-instance-attributes

    pk: int
    name: str
    order_by: str

    class Meta:
        tablename = 'event'


if __name__ == "__main__":
    objs = get_dataclasses_where(
        EventDB,
        order_by=['order_by']
    )

    pprint.pprint(objs)
