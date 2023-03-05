import logging

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    PicklePersistence,
)

from src.conversations.ask import (
    ask_conv_handler,
)
from src.other_commands import (
    TgCommands,
    on_callback_query,
    post_init,
)

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    with open(".token", encoding="utf-8") as f:
        TOKEN = f.read().strip()
        print(TOKEN)

    persistence = PicklePersistence(filepath="persitencebot", update_interval=1)

    app = ApplicationBuilder().token(TOKEN).persistence(persistence).post_init(post_init).build()

    app.add_handler(ask_conv_handler)

    for command in TgCommands.values_list():
        if command.handler:
            app.add_handler(command.handler)

    app.add_handler(CallbackQueryHandler(on_callback_query))
    app.run_polling()
