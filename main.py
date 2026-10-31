import logging

from telegram.ext import Application

import handlers

from config import (
    BOT_TOKEN,
    POLL_INTERVAL_SECONDS,
)

from poster import poll_and_post


logging.basicConfig(
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s: "
        "%(message)s"
    ),
    level=logging.INFO,
)


# Reduce noisy HTTP logs.
logging.getLogger(
    "httpx"
).setLevel(logging.WARNING)


logging.getLogger(
    "telegram"
).setLevel(logging.INFO)


def main() -> None:

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )


    handlers.register(
        app
    )


    # First scrape happens after 10 seconds.
    # Then every POLL_INTERVAL_SECONDS.
    app.job_queue.run_repeating(
        poll_and_post,
        interval=POLL_INTERVAL_SECONDS,
        first=10,
        name="deal-poll",
    )


    logging.info(
        "DealBot started."
    )


    logging.info(
        "Enabled sources: Flipkart"
    )


    logging.info(
        "Polling interval: %s seconds",
        POLL_INTERVAL_SECONDS,
    )


    app.run_polling(
        allowed_updates=[
            "message",
            "channel_post",
        ]
    )


if __name__ == "__main__":
    main()