"""Dataclasses representing the core domain models for the BMS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcnow() -> datetime:
    """Return current UTC time as a naive datetime (for SQLite compatibility)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class Business:
    """Business profile — one row in the database."""

    name: str
    owner: str
    currency: str  # ISO-4217 3-letter code, e.g. "USD"
    low_stock_threshold: int = 5


@dataclass
class Product:
    """A single inventory item."""

    product_id: str  # UUID4 string
    name: str
    price: float
    quantity_in_stock: int
    category: str
    is_archived: bool = False
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class Customer:
    """A named customer on record."""

    customer_id: str  # UUID4 string
    name: str
    email: str = ""
    phone: str = ""
    is_archived: bool = False
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class Sale:
    """An immutable sales transaction record."""

    sale_id: str  # UUID4 string
    product_id: str
    quantity_sold: int
    unit_price_at_sale: float  # price snapshot at time of sale
    total_amount: float  # quantity_sold * unit_price_at_sale
    sale_date: datetime
    customer_id: str | None = None  # None = walk-in sale
    notes: str = ""


@dataclass
class User:
    """An authenticated application user."""

    user_id: str
    username: str
    role: str  # "admin" | "staff"
