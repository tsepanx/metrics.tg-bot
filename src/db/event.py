from src.db import (
    classes,
)


def get_ordered_events_names() -> list[str]:
    class_ = classes.EventDB

    rows: list[class_] = classes.get_dataclasses_where(class_=class_, where_dict=None, order_by=["order_by"])

    return list(map(lambda x: x.name, rows))
