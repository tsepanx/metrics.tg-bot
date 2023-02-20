from utils import Question

direct = lambda x: x
binary = lambda x: 1 if x == 'Да' else 0

questions_list = [
    [1, "Сколько часов ты спал?", [7.5, 8, 8.5], direct],
    [2, "Ел ли ты сегодня Овсянку?", ["Да", "Нет"], binary]
]
questions_objects = [Question(*i) for i in questions_list]
