import datetime
import enum
from dataclasses import dataclass
from typing import Callable, Optional

binary = ["Да", "Нет"], lambda x: (1 if x == "Да" else 0) * 100
ternary = [0, 1, 2], lambda x: int(float(x) * 50)
decimal_grade = list(range(0, 10 + 1)), lambda x: int(float(x) * 10)


def str_to_time(s: str) -> datetime.time:
    t = datetime.time.fromisoformat(s)

    return t
    # return (t.hour * 60 + t.minute) / 60


def float_hrs_to_time(s: str) -> datetime.time:
    f = float(s)

    hrs = int(f) % 24
    mins = int((f - int(f)) * 60)

    return datetime.time(hour=hrs, minute=mins)


def int_minutes_to_time(s: str) -> datetime.time:
    n = int(s)

    hrs = n // 60
    mins = n % 60

    return datetime.time(hour=hrs, minute=mins)


def time_or_hours(s: str) -> datetime.time:
    try:
        t = str_to_time(s)
    except Exception:
        t = float_hrs_to_time(s)

    return t


# def time_or_minutes(s: str) -> datetime.time:
#     try:
#         t = str_to_time(s)
#     except Exception:
#         t = int_minutes_to_time(s)
#
#     return t

hours_1_buttons = ["00:00", "00:30", "01:00", "01:30"]


class QuestionType(enum.Enum):
    HOURS = time_or_hours
    BINARY = binary
    DECIMAL_GRADE = decimal_grade


questions_list = [
    [
        'sleep_1_start', "(H) Отбой (время)",
        # [22, 23, 24, 25], float_to_time
        ["22:00", "23:00", "00:00", "01:00"], time_or_hours
    ],
    [
        'sleep_2_end', "(H) Подъем (время)",
        # [7.5, 8, 9, 10, 11, 12], float_to_time
        ["08:00", "09:00", "10:00", "11:00", "12:00"], time_or_hours
    ],

    ['sleep_hrs', "`(H)` Sleep hours (hours) (h-w-gt3)", [7.5, 8, 8.5, 9], time_or_hours],
    ['sleep_score', '`(0-100)` Sleep score (h-w-gt3)', [50, 75, 100]],
    ['steps_cnt', '`(D)` Steps count  (h-w-gt3)', [6000, 8000, 10000, 20000]],
    ['hrs_active', '`(D)` Hours active  (h-w-gt3)', [0, 1, 2, 6, 8, 12]],
    ['mins_activity', "`(H)` Minutes activity (h-w-gt3)", hours_1_buttons, time_or_hours],

    ['sport_trainings', '`(H)` Спорт. тренировки (часы)?', hours_1_buttons, time_or_hours],
    ['walking', "(H) Прогулка (часы)?", hours_1_buttons, time_or_hours],

    # Meal
    ['oatmeal_eat', "`(0/1)` Овсянка?", *binary],
    ['meat_eat', "`(0/1)` Мясо?", *binary],
    ['fish_eat', "`(0/1)` Рыба?", *binary],

    ['vegetables_eat', "`(Grams)` Овощи?", [0, 50, 100, 150]],
    ['nuts_eat', "`(Grams)` Орехи?", [0, 40, 80, 120]],
    ['sugar_eat', "`(0-10)` Сладкое?", *decimal_grade],

    # .
    ['x_big', "X?", *binary],
    ['x_small', "(x)?", *binary],
]


@dataclass
class Question:
    name: str

    text: str
    inline_keyboard_answers: list[str]
    answer_mapping_func: Optional[Callable] = None

    def __str__(self):
        # return f'[{self.number}] {self.text}'
        return '{:15} {}'.format(self.name, self.text)


# questions_list.sort(key=lambda x: x[0])
# for q in questions_list:
#     q[2] = list(map(str, q[2]))

questions_objects = [Question(*i) for i in questions_list]
