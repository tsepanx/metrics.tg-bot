import pprint
from dataclasses import dataclass
from typing import Sequence, Type, TypeVar, ClassVar

from src.db import base


@dataclass(frozen=True)
class ForeignKey:
    class_: 'DBClassType'
    to_column: str

    def __post_init__(self):
        assert self.to_column in self.class_.__annotations__


@dataclass(frozen=True)
class Table:
    __FK_VALUES_ATTR_NAME = '_fk_values'

    def __post_init__(self):
        object.__setattr__(self, self.__FK_VALUES_ATTR_NAME, {})

    def set_fk_value(self, fkey: str, obj: 'DBClassType') -> None:
        self.__getattribute__(self.__FK_VALUES_ATTR_NAME)[fkey] = obj

    def get_fk_value(self, fkey: str) -> 'DBClassType':
        return self.__getattribute__(self.__FK_VALUES_ATTR_NAME)[fkey]

    class Meta:
        foreign_keys: dict
        tablename: ClassVar[str] = None


DBClassType = TypeVar('DBClassType', Table, dataclass)


def get_dataclasses_where(
        class_: DBClassType,
        join_foreign_keys: bool = False,
        where_dict: dict | None = None,
        order_by: Sequence[str] | None = None,
) -> list[Type[DBClassType]]:
    # meta_instance: Table.Meta = class_.meta_instance

    primary_tablename = class_.Meta.tablename
    columns_names = list(class_.__annotations__.keys())

    select_columns = {
        primary_tablename: columns_names
    }

    # Stores mapping <join_tablename> : <ForeignKey obj>
    # Auxiliary dict for faster finding ForeignKey instance
    # Used on creating Dataclasses object on setting ForeignKey.dataclass_instance (at the end of func)
    foreign_keys_objs: dict[str, tuple[str, ForeignKey]] = {}

    if join_foreign_keys and hasattr(class_.Meta, 'foreign_keys'):
        join_dict = {}

        fk_name: str
        fk_obj: ForeignKey
        for fk_name, fk_obj in class_.Meta.foreign_keys.items():
            # TODO Case: 2nd level of Foreign keys
            "JOIN question_type qt ON q.type_id = qt.pk;"

            join_tablename = fk_obj.class_.Meta.tablename
            from_col = fk_name
            to_col = fk_obj.to_column

            join_dict[join_tablename] = (from_col, to_col)

            join_table_columns = list(fk_obj.class_.__annotations__.keys())
            select_columns[join_tablename] = join_table_columns

            foreign_keys_objs[join_tablename] = (from_col, fk_obj)
    else:
        join_dict = None

    query_results = base.get_where(
        tablename=primary_tablename,
        select_cols=select_columns,
        join_dict=join_dict,
        where_dict=where_dict,
        order_by=order_by
    )

    objs_list: list[class_] = []

    row: list
    for row in query_results:
        primary_obj: class_ = None

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
                primary_obj = create_object(class_)
            else:
                assert primary_obj is not None
                from_col, fk_obj = foreign_keys_objs[table]
                fk_obj: ForeignKey

                obj = create_object(fk_obj.class_)
                primary_obj.set_fk_value(from_col, obj)

            offset += len(table_selected_colnames)
        objs_list.append(primary_obj)

    return objs_list


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
