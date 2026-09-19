"""Unit tests for core/sales_manager.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.customer_manager import CustomerManager
from core.inventory_manager import InventoryManager
from core.sales_manager import SalesManager
from data.storage import Storage
from exceptions import (
    CustomerNotFoundError,
    InsufficientStockError,
    InvalidQuantityError,
    ProductNotFoundError,
    ValidationError,
)


@pytest.fixture()
def managers() -> tuple[SalesManager, InventoryManager, CustomerManager]:
    db = Storage(":memory:")
    inv = InventoryManager(db)
    cust = CustomerManager(db)
    sales = SalesManager(db, inv)
    return sales, inv, cust


def _past(days: int = 1) -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


# ------------------------------------------------------------------
# record_sale
# ------------------------------------------------------------------


def test_record_sale_success(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 10.0, 50, "General")
    sale = sales.record_sale(p.product_id, 3, _past())
    assert sale.quantity_sold == 3
    assert sale.total_amount == 30.0
    assert sale.unit_price_at_sale == 10.0
    # Stock must have been decremented
    assert inv.get_product(p.product_id).quantity_in_stock == 47


def test_record_sale_decrements_stock(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 5.0, 10, "General")
    sales.record_sale(p.product_id, 10, _past())
    assert inv.get_product(p.product_id).quantity_in_stock == 0


def test_record_sale_insufficient_stock(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 5.0, 2, "General")
    with pytest.raises(InsufficientStockError):
        sales.record_sale(p.product_id, 5, _past())


def test_record_sale_zero_quantity(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 5.0, 10, "General")
    with pytest.raises(InvalidQuantityError):
        sales.record_sale(p.product_id, 0, _past())


def test_record_sale_unknown_product(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, _, _ = managers
    with pytest.raises(ProductNotFoundError):
        sales.record_sale("bad-id", 1, _past())


def test_record_sale_unknown_customer(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 5.0, 10, "General")
    with pytest.raises(CustomerNotFoundError):
        sales.record_sale(p.product_id, 1, _past(), customer_id="bad-cid")


def test_record_sale_walk_in_no_customer(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 5.0, 10, "General")
    sale = sales.record_sale(p.product_id, 1, _past())
    assert sale.customer_id is None


def test_record_sale_future_date(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 5.0, 10, "General")
    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    with pytest.raises(ValidationError):
        sales.record_sale(p.product_id, 1, future)


def test_record_sale_with_linked_customer(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, cust = managers
    p = inv.add_product("Widget", 5.0, 10, "General")
    c = cust.add_customer("Alice")
    sale = sales.record_sale(p.product_id, 2, _past(), customer_id=c.customer_id)
    assert sale.customer_id == c.customer_id


# ------------------------------------------------------------------
# total_revenue
# ------------------------------------------------------------------


def test_total_revenue_all_time(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 10.0, 100, "General")
    sales.record_sale(p.product_id, 2, _past(10))
    sales.record_sale(p.product_id, 3, _past(5))
    assert sales.total_revenue() == 50.0


def test_total_revenue_date_range(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 10.0, 100, "General")
    sales.record_sale(p.product_id, 1, _past(30))  # outside range
    sales.record_sale(p.product_id, 2, _past(5))   # inside range
    start = _past(10)
    end = datetime.now(timezone.utc).replace(tzinfo=None)
    assert sales.total_revenue(start_date=start, end_date=end) == 20.0


# ------------------------------------------------------------------
# best_selling_products
# ------------------------------------------------------------------


def test_best_selling_products_ordering(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p1 = inv.add_product("A", 1.0, 100, "Cat")
    p2 = inv.add_product("B", 1.0, 100, "Cat")
    sales.record_sale(p1.product_id, 5, _past(2))
    sales.record_sale(p2.product_id, 10, _past(1))
    best = sales.best_selling_products(top_n=2)
    assert best[0]["name"] == "B"
    assert best[1]["name"] == "A"


# ------------------------------------------------------------------
# top_customers
# ------------------------------------------------------------------


def test_top_customers_ordering(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, cust = managers
    p = inv.add_product("Widget", 10.0, 100, "General")
    c1 = cust.add_customer("Alice")
    c2 = cust.add_customer("Bob")
    sales.record_sale(p.product_id, 1, _past(3), customer_id=c1.customer_id)
    sales.record_sale(p.product_id, 5, _past(2), customer_id=c2.customer_id)
    top = sales.top_customers(top_n=2)
    assert top[0]["name"] == "Bob"
    assert top[1]["name"] == "Alice"


def test_top_customers_excludes_walk_in(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p = inv.add_product("Widget", 10.0, 100, "General")
    sales.record_sale(p.product_id, 1, _past())  # walk-in
    top = sales.top_customers()
    assert top == []


# ------------------------------------------------------------------
# sales_by_category
# ------------------------------------------------------------------


def test_sales_by_category(
    managers: tuple[SalesManager, InventoryManager, CustomerManager],
) -> None:
    sales, inv, _ = managers
    p1 = inv.add_product("A", 10.0, 100, "Electronics")
    p2 = inv.add_product("B", 5.0, 100, "Clothing")
    sales.record_sale(p1.product_id, 2, _past(2))  # 20.0
    sales.record_sale(p2.product_id, 4, _past(1))  # 20.0
    breakdown = sales.sales_by_category()
    assert breakdown["Electronics"] == 20.0
    assert breakdown["Clothing"] == 20.0
