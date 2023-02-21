from dataclasses import dataclass
from typing import Callable, Optional

binary = ["Да", "Нет"], lambda x: (1 if x == "Да" else 0) * 100
ternary = [0, 1, 2], lambda x: int(x) * 50

questions_list = [
    ['sleep_hrs', "Slee hours (h-w-gt3)", [7.5, 8, 8.5, 9]],
    ['sleep_score', 'Sleep score (h-w-gt3)', [50, 75, 100]],
    ['steps_cnt', 'Steps count  (h-w-gt3)', [6000, 8000, 10000, 20000]],
    ['hrs_active', 'Hours active  (h-w-gt3)', [0, 1, 2, 6, 8, 12]],
    ['oatmeal_eat', "Овсянка?", *binary],
    ['meat_eat', "Мясо?", *binary],
    ['fish_eat', "Рыба?", *binary],
    ['vegetables_eat', "Овощи?", *ternary],
    ['sugar_eat', "Сладкое?", *ternary],
]


@dataclass
class Question:
    name: str

    text: str
    inline_keyboard_answers: list[str | int]
    answer_mapping_func: Optional[Callable] = None

    def __str__(self):
        # return f'[{self.number}] {self.text}'
        return '{:15} {}'.format(self.name, self.text)


questions_list.sort(key=lambda x: x[0])

questions_objects = [Question(*i) for i in questions_list]
