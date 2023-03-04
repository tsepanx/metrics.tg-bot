import datetime
import enum
import functools
from io import BytesIO
from typing import Any, Type

import pytz
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
)

# DEFAULT_TZ = datetime.timezone(datetime.timedelta(hours=3))
DEFAULT_TZ = pytz.timezone("Europe/Moscow")


def get_now() -> datetime.datetime:
    return datetime.datetime.now(DEFAULT_TZ).replace(tzinfo=None)


def get_today() -> datetime.date:
    return get_now().date()


def format_dt(ts: datetime.datetime) -> str:
    return ts.isoformat(sep=" ", timespec="seconds")


class MyException(Exception):
    pass


def to_list(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> list:
        res = list(func(*args, **kwargs))
        return res

    return wrapper


def get_nth_delta_day(n: int = 0) -> datetime.date:
    date = get_today() + datetime.timedelta(days=n)
    return date


def text_to_png(text: str, bold=True):
    indent = 5
    indent_point = (indent, indent - 4)  # ...

    bg_color = (200, 200, 200)
    fg_color = (0, 0, 0)

    if bold:
        font = ImageFont.truetype("assets/SourceCodePro-Bold.otf", 16)
    else:
        font = ImageFont.truetype("assets/SourceCodePro-Regular.otf", 16)

    _, __, x2, y2 = ImageDraw.Draw(Image.new("RGB", (0, 0))).textbbox(indent_point, text, font)

    img = Image.new("RGB", (x2 + indent, y2 + indent), bg_color)
    d = ImageDraw.Draw(img)

    d.text(
        indent_point,
        text,
        font=font,
        fill=fg_color,
    )

    return img


def data_to_bytesio(data: Any, fname: str) -> BytesIO:
    bio = BytesIO()
    bio.name = fname

    if isinstance(data, str):
        bio.write(bytes(data, "utf-8"))
    else:
        bio.write(data)

    bio.seek(0)
    return bio


class MyEnum(enum.Enum):
    @classmethod
    def values_list(cls):
        return list(map(lambda x: x.value, cls.__members__.values()))

    @classmethod
    def enum_by_name(cls, name: str) -> Type["MyEnum"] | None:
        return cls.__members__.get(name)
