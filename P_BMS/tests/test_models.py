"""Unit tests for core/models.py."""

from datetime import datetime

from core.models import Business, Customer, Product, Sale, User


def test_sale_total_amount_reflects_inputs() -> None:
    sale = Sale(
        sale_id="s1",
        product_id="p1",
        quantity_sold=3,
        unit_price_at_sale=10.0,
        total_amount=30.0,
        sale_date=datetime(2024, 1, 15),
    )
    assert sale.total_amount == 30.0
    assert sale.quantity_sold * sale.unit_price_at_sale == sale.total_amount


def test_product_defaults() -> None:
    p = Product(
        product_id="p1",
        name="Widget",
        price=9.99,
        quantity_in_stock=10,
        category="General",
    )
    assert p.is_archived is False
    assert isinstance(p.created_at, datetime)


def test_customer_defaults() -> None:
    c = Customer(customer_id="c1", name="Alice")
    assert c.email == ""
    assert c.phone == ""
    assert c.is_archived is False
    assert isinstance(c.created_at, datetime)


def test_sale_walk_in_customer_is_none() -> None:
    sale = Sale(
        sale_id="s2",
        product_id="p1",
        quantity_sold=1,
        unit_price_at_sale=5.0,
        total_amount=5.0,
        sale_date=datetime(2024, 1, 1),
    )
    assert sale.customer_id is None


def test_business_low_stock_threshold_default() -> None:
    b = Business(name="Acme", owner="Alice", currency="USD")
    assert b.low_stock_threshold == 5


def test_user_role_field() -> None:
    u = User(user_id="u1", username="alice", role="admin")
    assert u.role == "admin"
