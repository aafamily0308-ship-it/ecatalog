from dataclasses import dataclass
from typing import Literal

ProductCondition = Literal["new", "used", "refurbished"]
OfferStatus = Literal["pending", "approved", "rejected"]
VALID_CONDITIONS = {"new", "used", "refurbished"}
VALID_OFFER_STATUSES = {"pending", "approved", "rejected"}


@dataclass(slots=True)
class ProductCreate:
    title: str
    brand: str | None
    category: str | None
    condition: ProductCondition


@dataclass(slots=True)
class SellerCreate:
    name: str
    city: str | None


@dataclass(slots=True)
class OfferCreate:
    product_id: int
    seller: SellerCreate
    price_azn: float
    currency: str = "AZN"
    url: str | None = None
    is_available: bool = True


@dataclass(slots=True)
class OfferStatusUpdate:
    status: OfferStatus
