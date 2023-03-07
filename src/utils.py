import datetime
import enum
import functools
from io import BytesIO
from typing import (
    Any,
    Sequence,
    Type,
)

import pytz
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
)

# DEFAULT_TZ = datetime.timezone(datetime.timedelta(hours=3))

LOCATION = "Europe/Moscow"

DEFAULT_TZ = pytz.timezone(LOCATION)

NO_ENTRIES_FOR_TYPE = lambda answer_type: f"No {answer_type.name} records"


class MyException(Exception):
    pass


class FormatException(Exception):
    pass


class MyEnum(enum.Enum):
    @classmethod
    def values_list(cls):
        return list(map(lambda x: x.value, cls.__members__.values()))

    @classmethod
    def enum_by_name(cls, name: str) -> Type["MyEnum"] | None:
        return cls.__members__.get(name)


def to_list(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> list:
        res = list(func(*args, **kwargs))
        return res

    return wrapper


def get_now() -> datetime.datetime:
    return datetime.datetime.now(DEFAULT_TZ).replace(tzinfo=None).replace(microsecond=0)


def get_now_time() -> datetime.time:
    return get_now().time()


def get_today() -> datetime.date:
    return get_now().date()


def get_nth_delta_day(n: int = 0) -> datetime.date:
    date = get_today() + datetime.timedelta(days=n)
    return date


def format_timedelta(td: datetime.timedelta) -> str:
    days_str = f"{td.days} days, " if td.days else ""
    time_str = str((datetime.datetime.min + td).time().replace(microsecond=0))

    return days_str + time_str


def format_datetime(ts: datetime.datetime) -> str:
    return ts.isoformat(sep=" ", timespec="seconds")


def any_of_strings_regex(list_str: list[str]) -> str:
    inner_s = "|".join(list_str)
    inner_s = inner_s.replace("+", r"\+")

    s = rf"^({inner_s})$"
    print(s)
    return s


def any_of_buttons_regex(keyboard: Sequence[Sequence[str]]) -> str:
    flat_list = [j for i in keyboard for j in i]
    return any_of_strings_regex(flat_list)


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
