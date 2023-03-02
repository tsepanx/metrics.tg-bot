from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def toggle_button_emoji_in_reply_markup(
        ikm: InlineKeyboardMarkup,
        button_old_callback_data: str,
        button_new_callback_data: str,
        emoji_str: str = "☑️",
) -> InlineKeyboardMarkup:

    keyboard: list[list[InlineKeyboardButton]] = []

    for row_i, row in enumerate(ikm.inline_keyboard):
        keyboard.append([])
        for butt_i, button in enumerate(row):
            if button.callback_data == button_old_callback_data:
                if button.text.find(emoji_str) != -1:
                    new_text = button.text[2:]
                else:
                    new_text = f"{emoji_str} " + button.text

                new_button = InlineKeyboardButton(text=new_text, callback_data=button_new_callback_data)
            else:
                new_button = InlineKeyboardButton(text=button.text, callback_data=button.callback_data)

            keyboard[row_i].append(new_button)
    return InlineKeyboardMarkup(keyboard)
