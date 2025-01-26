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
    size_at_level: Decimal # sequence info
    market_id: str
    asset_id: str
    yes_asset_id: str

@dataclass
class Order:
    id: str
    yes_side: str
    yes_price: Decimal
    remaining_size: Decimal
    size_at_level: Decimal
    request: OrderRequest
    status: str
    timestamp: int