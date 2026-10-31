import logging

import requests

from config import USER_AGENT, REQUEST_TIMEOUT
from models import Deal


log = logging.getLogger(__name__)


class BaseFetcher:

    source: str = ""

    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-IN,en;q=0.9",
        })

    def get(self, url, **kwargs):

        kwargs.setdefault(
            "timeout",
            REQUEST_TIMEOUT
        )

        response = self.session.get(
            url,
            **kwargs
        )

        response.raise_for_status()

        return response

    def fetch(self, address: dict) -> list[Deal]:

        raise NotImplementedError

    def safe_fetch(self, address: dict) -> list[Deal]:

        try:
            return self.fetch(address)

        except Exception as exc:

            log.exception(
                "[%s] fetch failed: %s",
                self.source,
                exc
            )

            return []


def to_float(text) -> float | None:

    if text is None:
        return None

    value = "".join(
        c
        for c in str(text)
        if c.isdigit() or c == "."
    )

    try:
        return float(value) if value else None

    except ValueError:
        return None