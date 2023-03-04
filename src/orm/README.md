
## ORM module

This is my small and neat module to handle `SQL` queries building & execution (done via `psycopg`).


### Docs

#### `base.py`

Does all the job connecting to `PostgreSQL` database (via `psycopg` lib).
It uses `psycopg.sql` module to safely generate `SQL` queries as templates, and then pass them with given parameters


#### `dataclasses.py`

My `ORM` is made mostly built around Python `dataclasses` classes.

This done for simplicity, and may, however, impose some limitations (I plan to move to pure classes in the future).

##### `Table` (`orm/dataclasses.py`)

The most important class, from which every class describing table must inherit.

It has 2 additional subclasses: 
- `Table.Meta`
  - stores `tablename` - a real name of table in `DB`
- `Table.ForeignKeys`
  - enum-like class to store `ForeignKey` (my class) objects

##### `ForeignKey` and `BackForeignKey`

Both describes foreign key from one table to another.

1) First is just an indication of that some class attribute named `ForeignKey.my_column` refers to a table of class `ForeignKey.class_` and column_name `ForeignKey.other_column`
    - it describes `many-to-one` relationship, so our class can store up to `1` of other's table instances
2) Second is the same, but for reverse case: Another table (`BackForeignKey.class_`) references via fkey (`BackForeignKey.my_column`) to current table's attr (`BackForeignKey.other_column`)
    - Main difference is that it is `one-to-many` relation (in terms of current table), and thus our table can store multiple of other's table instances, that are referencing to us.

Under the hood referenced (or referencing) objects are stored in `Table._fk_values`,
but should only be accessed via `{set,get}_fk_value`, `{set,get}_back_fk_value` methods.
Those objects are fetched by adding additional `JOIN` clause to query, and can be controlled by flag `join_on_fkeys=True` (in `Table.select` method)

