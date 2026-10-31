"""
Address and discount filtering.

Flipkart search results currently do not reliably expose
pincode-specific availability through the listing page, so
we only apply address filtering when a Deal explicitly contains
regional information.
"""

from config import ADDRESS, MIN_DISCOUNT_PERCENT
from models import Deal


def address_params() -> dict:
    return {
        "pincode": ADDRESS["pincode"],
        "city": ADDRESS["city"],
    }


def is_available_here(deal: Deal) -> bool:

    if deal.pincodes:
        if ADDRESS["pincode"] not in deal.pincodes:
            return False

    if deal.city:
        if deal.city.lower() != ADDRESS["city"].lower():
            return False

    return True


def filter_deals(deals: list[Deal]) -> list[Deal]:

    result = []

    for deal in deals:

        if not is_available_here(deal):
            continue

        if deal.discount_pct is None:
            continue

        if deal.discount_pct < MIN_DISCOUNT_PERCENT:
            continue

        if deal.price <= 0:
            continue

        if deal.mrp is None or deal.mrp <= deal.price:
            continue

        result.append(deal)

    return result