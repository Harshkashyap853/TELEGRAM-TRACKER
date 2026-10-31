"""
Central configuration for DealBot.

Currently enabled source:
    Flipkart

Other sources can be added later.
"""

import os


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is not set."
    )


# ============================================================
# DELIVERY ADDRESS
# ============================================================

ADDRESS = {
    "label": "Home",
    "line1": "Trident Coliving majestic stays, Maangaon, Hinjawadi Phase 2 Rd, Hinjawadi",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411057",
    "lat": 18.58,
    "lng": 73.70,
}


# ============================================================
# TELEGRAM CHANNELS
# ============================================================

CHANNELS = {
    # Replace this with your REAL Flipkart Telegram channel ID.
    "flipkart": your channel id,

    # Keep these for later.
    # "amazon": -1000000000001,
    # "instamart": -1000000000003,
    # "bigbasket": -1000000000004,
    # "swiggy": -1000000000005,
    # "zomato": -1000000000006,
    # "myntra": -1000000000007,
    # "ajio": -1000000000008,
}


# ============================================================
# FLIPKART CATEGORIES
# ============================================================

CATEGORIES_GENERAL = [
    "mobiles",
    "laptops",
    "headphones",
    "smart watches",
    "televisions",
    "refrigerators",
    "washing machine",
    "air conditioner",
    "home appliances",
    "kitchen",
    "home decor",
    "furniture",
    "toys",
    "beauty",
    "backpacks",
    "shoes",
    "watches",
    "tshirts",
    "jeans",
    "trimmers",
]


# ============================================================
# SCRAPING
# ============================================================

# IMPORTANT:
# During development we scrape ALL categories every cycle.
#
# Later, when the scraper is stable, we can optimize this.
PAGES_PER_CYCLE = len(CATEGORIES_GENERAL)

SCROLLS_PER_PAGE = 5

PAGE_LOAD_TIMEOUT = 45000

WAIT_AFTER_LOAD_MS = 2500

WAIT_AFTER_SCROLL_MS = 800


# ============================================================
# DEAL FILTERING
# ============================================================

MIN_DISCOUNT_PERCENT = 50

MAX_POSTS_PER_CYCLE = 10


# ============================================================
# BOT SCHEDULER
# ============================================================

POLL_INTERVAL_SECONDS = 300


# ============================================================
# HTTP / BROWSER
# ============================================================

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)


# ============================================================
# DEBUGGING
# ============================================================

DEBUG_BROWSER = os.environ.get("DEBUG_BROWSER", "0") == "1"

HEADFUL = os.environ.get("HEADFUL", "0") == "1"


# ============================================================
# DATABASE
# ============================================================

DB_PATH = "dealbot.sqlite3"
