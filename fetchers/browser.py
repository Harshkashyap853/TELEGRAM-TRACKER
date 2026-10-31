"""
Browser based deal fetchers.

Flipkart is scraped from the product-card DOM. Price extraction is deliberately
DOM-based: the current selling price and struck-through MRP are identified as
separate elements.

The scraper does NOT collect every rupee amount from the card and guess which
two values are the selling price and MRP.

Currently:
    Flipkart

Other browser fetchers remain registered for future implementation.
"""

import logging
import os
import re
from urllib.parse import urlencode, urlparse, parse_qs

from playwright.sync_api import sync_playwright

import config
from models import Deal

from .base import BaseFetcher


log = logging.getLogger(__name__)


DEBUG = os.environ.get(
    "DEBUG_BROWSER",
    "0",
) == "1"


HEADFUL = os.environ.get(
    "HEADFUL",
    "0",
) == "1"


# ============================================================
# MONEY / DISCOUNT REGEX
# ============================================================

MONEY_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)


DISCOUNT_RE = re.compile(
    r"(\d{1,2})\s*%\s*off",
    re.IGNORECASE,
)


PERCENT_RE = re.compile(
    r"(\d{1,2})\s*%",
    re.IGNORECASE,
)


# ============================================================
# TEXT THAT SHOULD NOT BE USED AS PRODUCT NAME
# ============================================================

NOT_NAME_RE = re.compile(
    r"""
    ^(
        sponsored|
        ad|
        add\s+to\s+compare|
        assured|
        f-assured|
        bestseller|
        best\s+seller|
        limited\s+time\s+deal|
        new|
        only\s+few\s+left|
        hot\s+deal|
        wishlist|
        trending|
        free\s+delivery|
        prime|
        deal\s+of\s+the\s+day|
        lowest\s+price|
        saver\s+deal|
        top\s+discount|
        value\s+365|
        [\d.,]+\s*$
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# OFFER / NOISE TEXT
# ============================================================

NOISE_RE = re.compile(
    r"""
    (
        emi|
        bank\s+offer|
        exchange|
        cashback|
        coupon|
        extra|
        per\s+month|
        no\s+cost|
        with\s+offer|
        buy\s+\d|
        pay\s+later|
        upi\s+offer|
        lowest\s+price|
        platform\s+fee|
        offer\s+handling|
        payment\s+handling
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# FLIPKART PRODUCT EXTRACTION
# ============================================================

PRODUCT_EXTRACTION_JS = r"""
() => {

    const moneyRe =
        /^(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?$/i;

    const discountRe =
        /^\d{1,2}\s*%\s*off$/i;


    // --------------------------------------------------------
    // BASIC HELPERS
    // --------------------------------------------------------

    const normalizeUrl = (url) => {

        try {

            const u =
                new URL(url, location.href);

            return (
                u.origin +
                u.pathname
            );

        } catch {

            return url;
        }
    };


    const text = (el) => {

        return (
            el?.innerText ||
            el?.textContent ||
            ""
        ).trim();
    };


    const visible = (el) => {

        if (!el) {
            return false;
        }

        const style =
            getComputedStyle(el);

        const rect =
            el.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            parseFloat(style.opacity || "1") > 0 &&
            rect.width > 0 &&
            rect.height > 0
        );
    };


    const classText = (el) => {

        return String(
            el?.className || ""
        ).toLowerCase();
    };


    const attributeText = (el) => {

        return [
            el?.getAttribute?.("data-testid"),
            el?.getAttribute?.("aria-label"),
            el?.getAttribute?.("title")
        ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
    };


    const roleText = (el) => {

        return (
            classText(el) +
            " " +
            attributeText(el)
        );
    };


    // --------------------------------------------------------
    // MONEY
    // --------------------------------------------------------

    const getAmount = (el) => {

        if (!el) {
            return null;
        }

        const match =
            text(el).match(
                /(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)/i
            );

        if (!match) {
            return null;
        }

        const value =
            Number(
                match[1].replace(/,/g, "")
            );

        if (
            !Number.isFinite(value) ||
            value <= 0
        ) {
            return null;
        }

        return value;
    };


    const isMoneyElement = (el) => {

        if (!visible(el)) {
            return false;
        }

        return moneyRe.test(
            text(el)
        );
    };


    // --------------------------------------------------------
    // STRIKETHROUGH / MRP DETECTION
    // --------------------------------------------------------

    const isStruckThrough = (el) => {

        if (!el) {
            return false;
        }


        const tag =
            (
                el.tagName || ""
            ).toLowerCase();


        // Semantic HTML.
        if (
            tag === "del" ||
            tag === "s" ||
            tag === "strike"
        ) {
            return true;
        }


        // Element's own style.
        const style =
            getComputedStyle(el);


        if (
            /line-through/i.test(
                style.textDecorationLine || ""
            )
        ) {
            return true;
        }


        if (
            /line-through/i.test(
                style.textDecoration || ""
            )
        ) {
            return true;
        }


        // Sometimes the strike-through is applied
        // to a parent wrapper.
        let parent =
            el.parentElement;


        for (
            let i = 0;
            i < 3 && parent;
            i++,
            parent = parent.parentElement
        ) {

            const parentStyle =
                getComputedStyle(parent);


            if (
                /line-through/i.test(
                    parentStyle.textDecorationLine || ""
                )
            ) {
                return true;
            }


            if (
                /line-through/i.test(
                    parentStyle.textDecoration || ""
                )
            ) {
                return true;
            }
        }


        return false;
    };


    // --------------------------------------------------------
    // PRICE / MRP DOM IDENTIFICATION
    // --------------------------------------------------------

    const isSellingPriceElement = (el) => {

        const role =
            roleText(el);


        // An MRP is not the current selling price.
        if (
            isStruckThrough(el)
        ) {
            return false;
        }


        /*
         * Flipkart has historically used classes such as
         * _30jeq3 for selling price.
         *
         * We also support semantic attributes/classes.
         */

        return (
            /\b30jeq3\b/.test(role) ||
            /\bcurrent[-_\s]?price\b/.test(role) ||
            /\bselling[-_\s]?price\b/.test(role) ||
            /\bdeal[-_\s]?price\b/.test(role) ||
            /\bfinal[-_\s]?price\b/.test(role)
        );
    };


    const isMrpElement = (el) => {

        const role =
            roleText(el);


        return (
            /*
             * Historically used Flipkart MRP class.
             */
            /\b3i9_wc\b/.test(role) ||

            /*
             * Semantic naming.
             */
            /\bmrp\b/.test(role) ||
            /\boriginal[-_\s]?price\b/.test(role) ||
            /\blist[-_\s]?price\b/.test(role) ||
            /\bwas[-_\s]?price\b/.test(role) ||

            /*
             * Visual/semantic strike-through.
             */
            /\bstrike\b/.test(role) ||
            /\bstrikethrough\b/.test(role) ||
            isStruckThrough(el)
        );
    };


    // --------------------------------------------------------
    // PRODUCT NAME
    // --------------------------------------------------------

    const getProductName = (card) => {

        const titleNodes = [
            ...card.querySelectorAll("[title]")
        ];


        for (
            const node of titleNodes
        ) {

            const value =
                (
                    node.getAttribute("title") ||
                    ""
                ).trim();


            if (
                value.length >= 10 &&
                !/[₹%]/.test(value)
            ) {

                return value;
            }
        }


        const images = [
            ...card.querySelectorAll(
                "img[alt]"
            )
        ];


        for (
            const image of images
        ) {

            const value =
                (
                    image.getAttribute("alt") ||
                    ""
                ).trim();


            if (
                value.length >= 10
            ) {

                return value;
            }
        }


        return "";
    };


    // --------------------------------------------------------
    // FIND PRODUCT CARD
    // --------------------------------------------------------

    const productLinkCount = (element) => {

        return new Set(
            [
                ...element.querySelectorAll(
                    "a[href*='/p/']"
                )
            ]
            .map(
                a => normalizeUrl(a.href)
            )
        ).size;
    };


    const findProductCard = (anchor) => {

        let current =
            anchor;


        for (
            let depth = 0;
            depth < 12;
            depth++
        ) {

            const parent =
                current.parentElement;


            if (!parent) {
                break;
            }


            const parentText =
                text(parent);


            const links =
                productLinkCount(parent);


            /*
             * A product card should contain:
             *
             * - enough text
             * - price information
             * - one product URL
             *
             * We stop before climbing into a grid/list
             * containing multiple products.
             */

            if (
                parentText.length >= 20 &&
                parentText.length <= 5000 &&
                links <= 1 &&
                /₹\s*[\d,]+/.test(parentText)
            ) {

                current =
                    parent;

            } else {

                break;
            }
        }


        return current;
    };


    // --------------------------------------------------------
    // EXTRACT ACTUAL PRICE + MRP
    // --------------------------------------------------------

    const extractPriceData = (card) => {

        const elements = [
            ...card.querySelectorAll("*")
        ]
        .filter(
            isMoneyElement
        );


        let sellingPriceElement =
            null;


        let mrpElement =
            null;


        // ----------------------------------------------------
        // FIRST PRIORITY
        // Explicit Flipkart price/MRP DOM indicators.
        // ----------------------------------------------------

        for (
            const element of elements
        ) {

            if (
                !sellingPriceElement &&
                isSellingPriceElement(element)
            ) {

                sellingPriceElement =
                    element;
            }


            if (
                !mrpElement &&
                isMrpElement(element)
            ) {

                mrpElement =
                    element;
            }
        }


        // ----------------------------------------------------
        // SECOND PRIORITY
        // Actual struck-through price.
        // ----------------------------------------------------

        if (!mrpElement) {

            const struckElements =
                elements.filter(
                    isStruckThrough
                );


            if (
                struckElements.length === 1
            ) {

                mrpElement =
                    struckElements[0];
            }
        }


        // ----------------------------------------------------
        // THIRD PRIORITY
        // If there is exactly one non-struck price
        // and exactly one MRP, use that price.
        // ----------------------------------------------------

        if (
            !sellingPriceElement &&
            mrpElement
        ) {

            const mrpValue =
                getAmount(mrpElement);


            const nonStruck =
                elements.filter(
                    element =>
                        !isStruckThrough(element) &&
                        getAmount(element) !== mrpValue
                );


            if (
                nonStruck.length === 1
            ) {

                sellingPriceElement =
                    nonStruck[0];
            }
        }


        // ----------------------------------------------------
        // FINAL CONSERVATIVE DOM FALLBACK
        //
        // We NEVER select:
        //
        // prices[0]
        // prices[1]
        //
        // or arbitrary pairs from text.
        // ----------------------------------------------------

        if (
            !sellingPriceElement ||
            !mrpElement
        ) {

            const struck =
                elements.filter(
                    isStruckThrough
                );


            const nonStruck =
                elements.filter(
                    element =>
                        !isStruckThrough(element)
                );


            if (
                !mrpElement &&
                struck.length === 1
            ) {

                mrpElement =
                    struck[0];
            }


            if (
                !sellingPriceElement &&
                nonStruck.length === 1
            ) {

                sellingPriceElement =
                    nonStruck[0];
            }
        }


        const price =
            getAmount(
                sellingPriceElement
            );


        const mrp =
            getAmount(
                mrpElement
            );


        /*
         * This is critical.
         *
         * If the DOM does not clearly identify both
         * values, return nothing instead of guessing.
         */

        if (
            !price ||
            !mrp ||
            mrp <= price
        ) {

            return {

                price: null,

                mrp: null,

                discount: null,

                priceSource: null,

                mrpSource: null
            };
        }


        // ----------------------------------------------------
        // DISPLAYED DISCOUNT
        //
        // This is ONLY informational/debug data.
        // It is NOT used to determine price/MRP.
        // ----------------------------------------------------

        let displayedDiscount =
            null;


        for (
            const element of
                card.querySelectorAll("*")
        ) {

            if (
                !visible(element)
            ) {
                continue;
            }


            const value =
                text(element);


            if (
                discountRe.test(value)
            ) {

                const match =
                    value.match(
                        /\d{1,2}/
                    );


                if (match) {

                    displayedDiscount =
                        Number(
                            match[0]
                        );

                    break;
                }
            }
        }


        return {

            price,

            mrp,

            discount:
                displayedDiscount,

            priceSource:
                roleText(
                    sellingPriceElement
                ),

            mrpSource:
                roleText(
                    mrpElement
                )
        };
    };


    // --------------------------------------------------------
    // BUILD RESULTS
    // --------------------------------------------------------

    const results = [];

    const seen = new Set();


    const anchors = [
        ...document.querySelectorAll(
            "a[href*='/p/']"
        )
    ];


    for (
        const anchor of anchors
    ) {

        const href =
            normalizeUrl(
                anchor.href
            );


        if (
            !href ||
            seen.has(href)
        ) {

            continue;
        }


        const card =
            findProductCard(
                anchor
            );


        const cardText =
            text(card);


        if (
            !/₹\s*[\d,]+/.test(
                cardText
            )
        ) {

            continue;
        }


        const priceData =
            extractPriceData(
                card
            );


        seen.add(href);


        results.push({

            href,

            text:
                cardText.slice(
                    0,
                    5000
                ),

            hint:
                getProductName(
                    card
                ),

            price:
                priceData.price,

            mrp:
                priceData.mrp,

            discount:
                priceData.discount,

            priceSource:
                priceData.priceSource,

            mrpSource:
                priceData.mrpSource
        });
    }


    return results;
}
"""


# ============================================================
# URL CLEANING
# ============================================================

def clean_url(url: str) -> str:

    try:

        parsed = urlparse(url)

        query = parse_qs(
            parsed.query
        )

        pid = query.get(
            "pid"
        )


        if pid:

            return (
                f"{parsed.scheme}://"
                f"{parsed.netloc}"
                f"{parsed.path}"
                f"?pid={pid[0]}"
            )


        return (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
            f"{parsed.path}"
        )


    except Exception:

        return url


# ============================================================
# PRICE EXTRACTION
# ============================================================

def find_prices(
    text: str,
) -> list[float]:

    values = []


    for match in MONEY_RE.finditer(
        text
    ):

        raw = match.group(1)

        raw = raw.replace(
            ",",
            "",
        )


        try:

            value = float(
                raw
            )


            if value > 0:

                values.append(
                    value
                )


        except ValueError:

            continue


    return values


# ============================================================
# DISCOUNT EXTRACTION
# ============================================================

def find_discount(
    text: str,
) -> float | None:

    match = DISCOUNT_RE.search(
        text
    )


    if match:

        value = float(
            match.group(1)
        )


        if 1 <= value <= 99:

            return value


    matches = PERCENT_RE.findall(
        text
    )


    for value in matches:

        number = float(
            value
        )


        if 1 <= number <= 99:

            return number


    return None


# ============================================================
# PRODUCT NAME
# ============================================================

def extract_name(
    text: str,
    hint: str,
) -> str | None:

    hint = (
        hint or ""
    ).strip()


    if (
        len(hint) >= 10
        and not MONEY_RE.search(hint)
        and "%" not in hint
    ):

        return hint[:150]


    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


    candidates = []


    for line in lines:

        if len(line) < 3:

            continue


        if len(line) > 250:

            continue


        if MONEY_RE.search(line):

            continue


        if "%" in line:

            continue


        if NOISE_RE.search(line):

            continue


        if NOT_NAME_RE.match(line):

            continue


        # Ratings.
        if re.fullmatch(
            r"[\d.]+\s*★?",
            line,
        ):

            continue


        # Review counts.
        if re.fullmatch(
            r"[\d,()]+\s*(Ratings?|Reviews?)?",
            line,
            re.IGNORECASE,
        ):

            continue


        candidates.append(
            line
        )


    if not candidates:

        return None


    name =candidates[0]


    if (
        len(name) < 20
        and len(candidates) > 1
    ):

        second = candidates[1]


        if not second.lower().startswith(
            name.lower()
        ):

            name = f"{name} {second}"


    return name[:150]


# ============================================================
# CARD PARSER
# ============================================================

def parse_card(
    source: str,
    href: str,
    text: str,
    hint: str = "",
    dom_price=None,
    dom_mrp=None,
    dom_discount=None,
    price_source: str = "",
    mrp_source: str = "",
) -> Deal | None:

    try:

        if not href:

            return None


        if not text:

            return None


        # ----------------------------------------------------
        # FLIPKART
        #
        # IMPORTANT:
        # We no longer use find_prices() or pick_price_pair()
        # to guess the selling price/MRP.
        #
        # The JavaScript extraction must provide both values
        # from the actual DOM.
        # ----------------------------------------------------

        if source == "flipkart":

            if (
                dom_price is None or
                dom_mrp is None
            ):

                log.debug(
                    "[flipkart] skipped: "
                    "reliable DOM price/MRP not found | "
                    "price=%r mrp=%r",
                    dom_price,
                    dom_mrp,
                )

                return None


            price = float(dom_price)


            mrp = float(dom_mrp)


            if price <= 0:

                return None


            if mrp <= price:

                return None


        else:

            # /*
            #  * Other browser sources remain in the
            #  * project but are currently disabled by
            #  * their all_pages() methods.
            #  */

            return None


        # ----------------------------------------------------
        # ACTUAL DISCOUNT CALCULATION
        #
        # Flipkart's displayed discount is NOT trusted.
        # We calculate it ourselves from the DOM price/MRP.
        # ----------------------------------------------------

        calculated_discount = (
            (mrp - price) /
            mrp
        ) * 100


        if calculated_discount <= 0:

            return None


        name = extract_name(
                text,
                hint,
            )


        if not name:

            return None


        log.info(
            "[%s] %s | "
            "PRICE=₹%.2f | "
            "MRP=₹%.2f | "
            "DISCOUNT=%.2f%%",
            source,
            name[:80],
            price,
            mrp,
            calculated_discount,
        )


        log.debug(
            "[%s] DOM price source=%s | "
            "DOM MRP source=%s | "
            "Flipkart displayed discount=%s",
            source,
            price_source,
            mrp_source,
            dom_discount,
        )


        return Deal(

            source=source,

            name=name,

            price=price,

            mrp=mrp,

            url=clean_url(
                href
            ),

            discount_pct=round(
                calculated_discount
            ),
        )


    except Exception as exc:

        log.debug(
            "parse_card failed: %s",
            exc,
        )

        return None


# ============================================================
# GENERIC BROWSER FETCHER
# ============================================================

class BrowserFetcher(
    BaseFetcher
):

    LINK_SELECTOR = "a[href]"

    CARD_SELECTOR = ""


    def __init__(self):

        super().__init__()

        self._cursor = 0


    def all_pages(
        self,
    ) -> list[str]:

        raise NotImplementedError


    def _batch(
        self,
    ) -> list[str]:

        pages = self.all_pages()


        if not pages:

            return []


        n = min(
                config.PAGES_PER_CYCLE,
                len(pages),
            )


        batch = [

            pages[
                (
                    self._cursor +
                    i
                ) % len(pages)
            ]

            for i in range(n)

        ]


        self._cursor = (
            self._cursor +
            n
        ) % len(pages)


        return batch


    def fetch(
        self,
        address,
    ):

        deals = []

        seen_urls = set()

        dump = []


        pages = self._batch()


        log.info(
            "[%s] starting scrape: %d pages",
            self.source,
            len(pages),
        )


        with sync_playwright() as playwright:

            browser = playwright.chromium.launch(

                    headless=
                        not HEADFUL,

                    args=[

                        "--disable-blink-features=AutomationControlled",

                        "--disable-dev-shm-usage",

                        "--no-sandbox",

                    ],
                )


            context = browser.new_context(

                    user_agent=
                        config.USER_AGENT,

                    locale="en-IN",

                    timezone_id="Asia/Kolkata",

                    viewport={

                        "width":
                            1366,

                        "height":
                            900,
                    },
                )


            context.add_init_script(
                """
                Object.defineProperty(
                    navigator,
                    'webdriver',
                    {
                        get: () => undefined
                    }
                );
                """
            )


            page = context.new_page()


            # ------------------------------------------------
            # BLOCK HEAVY RESOURCES
            # ------------------------------------------------

            def route_handler(
                route,
            ):

                resource_type = route.request.resource_type


                if resource_type in {

                    "image",

                    "font",

                    "media",

                }:

                    route.abort()

                else:

                    route.continue_()


            page.route(
                "**/*",
                route_handler,
            )


            try:

                for index, url in enumerate(
                    pages,
                    start=1,
                ):

                    try:

                        log.info(
                            "[%s] [%d/%d] opening %s",
                            self.source,
                            index,
                            len(pages),
                            url,
                        )


                        page.goto(

                            url,

                            wait_until="domcontentloaded",

                            timeout=config.PAGE_LOAD_TIMEOUT,
                        )


                        page.wait_for_timeout(
                            config.WAIT_AFTER_LOAD_MS
                        )


                        # ------------------------------------------------
                        # WAIT FOR PRODUCT LINKS
                        # ------------------------------------------------

                        try:

                            page.wait_for_selector(

                                "a[href*='/p/']",

                                timeout=10000,
                            )


                        except Exception:

                            log.warning(

                                "[%s] no product links found: %s",

                                self.source,

                                url,
                            )


                        # ------------------------------------------------
                        # SCROLL
                        # ------------------------------------------------

                        for _ in range(
                            config.SCROLLS_PER_PAGE
                        ):

                            page.mouse.wheel(
                                0,
                                2500,
                            )


                            page.wait_for_timeout(
                                config.WAIT_AFTER_SCROLL_MS
                            )


                        # ------------------------------------------------
                        # EXTRACT PRODUCT CARDS
                        # ------------------------------------------------

                        cards = page.evaluate(
                                PRODUCT_EXTRACTION_JS
                            )


                        parsed_count = 0


                        for card in cards:

                            href = card.get(
                                    "href",
                                    "",
                                )


                            text =card.get(
                                    "text",
                                    "",
                                )


                            hint = card.get(
                                    "hint",
                                    "",
                                )


                            # ------------------------------------------------
                            # ACTUAL DOM PRICE/MRP
                            # ------------------------------------------------

                            dom_price = card.get(
                                    "price"
                                )


                            dom_mrp = card.get(
                                    "mrp"
                                )


                            dom_discount = card.get(
                                    "discount"
                                )


                            price_source = card.get(
                                    "priceSource",
                                    "",
                                )


                            mrp_source = card.get(
                                    "mrpSource",
                                    "",
                                )


                            # ------------------------------------------------
                            # DEBUG OUTPUT
                            # ------------------------------------------------

                            if DEBUG:

                                dump.append(

                                    "\n".join(

                                        [

                                            f"URL: {href}",

                                            f"HINT: {hint}",

                                            f"DOM PRICE: {dom_price}",

                                            f"DOM MRP: {dom_mrp}",

                                            f"DOM DISCOUNT: {dom_discount}",

                                            f"PRICE SOURCE: {price_source}",

                                            f"MRP SOURCE: {mrp_source}",

                                            text,

                                            "-" * 80,

                                        ]
                                    )
                                )


                            # ------------------------------------------------
                            # PARSE DEAL
                            # ------------------------------------------------

                            deal = parse_card(

                                    self.source,

                                    href,

                                    text,

                                    hint,

                                    dom_price=
                                        dom_price,

                                    dom_mrp=
                                        dom_mrp,

                                    dom_discount=
                                        dom_discount,

                                    price_source=
                                        price_source,

                                    mrp_source=
                                        mrp_source,
                                )


                            if not deal:

                                continue


                            if (
                                deal.url
                                in seen_urls
                            ):

                                continue


                            seen_urls.add(
                                deal.url
                            )


                            deals.append(
                                deal
                            )


                            parsed_count += 1


                        log.info(

                            "[%s] [%d/%d] "
                            "cards=%d parsed=%d",

                            self.source,

                            index,

                            len(pages),

                            len(cards),

                            parsed_count,
                        )


                    except Exception as exc:

                        log.exception(

                            "[%s] page failed: %s",

                            self.source,

                            url,
                        )


            finally:

                browser.close()


        # ----------------------------------------------------
        # DEBUG FILE
        # ----------------------------------------------------

        if DEBUG:

            filename = f"debug_{self.source}.txt"


            with open(
                filename,
                "w",
                encoding="utf-8",
            ) as file:

                file.write(
                    "\n".join(
                        dump[:100]
                    )
                )


            log.info(

                "[%s] debug output written to %s",

                self.source,

                filename,
            )


        log.info(

            "[%s] TOTAL parsed deals=%d",

            self.source,

            len(deals),
        )


        return deals


# ============================================================
# FLIPKART
# ============================================================

class FlipkartBrowser(
    BrowserFetcher
):

    source ="flipkart"


    LINK_SELECTOR = "a[href*='/p/']"


    CARD_SELECTOR = ""


    def all_pages(
        self,
    ):

        pages = []


        for category in config.CATEGORIES_GENERAL:

            url = (

                "https://www.flipkart.com/search?"

                +

                urlencode(
                    {
                        "q":category,

                        "marketplace": "FLIPKART",
                    }
                )
            )


            pages.append(
                url
            )


        return pages


# ============================================================
# AMAZON
# ============================================================

class AmazonBrowser(
    BrowserFetcher
):

    source = "amazon"


    LINK_SELECTOR = "a[href*='/dp/']"


    CARD_SELECTOR ="div[data-component-type='s-search-result']"


    def all_pages(
        self,
    ):

        return []


# ============================================================
# MYNTRA
# ============================================================

class MyntraBrowser(
    BrowserFetcher
):

    source = "myntra"


    LINK_SELECTOR ="a[href$='/buy']"


    CARD_SELECTOR =""


    def all_pages(
        self,
    ):

        return []


# ============================================================
# AJIO
# ============================================================

class AjioBrowser(
    BrowserFetcher
):

    source ="ajio"


    LINK_SELECTOR = "a[href*='/p/']"


    CARD_SELECTOR = ""


    def all_pages(
        self,
    ):

        return []