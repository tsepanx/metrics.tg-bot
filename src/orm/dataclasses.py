"""
This file defines two main classes "Table" and "ForeignKeyRelation" that are most common in my orm.
"""

from dataclasses import dataclass
from typing import (
    ClassVar,
    List,
    Type,
    TypeVar,
)

from src.orm import base
from src.orm.base import (
    ColumnDC,
    JoinByClauseDC,
    JoinTypes,
    TableName,
    ValueType, _update_row, _insert_row,
)

Tbl = TypeVar("Tbl", "Table", dataclass)


@dataclass(frozen=True)
class ForeignKeyRelation:
    class_: Type[Tbl]
    from_column: str
    to_column: str

    def __post_init__(self):
        assert self.to_column in self.class_.__annotations__


@dataclass(frozen=True)
class Table:
    """
    TODO cache objects with the same parameterers
    TODO https://stackoverflow.com/questions/73184156/return-cached-object-for-same-initialization-arguments
    """

    def __post_init__(self):
        object.__setattr__(self, "_fk_values", {})

    @classmethod
    def dataclass_dict_to_row_dict(cls, d: dict[str, ValueType]) -> dict[ColumnDC, ValueType]:
        return {
            ColumnDC(
                table_name=cls.Meta.tablename,
                column_name=k
            ): d[k] for k in d
        }

    def update(self, **kwargs) -> None:
        row: dict[str, ValueType] = self.__dict__
        existing_columns: set[str] = set(row.keys())
        new_columns: set[str] = set(kwargs.keys())

        unchanged_columns: set[str] = existing_columns - new_columns

        where_clauses: dict[ColumnDC, ValueType] = {
            ColumnDC(
                table_name=self.Meta.tablename,
                column_name=k
            ): row[k] for k in unchanged_columns
        }

        set_dict: dict[ColumnDC, ValueType] = {
            ColumnDC(
                table_name=self.Meta.tablename,
                column_name=k
            ): kwargs[k] for k in kwargs
        }

        return _update_row(
            tablename=self.Meta.tablename,
            where_clauses=where_clauses,
            set_dict=set_dict,
        )

    def create(self) -> 'Table':
        row = self.__dict__

        _insert_row(
            tablename=self.Meta.tablename,
            row_dict={
                ColumnDC(
                    table_name=self.Meta.tablename,
                    column_name=k
                ): row[k] for k in row
            }
        )

        return self

    def set_fk_value(self, fkey: str, obj: Tbl) -> None:
        self._fk_values[fkey] = obj

    def get_fk_value(self, fkey: str) -> Tbl | None:
        return self._fk_values.get(fkey, None)

    @classmethod
    def select(
            cls: Type[Tbl],
            join_on_fkeys: bool = False,
            where_clauses: dict[ColumnDC, ValueType] | None = None,
            order_by_columns: list[ColumnDC] | None = None,
    ) -> List[Tbl]:

        def create_dataclass_instance(
                class_to_create: Tbl,
                columns_list: list[ColumnDC],
                values_list: list[ValueType]
        ) -> Tbl:
            return class_to_create(**{
                columns_list[i].column_name: values_list[i]
                for i in range(len(columns_list))
            })

        primary_tablename: TableName = cls.Meta.tablename
        primary_table_columns: list[ColumnDC] = list(
            map(lambda x: ColumnDC(table_name=primary_tablename, column_name=x), cls.__annotations__.keys())
        )

        all_columns: list[ColumnDC] = []
        all_columns += primary_table_columns

        # Stores mapping <join_tablename> : <ForeignKey obj>
        # Auxiliary dict for faster finding ForeignKey instance
        # Used on creating Dataclasses object on setting primary_class._fk_values (at the end of func)
        auxiliary_table_fk_mapping: dict[TableName, ForeignKeyRelation] = {}

        # Stores mapping <table_name> : (<column names list>)
        auxiliary_table_columns_mapping: dict[TableName, list[ColumnDC]] = {primary_tablename: primary_table_columns}

        if join_on_fkeys and hasattr(cls.Meta, "foreign_keys"):
            join_clauses: list[JoinByClauseDC] | None = []

            for fk_dataclass in cls.Meta.foreign_keys:
                # TODO Case: 2nd level of Foreign keys
                "JOIN question_type qt ON q.type_id = qt.pk;"

                join_table_name: TableName = fk_dataclass.class_.Meta.tablename

                join_clauses.append(
                    JoinByClauseDC(
                        table_name=join_table_name,
                        from_column=fk_dataclass.from_column,
                        to_column=fk_dataclass.to_column,
                        join_type=JoinTypes.LEFT,
                    )
                )

                join_table_columns: list[ColumnDC] = list(
                    map(
                        lambda x: ColumnDC(table_name=join_table_name, column_name=x),
                        fk_dataclass.class_.__annotations__.keys(),
                    )
                )

                all_columns += join_table_columns

                auxiliary_table_fk_mapping[join_table_name] = fk_dataclass
                auxiliary_table_columns_mapping[join_table_name] = join_table_columns
        else:
            join_clauses = None

        query_results = base._select(
            tablename=primary_tablename,
            select_columns=all_columns,
            join_clauses=join_clauses,
            where_clauses=where_clauses,
            order_by_columns=order_by_columns,
        )

        objs_list: List[Tbl] = []

        row: list[ValueType]
        for row in query_results:
            primary_table_obj: cls = None

            offset = 0
            for table in auxiliary_table_columns_mapping:
                table_selected_columns: list[ColumnDC] = auxiliary_table_columns_mapping[table]
                columns_count = len(table_selected_columns)

                values_for_table = row[offset: offset + columns_count]

                # len(colnames) == len(values)
                assert len(table_selected_columns) == len(values_for_table)

                if table == primary_tablename:
                    # creating Primary table instance
                    primary_table_obj = create_dataclass_instance(cls, table_selected_columns, values_for_table)
                else:
                    # creating Dataclasses that are JOINED via fk
                    assert primary_table_obj is not None
                    fk_obj = auxiliary_table_fk_mapping[table]

                    # Foreign key value is <null>
                    if primary_table_obj.__getattribute__(fk_obj.from_column) is None:
                        new_dataclass_obj = None
                    else:
                        new_dataclass_obj = create_dataclass_instance(fk_obj.class_, table_selected_columns,
                                                                      values_for_table)
                    primary_table_obj.set_fk_value(fk_obj.from_column, new_dataclass_obj)

                offset += columns_count
            objs_list.append(primary_table_obj)

        return objs_list

    @classmethod
    def select_all(cls):
        return cls.select(
            join_on_fkeys=True,
            where_clauses=None,
            order_by_columns=[
                ColumnDC(table_name=cls.Meta.tablename, column_name="order_by")
            ]
        )

    class Meta:
        foreign_keys: ClassVar[list[ForeignKeyRelation]] = None
        tablename: ClassVar[str] = None
