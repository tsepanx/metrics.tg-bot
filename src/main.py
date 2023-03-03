import logging

from telegram.ext import PicklePersistence, ApplicationBuilder, CommandHandler

from src.conversations.ask import ask_conv_handler
from src.other_commands import post_init, stats_command

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    with open(".token", encoding="utf-8") as f:
        TOKEN = f.read()
        print(TOKEN)

    persistence = PicklePersistence(filepath="persitencebot", update_interval=1)

    app = ApplicationBuilder() \
        .token(TOKEN) \
        .persistence(persistence) \
        .post_init(post_init) \
        .build()

    app.add_handler(ask_conv_handler)
    app.add_handler(CommandHandler("stats", stats_command))
    app.run_polling()
