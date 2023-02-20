from utils import Question

questions_list = [
    [1, "Сколько часов ты спал?", [7.5, 8, 8.5], lambda x: x],
    [2, "Ел ли ты сегодня Овсянку?", ["Да", "Нет"], lambda x: 1 if x == 'Да' else 0]
]
questions_objects = [Question(*i) for i in questions_list]
