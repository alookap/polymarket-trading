from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass
class PriceLevel:
    price: Decimal
    size: Decimal

@dataclass
class OrderRequest:
    side: str
    price: Decimal
    size: Decimal
    market_id: str
    asset_id: str

@dataclass
class Order:
    id: str
    request: OrderRequest
    status: str
    timestamp: int