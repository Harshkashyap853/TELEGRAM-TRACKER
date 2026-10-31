"""
Telegram commands.

Commands:
    /start
    /stop
"""

from telegram import Update

from telegram.ext import (
    CommandHandler,
    ContextTypes,
    filters,
)

import storage

from config import CHANNELS


_ALLOWED = set(
    CHANNELS.values()
)


_SOURCE_BY_CHAT = {
    chat_id: source
    for source, chat_id
    in CHANNELS.items()
}


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    chat = update.effective_chat

    if not chat:
        return


    if chat.id not in _ALLOWED:
        return


    storage.set_active(
        chat.id,
        True,
    )


    source = _SOURCE_BY_CHAT.get(
        chat.id,
        "deal"
    )


    await context.bot.send_message(
        chat.id,
        f"✅ {source.title()} deal alerts started.",
    )


async def stop(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    chat = update.effective_chat

    if not chat:
        return


    if chat.id not in _ALLOWED:
        return


    storage.set_active(
        chat.id,
        False,
    )


    source = _SOURCE_BY_CHAT.get(
        chat.id,
        "deal"
    )


    await context.bot.send_message(
        chat.id,
        f"⏹ {source.title()} deal alerts stopped.",
    )


def register(app) -> None:

    update_filter = (
        filters.UpdateType.CHANNEL_POSTS
        | filters.UpdateType.MESSAGES
    )


    app.add_handler(
        CommandHandler(
            "start",
            start,
            filters=update_filter,
        )
    )


    app.add_handler(
        CommandHandler(
            "stop",
            stop,
            filters=update_filter,
        )
    )