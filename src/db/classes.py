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
    primary_table_colnames = list(class_.__annotations__.keys())

    select_identifiers: list[tuple[str, str]] = []
    select_identifiers.extend([(primary_tablename, col_name) for col_name in primary_table_colnames])

    # Stores mapping <join_tablename> : <ForeignKey obj>
    # Auxiliary dict for faster finding ForeignKey instance
    # Used on creating Dataclasses object on setting ForeignKey.dataclass_instance (at the end of func)
    foreign_keys_objs: dict[str, tuple[str, ForeignKey]] = {}

    # Stores mapping <table_name> : (<column names list>)
    table_columns_mapping: dict[str, list[str]] = {
        primary_tablename: primary_table_colnames
    }

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
            select_identifiers.extend([(join_tablename, col_name) for col_name in join_table_columns])

            foreign_keys_objs[join_tablename] = (from_col, fk_obj)
            table_columns_mapping[join_tablename] = join_table_columns
    else:
        join_dict = None

    query_results = base.get_where(
        tablename=primary_tablename,
        select_cols=select_identifiers,
        join_dict=join_dict,
        where_dict=where_dict,
        order_by=order_by
    )

    objs_list: list[class_] = []

    row: list
    for row in query_results:
        primary_obj: class_ = None

        offset = 0
        for table in table_columns_mapping:
            table_selected_columns: list[str] = table_columns_mapping[table]
            columns_count = len(table_selected_columns)

            values_for_table = row[offset: offset + columns_count]

            # len(colnames) == len(values)
            assert len(table_selected_columns) == len(values_for_table)

            def create_object(class_to_create: DBClassType) -> DBClassType:
                return class_to_create(**{
                    table_selected_columns[i]: values_for_table[i]
                    for i in range(columns_count)
                })

            if table == primary_tablename:
                # creating Primary table instance
                primary_obj = create_object(class_)
            else:
                # creating Dataclasses that are JOINED via fk
                assert primary_obj is not None
                from_col, fk_obj = foreign_keys_objs[table]
                fk_obj: ForeignKey

                obj = create_object(fk_obj.class_)
                primary_obj.set_fk_value(from_col, obj)

            offset += columns_count
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
