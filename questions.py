from dataclasses import dataclass
from typing import Callable

values = lambda v: [v, lambda x: x]
# binary = [["Да", "Нет"], lambda x: 1 if x == 'Да' else 0]
binary = ["Да", "Нет"]
# ternary = [[0, 1, 2], lambda x: x]
ternary = [0, 1, 2]

questions_list = [
    ['sleep_hrs', "Сколько часов ты спал?", [7.5, 8, 8.5, 9]],
    ['sleep_score', 'Sleep score (huwei-watch-gt3)', [50, 75, 100]],
    ['oatmeal_eat', "Овсянка?", binary],
    ['meat_eat', "Мясо?", binary],
    ['fish_eat', "Рыба?", binary],
    ['vegetables_eat', "Овощи?", binary],
    ['sugar_eat', "Сладкое?", ternary],
]


@dataclass
class Question:
    name: str

    text: str
    inline_keyboard_answers: list[str | int]

    # answer_mapping_func: Callable

    def __str__(self):
        # return f'[{self.number}] {self.text}'
        return '{:15} {}'.format(self.name, self.text)


questions_list.sort(key=lambda x: x[0])

questions_objects = [Question(*i) for i in questions_list]
