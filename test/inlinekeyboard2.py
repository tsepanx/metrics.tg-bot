import telegram
from telegram import (
    Update, InputTextMessageContent,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    PicklePersistence,
    InlineQueryHandler,
)


async def on_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    print(query)
    results = [
        telegram.InlineQueryResultArticle(
            '123',
            'title1',
            input_message_content=InputTextMessageContent(query.upper())
        )
    ]
    # отвечаем на сообщение результатом
    await update.inline_query.answer(results)


if __name__ == "__main__":
    TOKEN = "1407932407:AAHFbEsEKEHpB-9kAdTTlzfVRrQE6kg6Tqs"

    persistence = PicklePersistence(filepath="../persitencebot", update_interval=1)

    app = ApplicationBuilder().persistence(persistence).token(TOKEN).build()

    # commands_mapping = {
    #     "ask": (ask_command, "Start asking"),
    #     "stats": (stats_command, "Get stats"),
    #     "exitt": (exit_command,),
    # }

    # for command_string, value in commands_mapping.items():
    #     func = value[0]
    #     app.add_handler(CommandHandler(command_string, func))

    # app.add_handler(MessageHandler(filters.TEXT, plaintext_handler))
    # app.add_handler(CallbackQueryHandler(on_callback_query))
    app.add_handler(InlineQueryHandler(on_inline_query))
    app.run_polling()
