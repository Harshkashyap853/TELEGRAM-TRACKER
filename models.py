from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Deal:
    source: str
    name: str
    price: float
    mrp: Optional[float]
    url: str

    discount_pct: Optional[float] = None

    pincodes: list[str] = field(default_factory=list)
    city: Optional[str] = None

    def __post_init__(self):
        if (
            self.discount_pct is None
            and self.mrp is not None
            and self.mrp > self.price
        ):
            self.discount_pct = round(
                ((self.mrp - self.price) / self.mrp) * 100
            )

    @property
    def deal_id(self) -> str:
        """
        Product identity.

        Do NOT include price here.

        If the price changes, it is still the same product.
        This prevents duplicate products from flooding the channel.
        """
        return f"{self.source}|{self.url}"