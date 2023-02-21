import datetime
from dataclasses import dataclass
from typing import Callable, Optional

binary = ["Да", "Нет"], lambda x: (1 if x == "Да" else 0) * 100
ternary = [0, 1, 2], lambda x: int(x) * 50


def str_to_time(s: str) -> datetime.time:
    t = datetime.time.fromisoformat(s)

    return t
    # return (t.hour * 60 + t.minute) / 60


def float_to_time(s: str) -> datetime.time:
    f = float(s)

    hrs = int(f) % 24
    mins = int((f - int(f)) * 60)

    return datetime.time(hour=hrs, minute=mins)


def time_from_both_formats(s: str) -> datetime.time:
    try:
        t = str_to_time(s)
    except Exception:
        t = float_to_time(s)

    return t


questions_list = [
    [
        'sleep_1_start', "(H) Отбой (время)",
        # [22, 23, 24, 25], float_to_time
        ["22:00", "23:00", "00:00", "01:00"], time_from_both_formats
    ],
    [
        'sleep_2_end', "(H) Подъем (время)",
        # [7.5, 8, 9, 10, 11, 12], float_to_time
        ["08:00", "09:00", "10:00", "11:00", "12:00"], time_from_both_formats
    ],

    ['sleep_hrs', "(H) Sleep hours (hours) (h-w-gt3)", [7.5, 8, 8.5, 9], time_from_both_formats],
    ['sleep_score', 'Sleep score (h-w-gt3)', [50, 75, 100]],
    ['steps_cnt', 'Steps count  (h-w-gt3)', [6000, 8000, 10000, 20000]],
    ['hrs_active', '(H) Hours active  (h-w-gt3)', [0, 1, 2, 6, 8, 12], time_from_both_formats],
    ['mins_activity', "(H) Minutes activity (h-w-gt3)", [0, .15, .30, .45], time_from_both_formats],

    ['sport_trainings', '(H) Спорт. тренировки (часы)?', [0, 1, 1.5, 2], time_from_both_formats],
    ['walking', "(H) Прогулка (часы)?", [0, 0.5, 1, 1.5], time_from_both_formats],

    # Meal
    ['oatmeal_eat', "Овсянка?", *binary],
    ['meat_eat', "Мясо?", *binary],
    ['fish_eat', "Рыба?", *binary],
    ['vegetables_eat', "Овощи?", *ternary],
    ['sugar_eat', "Сладкое?", *ternary],

    # .
    ['not_x_big', "not X?", *binary],
    ['not_x_small', "not (x)?", *binary],
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
for q in questions_list:
    q[2] = list(map(str, q[2]))

questions_objects = [Question(*i) for i in questions_list]
