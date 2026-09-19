"""Unit tests for data/storage.py using an in-memory SQLite database."""

from __future__ import annotations

from datetime import datetime

import pytest

from core.models import Business, Customer, Product, Sale
from data.storage import Storage


@pytest.fixture()
def db() -> Storage:
    """Fresh in-memory database for each test."""
    return Storage(":memory:")


# ------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------


def test_init_schema_creates_tables(db: Storage) -> None:
    tables = {
        row[0]
        for row in db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"business", "products", "customers", "sales"}.issubset(tables)


# ------------------------------------------------------------------
# Business
# ------------------------------------------------------------------


def test_save_and_load_business(db: Storage) -> None:
    biz = Business(name="Acme", owner="Alice", currency="USD", low_stock_threshold=3)
    db.save_business(biz)
    loaded = db.load_business()
    assert loaded is not None
    assert loaded.name == "Acme"
    assert loaded.currency == "USD"
    assert loaded.low_stock_threshold == 3


def test_load_business_returns_none_when_empty(db: Storage) -> None:
    assert db.load_business() is None


def test_save_business_overwrites_existing(db: Storage) -> None:
    db.save_business(Business(name="Old", owner="X", currency="USD"))
    db.save_business(Business(name="New", owner="Y", currency="GBP"))
    loaded = db.load_business()
    assert loaded is not None
    assert loaded.name == "New"
    assert loaded.currency == "GBP"


# ------------------------------------------------------------------
# Products
# ------------------------------------------------------------------


def _make_product(pid: str = "p1") -> Product:
    return Product(
        product_id=pid,
        name="Widget",
        price=9.99,
        quantity_in_stock=50,
        category="General",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )


def test_insert_and_fetch_product(db: Storage) -> None:
    p = _make_product()
    db.insert_product(p)
    fetched = db.fetch_product("p1")
    assert fetched is not None
    assert fetched.product_id == "p1"
    assert fetched.name == "Widget"
    assert fetched.price == 9.99
    assert fetched.quantity_in_stock == 50
    assert fetched.is_archived is False


def test_fetch_product_not_found_returns_none(db: Storage) -> None:
    assert db.fetch_product("nonexistent") is None


def test_update_product(db: Storage) -> None:
    p = _make_product()
    db.insert_product(p)
    p.price = 19.99
    p.quantity_in_stock = 30
    db.update_product(p)
    fetched = db.fetch_product("p1")
    assert fetched is not None
    assert fetched.price == 19.99
    assert fetched.quantity_in_stock == 30


def test_fetch_all_products_excludes_archived_by_default(db: Storage) -> None:
    p1 = _make_product("p1")
    p2 = _make_product("p2")
    p2.is_archived = True
    db.insert_product(p1)
    db.insert_product(p2)
    active = db.fetch_all_products()
    assert len(active) == 1
    assert active[0].product_id == "p1"


def test_fetch_all_products_include_archived(db: Storage) -> None:
    p1 = _make_product("p1")
    p2 = _make_product("p2")
    p2.is_archived = True
    db.insert_product(p1)
    db.insert_product(p2)
    all_products = db.fetch_all_products(include_archived=True)
    assert len(all_products) == 2


# ------------------------------------------------------------------
# Customers
# ------------------------------------------------------------------


def _make_customer(cid: str = "c1") -> Customer:
    return Customer(
        customer_id=cid,
        name="Alice",
        email="alice@example.com",
        phone="555-1234",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )


def test_insert_and_fetch_customer(db: Storage) -> None:
    c = _make_customer()
    db.insert_customer(c)
    fetched = db.fetch_customer("c1")
    assert fetched is not None
    assert fetched.name == "Alice"
    assert fetched.email == "alice@example.com"


def test_fetch_customer_not_found_returns_none(db: Storage) -> None:
    assert db.fetch_customer("nonexistent") is None


# ------------------------------------------------------------------
# Sales
# ------------------------------------------------------------------


def _make_sale(sid: str = "s1", dt: datetime | None = None) -> Sale:
    return Sale(
        sale_id=sid,
        product_id="p1",
        customer_id="c1",
        quantity_sold=2,
        unit_price_at_sale=9.99,
        total_amount=19.98,
        sale_date=dt or datetime(2024, 6, 15, 10, 0, 0),
    )


def test_insert_and_fetch_sale(db: Storage) -> None:
    db.insert_sale(_make_sale())
    fetched = db.fetch_sale("s1")
    assert fetched is not None
    assert fetched.sale_id == "s1"
    assert fetched.quantity_sold == 2
    assert fetched.total_amount == 19.98


def test_fetch_sale_not_found_returns_none(db: Storage) -> None:
    assert db.fetch_sale("nonexistent") is None


def test_fetch_sales_in_range(db: Storage) -> None:
    db.insert_sale(_make_sale("s1", datetime(2024, 1, 10)))
    db.insert_sale(_make_sale("s2", datetime(2024, 3, 20)))
    db.insert_sale(_make_sale("s3", datetime(2024, 6, 5)))

    results = db.fetch_sales_in_range(
        datetime(2024, 2, 1), datetime(2024, 5, 1)
    )
    assert len(results) == 1
    assert results[0].sale_id == "s2"


def test_fetch_all_sales_returns_all(db: Storage) -> None:
    db.insert_sale(_make_sale("s1"))
    db.insert_sale(_make_sale("s2", datetime(2024, 7, 1)))
    assert len(db.fetch_all_sales()) == 2
