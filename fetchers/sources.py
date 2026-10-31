"""
Registry of currently enabled deal fetchers.

Flipkart is the first source being developed.
Other platforms will be enabled after Flipkart is stable.
"""

from .browser import FlipkartBrowser


ALL_FETCHERS = [
    FlipkartBrowser(),
]