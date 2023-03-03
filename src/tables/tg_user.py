from dataclasses import dataclass

from src.orm.dataclasses import (
    Table,
)


@dataclass(frozen=True, slots=True)
class TgUserDB(Table):
    user_id: int

    class Meta:
        tablename = "tg_user"
