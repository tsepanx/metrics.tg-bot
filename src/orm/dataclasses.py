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
    ValueType,
    _insert_row,
    _update_row,
)
from src.utils import MyEnum

Tbl = TypeVar("Tbl", "Table", dataclass)


@dataclass(frozen=True)
class ForeignKeyRelation:
    class_: Type[Tbl]
    my_column: str
    other_column: str

    def __post_init__(self):
        assert self.other_column in self.class_.__slots__

    def __str__(self) -> str:
        return f"{self.class_.Meta.tablename}__{self.my_column}__{self.other_column}"


@dataclass(frozen=True)
class BackForeignKeyRelation(ForeignKeyRelation):
    def __str__(self):
        return f"back_{super().__str__()}"


# slots=False to add availability for __setattr__ of new attribute
@dataclass(frozen=True, slots=False)
class Table:
    """
    TODO cache objects with the same parameterers
    TODO https://stackoverflow.com/questions/73184156/return-cached-object-for-same-initialization-arguments
    """

    def __post_init__(self):
        object.__setattr__(self, "_fk_values", {})
        # object.__setattr__(self, "_back_fk_values", {})

    @classmethod
    def dataclass_dict_to_row_dict(cls, d: dict[str, ValueType]) -> dict[ColumnDC, ValueType]:
        return {ColumnDC(table_name=cls.Meta.tablename, column_name=k): d[k] for k in d}

    def update(self, **kwargs) -> None:
        row: dict[str, ValueType] = self.__dict__
        existing_columns: set[str] = set(row.keys())
        new_columns: set[str] = set(kwargs.keys())

        unchanged_columns: set[str] = existing_columns - new_columns

        where_clauses: dict[ColumnDC, ValueType] = {
            ColumnDC(table_name=self.Meta.tablename, column_name=k): row[k]
            for k in unchanged_columns
        }

        set_dict: dict[ColumnDC, ValueType] = {
            ColumnDC(table_name=self.Meta.tablename, column_name=k): kwargs[k] for k in kwargs
        }

        return _update_row(
            tablename=self.Meta.tablename,
            where_clauses=where_clauses,
            set_dict=set_dict,
        )

    def create(self) -> "Table":
        row = self.__dict__

        _insert_row(
            tablename=self.Meta.tablename,
            row_dict={ColumnDC(table_name=self.Meta.tablename, column_name=k): row[k] for k in row},
        )

        return self

    def set_fk_value(self, fkey: ForeignKeyRelation, obj: Tbl) -> None:
        # question_type_type_id_pk

        self._fk_values[str(fkey)] = obj

    def get_fk_value(self, fkey: ForeignKeyRelation) -> Tbl | None:
        return self._fk_values.get(str(fkey), None)

    def set_back_fk_value(self, back_fkey: BackForeignKeyRelation, obj: Tbl) -> None:
        key: str = str(back_fkey)
        existing_obj_list: list[Tbl] = self._fk_values.setdefault(key, [])
        existing_obj_list.append(obj)

        self._fk_values[key] = existing_obj_list

    def get_back_fk_value(self, back_fkey: BackForeignKeyRelation) -> list[Tbl] | None:
        key: str = str(back_fkey)

        if key in self._fk_values:
            existing_obj_list: list[Tbl] = self._fk_values.setdefault(key, [])
            return existing_obj_list
        return None

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
            values_list: list[ValueType],
        ) -> Tbl:
            value_apply = lambda x: tuple(x) if isinstance(x, list) else x  # noqa: E731

            return class_to_create(
                **{
                    columns_list[i].column_name: value_apply(values_list[i])
                    for i in range(len(columns_list))
                }
            )

        primary_tablename: TableName = cls.Meta.tablename
        primary_table_columns: list[ColumnDC] = list(
            map(
                lambda x: ColumnDC(table_name=primary_tablename, column_name=x),
                cls.__slots__,
            )
        )

        all_columns: list[ColumnDC] = []
        all_columns += primary_table_columns

        # Stores mapping <join_tablename> : <ForeignKey obj>
        # Auxiliary dict for faster finding ForeignKey instance
        # Used on creating Dataclasses object on setting primary_class._fk_values (at the end of func)
        auxiliary_table_fk_mapping: dict[TableName, ForeignKeyRelation] = {}

        # Stores mapping <table_name> : (<column names list>)
        auxiliary_table_columns_mapping: dict[TableName, list[ColumnDC]] = {
            primary_tablename: primary_table_columns
        }

        join_clauses: list[JoinByClauseDC] | None = []
        if join_on_fkeys and cls.foreign_keys():  # hasattr(cls.Meta, "foreign_keys"):
            for fk_dataclass in cls.foreign_keys():
                # TODO Case: 2nd level of Foreign keys
                "JOIN question_type qt ON q.type_id = qt.pk;"

                join_table_name: TableName = fk_dataclass.class_.Meta.tablename

                join_clauses.append(
                    JoinByClauseDC(
                        table_name=join_table_name,
                        from_column=fk_dataclass.my_column,
                        to_column=fk_dataclass.other_column,
                        join_type=JoinTypes.LEFT,
                    )
                )

                join_table_columns: list[ColumnDC] = list(
                    map(
                        lambda x: ColumnDC(table_name=join_table_name, column_name=x),
                        fk_dataclass.class_.__slots__,
                    )
                )

                all_columns += join_table_columns

                auxiliary_table_fk_mapping[join_table_name] = fk_dataclass
                auxiliary_table_columns_mapping[join_table_name] = join_table_columns

        query_results = base._select(
            tablename=primary_tablename,
            select_columns=all_columns,
            join_clauses=join_clauses,
            where_clauses=where_clauses,
            order_by_columns=order_by_columns,
        )

        objs_dict: dict[int, Tbl] = {}

        row: list[ValueType]
        for row in query_results:
            primary_table_obj: cls = None

            offset = 0
            for table in auxiliary_table_columns_mapping:
                table_selected_columns: list[ColumnDC] = auxiliary_table_columns_mapping[table]
                columns_count = len(table_selected_columns)

                values_for_table = row[offset : offset + columns_count]

                # len(colnames) == len(values)
                assert len(table_selected_columns) == len(values_for_table)

                if table == primary_tablename:
                    # creating Primary table instance
                    primary_table_obj = create_dataclass_instance(
                        cls, table_selected_columns, values_for_table
                    )

                    hash_int: int = primary_table_obj.__hash__()

                    if hash_int in objs_dict:
                        primary_table_obj = objs_dict[hash_int]
                    else:
                        objs_dict[hash_int] = primary_table_obj
                else:
                    # creating Dataclasses that are JOINED via fk
                    assert primary_table_obj is not None
                    fk_obj = auxiliary_table_fk_mapping[table]

                    # Foreign key value is <null>
                    if primary_table_obj.__getattribute__(fk_obj.my_column) is None:
                        new_dataclass_obj = None
                    else:
                        new_dataclass_obj = create_dataclass_instance(
                            fk_obj.class_, table_selected_columns, values_for_table
                        )

                    # TODO possibly merge set_fk_value & set_back_fk_value methods
                    if isinstance(fk_obj, BackForeignKeyRelation):
                        primary_table_obj.set_back_fk_value(fk_obj, new_dataclass_obj)
                    elif isinstance(fk_obj, ForeignKeyRelation):
                        primary_table_obj.set_fk_value(fk_obj, new_dataclass_obj)
                    else:
                        raise Exception

                offset += columns_count

            # objs_dict.append(primary_table_obj)

        return list(objs_dict.values())

    @classmethod
    def select_all(cls):
        return cls.select(
            join_on_fkeys=True,
            where_clauses=None,
            order_by_columns=[ColumnDC(table_name=cls.Meta.tablename, column_name="order_by")],
        )

    @classmethod
    def foreign_keys(cls) -> list[ForeignKeyRelation]:
        return cls.ForeignKeys.values_list()

    class Meta:
        # foreign_keys: ClassVar[list[Union[BackForeignKeyRelation, ForeignKeyRelation]]] = None

        # Foreign keys referencing to this table
        # back_foreign_keys: ClassVar[list[BackForeignKeyRelation]] = None
        tablename: ClassVar[str] = None

    class ForeignKeys(MyEnum):
        pass
