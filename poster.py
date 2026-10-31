"""
Deal polling and Telegram posting.
"""

import asyncio
import html
import logging

from telegram.constants import ParseMode

from telegram.ext import ContextTypes

import storage

from address_filter import (
    address_params,
    filter_deals,
)

from config import (
    CHANNELS,
    MAX_POSTS_PER_CYCLE,
)

from fetchers import ALL_FETCHERS

from models import Deal


log = logging.getLogger(__name__)


def format_deal(
    deal: Deal,
) -> str:

    mrp_text = (
        f"₹{deal.mrp:,.0f}"
        if deal.mrp is not None
        else "-"
    )


    discount_text = (
        f"{deal.discount_pct:.0f}%"
        if deal.discount_pct is not None
        else "N/A"
    )


    return "\n".join([
        f"🔥 <b>{html.escape(deal.name)}</b>",
        "",
        f"💸 Discount: <b>{discount_text} OFF</b>",
        f"💰 Price: <b>₹{deal.price:,.0f}</b>",
        f"🏷️ MRP: <s>{mrp_text}</s>",
        "",
        f"🛒 Source: {html.escape(deal.source.title())}",
        "",
        (
            f'🔗 <a href="{html.escape(deal.url, quote=True)}">'
            "Grab the deal</a>"
        ),
    ])


async def poll_and_post(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:

    address = address_params()


    for fetcher in ALL_FETCHERS:

        chat_id = CHANNELS.get(
            fetcher.source
        )


        if chat_id is None:

            log.error(
                "[%s] No Telegram channel configured",
                fetcher.source,
            )

            continue


        if not storage.is_active(chat_id):

            log.warning(
                "[%s] channel inactive. "
                "Send /start in the channel.",
                fetcher.source,
            )

            continue


        log.info(
            "[%s] Starting fetch...",
            fetcher.source,
        )


        deals = await asyncio.to_thread(
            fetcher.safe_fetch,
            address,
        )


        log.info(
            "[%s] raw deals=%d",
            fetcher.source,
            len(deals),
        )


        good = filter_deals(
            deals
        )


        log.info(
            "[%s] deals >= minimum discount=%d",
            fetcher.source,
            len(good),
        )


        fresh = [
            deal
            for deal in good
            if not storage.already_seen(
                deal.deal_id
            )
        ]


        fresh.sort(
            key=lambda deal: (
                deal.discount_pct or 0
            ),
            reverse=True,
        )


        log.info(
            "[%s] fresh deals=%d",
            fetcher.source,
            len(fresh),
        )


        for deal in fresh[
            :MAX_POSTS_PER_CYCLE
        ]:

            try:

                log.info(
                    "[%s] posting: %s | "
                    "₹%.0f | MRP ₹%.0f | %s%%",
                    deal.source,
                    deal.name[:80],
                    deal.price,
                    deal.mrp or 0,
                    deal.discount_pct or 0,
                )


                await context.bot.send_message(
                    chat_id=chat_id,
                    text=format_deal(deal),
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                )


                storage.mark_seen(
                    deal.deal_id
                )


                await asyncio.sleep(
                    1.5
                )


            except Exception as exc:

                log.exception(
                    "[%s] Telegram post failed: %s",
                    fetcher.source,
                    exc,
                )


        log.info(
            "[%s] cycle complete.",
            fetcher.source,
        )