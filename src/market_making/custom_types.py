from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass
class PriceLevel:
    price: Decimal
    size: Decimal

    def total_value(self) -> Decimal:
        """Calculate the total value (price * size) at this price level."""
        return self.price * self.size

@dataclass
class OrderRequest:
    side: str
    price: Decimal
    size: Decimal
    size_at_level: Decimal
    market_id: str
    asset_id: str
    yes_asset_id: str

@dataclass
class Order:
    id: str
    request: OrderRequest
    status: str
    timestamp: int