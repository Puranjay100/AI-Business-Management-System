"""Unit tests for core/inventory_manager.py."""

from __future__ import annotations

import pytest

from core.inventory_manager import InventoryManager
from data.storage import Storage
from exceptions import (
    DuplicateProductError,
    InsufficientStockError,
    InvalidPriceError,
    InvalidQuantityError,
    ProductNotFoundError,
    ValidationError,
)


@pytest.fixture()
def manager() -> InventoryManager:
    return InventoryManager(Storage(":memory:"))


# ------------------------------------------------------------------
# add_product
# ------------------------------------------------------------------


def test_add_product_success(manager: InventoryManager) -> None:
    p = manager.add_product("Widget", 9.99, 100, "General")
    assert p.name == "Widget"
    assert p.price == 9.99
    assert p.quantity_in_stock == 100
    assert p.is_archived is False


def test_add_product_negative_price(manager: InventoryManager) -> None:
    with pytest.raises(InvalidPriceError):
        manager.add_product("Widget", -1.0, 10, "General")


def test_add_product_negative_quantity(manager: InventoryManager) -> None:
    with pytest.raises(InvalidQuantityError):
        manager.add_product("Widget", 5.0, -1, "General")


def test_add_product_zero_price_is_allowed(manager: InventoryManager) -> None:
    """Free products are valid (price = 0)."""
    p = manager.add_product("Freebie", 0.0, 10, "Promo")
    assert p.price == 0.0


def test_add_product_empty_name(manager: InventoryManager) -> None:
    with pytest.raises(ValidationError):
        manager.add_product("  ", 5.0, 10, "General")


def test_add_product_empty_category(manager: InventoryManager) -> None:
    with pytest.raises(ValidationError):
        manager.add_product("Widget", 5.0, 10, "")


def test_add_duplicate_product_name_same_category(manager: InventoryManager) -> None:
    manager.add_product("Widget", 5.0, 10, "General")
    with pytest.raises(DuplicateProductError):
        manager.add_product("Widget", 7.0, 5, "General")


def test_add_duplicate_product_name_different_category(manager: InventoryManager) -> None:
    manager.add_product("Widget", 5.0, 10, "Electronics")
    p2 = manager.add_product("Widget", 7.0, 5, "Clothing")
    assert p2.category == "Clothing"


# ------------------------------------------------------------------
# edit_product
# ------------------------------------------------------------------


def test_edit_product_updates_fields(manager: InventoryManager) -> None:
    p = manager.add_product("Widget", 5.0, 10, "General")
    edited = manager.edit_product(p.product_id, "Super Widget", 12.0, 20, "Premium")
    assert edited.name == "Super Widget"
    assert edited.price == 12.0
    assert edited.quantity_in_stock == 20
    assert edited.category == "Premium"


def test_edit_product_not_found(manager: InventoryManager) -> None:
    with pytest.raises(ProductNotFoundError):
        manager.edit_product("nonexistent", "X", 1.0, 1, "Cat")


# ------------------------------------------------------------------
# archive_product / get_product / list_products
# ------------------------------------------------------------------


def test_archive_product_hides_from_list(manager: InventoryManager) -> None:
    p = manager.add_product("Widget", 5.0, 10, "General")
    manager.archive_product(p.product_id)
    active = manager.list_products()
    assert all(prod.product_id != p.product_id for prod in active)


def test_archive_product_still_fetched_with_include_archived(
    manager: InventoryManager,
) -> None:
    p = manager.add_product("Widget", 5.0, 10, "General")
    manager.archive_product(p.product_id)
    all_products = manager.list_products(include_archived=True)
    assert any(prod.product_id == p.product_id for prod in all_products)


def test_get_product_not_found(manager: InventoryManager) -> None:
    with pytest.raises(ProductNotFoundError):
        manager.get_product("nonexistent")


def test_get_archived_product_raises(manager: InventoryManager) -> None:
    p = manager.add_product("Widget", 5.0, 10, "General")
    manager.archive_product(p.product_id)
    with pytest.raises(ProductNotFoundError):
        manager.get_product(p.product_id)


# ------------------------------------------------------------------
# low-stock
# ------------------------------------------------------------------


def test_low_stock_products(manager: InventoryManager) -> None:
    manager.add_product("LowItem", 1.0, 3, "A")
    manager.add_product("HighItem", 1.0, 100, "A")
    low = manager.get_low_stock_products(threshold=5)
    assert len(low) == 1
    assert low[0].name == "LowItem"


def test_low_stock_at_exact_threshold(manager: InventoryManager) -> None:
    manager.add_product("Exact", 1.0, 5, "A")
    low = manager.get_low_stock_products(threshold=5)
    assert len(low) == 1


# ------------------------------------------------------------------
# decrement_stock
# ------------------------------------------------------------------


def test_decrement_stock_success(manager: InventoryManager) -> None:
    p = manager.add_product("Widget", 5.0, 10, "General")
    manager.decrement_stock(p.product_id, 3)
    updated = manager.get_product(p.product_id)
    assert updated.quantity_in_stock == 7


def test_decrement_stock_below_zero(manager: InventoryManager) -> None:
    p = manager.add_product("Widget", 5.0, 2, "General")
    with pytest.raises(InsufficientStockError):
        manager.decrement_stock(p.product_id, 5)


def test_decrement_stock_exact_amount(manager: InventoryManager) -> None:
    p = manager.add_product("Widget", 5.0, 5, "General")
    manager.decrement_stock(p.product_id, 5)
    updated = manager.get_product(p.product_id)
    assert updated.quantity_in_stock == 0
