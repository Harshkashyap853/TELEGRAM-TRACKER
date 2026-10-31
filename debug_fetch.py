"""
Flipkart scraper debugging tool.

Usage:

    python debug_fetcher.py

Optional:

    set HEADFUL=1
    set DEBUG_BROWSER=1

Then:

    python debug_fetcher.py
"""

import logging
import os


# Enable debug extraction.
os.environ["DEBUG_BROWSER"] = "1"


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s: "
        "%(message)s"
    ),
)


from address_filter import (
    address_params,
    filter_deals,
)

from fetchers import ALL_FETCHERS


def main():

    source = "flipkart"


    fetcher = next(
        (
            item
            for item in ALL_FETCHERS
            if item.source == source
        ),
        None,
    )


    if fetcher is None:

        raise RuntimeError(
            f"Fetcher not found: {source}"
        )


    print()
    print("=" * 80)
    print("FLIPKART DEBUG FETCH")
    print("=" * 80)
    print()


    deals = fetcher.fetch(
        address_params()
    )


    good = filter_deals(
        deals
    )


    print()
    print(
        f"Parsed deals : {len(deals)}"
    )

    print(
        f"50%+ deals   : {len(good)}"
    )

    print()


    for deal in good[:30]:

        print(
            f"{deal.discount_pct:.0f}% | "
            f"₹{deal.price:,.0f} | "
            f"MRP ₹{deal.mrp:,.0f}"
        )

        print(
            f"{deal.name}"
        )

        print(
            f"{deal.url}"
        )

        print("-" * 80)


    print()
    print(
        "Raw card output:"
    )

    print(
        "debug_flipkart.txt"
    )

    print()


if __name__ == "__main__":
    main()