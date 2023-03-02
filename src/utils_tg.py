import re

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from src.tables.question import QuestionDB


def match_question_choice_callback_data(query: str) -> bool:
    return bool(re.compile("^[0-9]+ (add|remove)$").match(query))


def get_questions_select_keyboard(
        questions: list[QuestionDB],
        include_indices_set: set[int] = None,
        emoji_str: str = "☑️",
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("All", callback_data="all"),
            InlineKeyboardButton("Unanswered", callback_data="unanswered"),
            InlineKeyboardButton("OK", callback_data="end_choosing"),
        ],
    ]

    for i, q in enumerate(questions):
        if include_indices_set is not None and i in include_indices_set:
            butt_text = f"{emoji_str} {q.name}"
            butt_data = f"{i} remove"
        else:
            butt_text = f"{q.name}"
            butt_data = f"{i} add"

        new_button = InlineKeyboardButton(text=butt_text, callback_data=butt_data)
        keyboard.append([new_button])

    return InlineKeyboardMarkup(keyboard)
