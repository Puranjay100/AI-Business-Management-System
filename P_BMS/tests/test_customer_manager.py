"""Unit tests for core/customer_manager.py."""

from __future__ import annotations

import pytest

from core.customer_manager import CustomerManager
from data.storage import Storage
from exceptions import CustomerNotFoundError, ValidationError


@pytest.fixture()
def manager() -> CustomerManager:
    return CustomerManager(Storage(":memory:"))


# ------------------------------------------------------------------
# add_customer
# ------------------------------------------------------------------


def test_add_customer_success(manager: CustomerManager) -> None:
    c = manager.add_customer("Alice", "alice@example.com", "555-0100")
    assert c.name == "Alice"
    assert c.email == "alice@example.com"
    assert c.phone == "555-0100"
    assert c.is_archived is False


def test_add_customer_minimal(manager: CustomerManager) -> None:
    """Only name is required."""
    c = manager.add_customer("Bob")
    assert c.name == "Bob"
    assert c.email == ""
    assert c.phone == ""


def test_add_customer_empty_name(manager: CustomerManager) -> None:
    with pytest.raises(ValidationError):
        manager.add_customer("   ")


def test_add_customer_invalid_email(manager: CustomerManager) -> None:
    with pytest.raises(ValidationError):
        manager.add_customer("Alice", "not-an-email")


def test_add_customer_invalid_phone(manager: CustomerManager) -> None:
    with pytest.raises(ValidationError):
        manager.add_customer("Alice", "", "abc-not-a-phone")


def test_add_customer_valid_phone_formats(manager: CustomerManager) -> None:
    """Various phone formats should all be accepted."""
    c1 = manager.add_customer("Alice", "", "+1 800 555 1234")
    c2 = manager.add_customer("Bob", "", "(555) 123-4567")
    assert c1.phone == "+1 800 555 1234"
    assert c2.phone == "(555) 123-4567"


# ------------------------------------------------------------------
# edit_customer
# ------------------------------------------------------------------


def test_edit_customer_updates_fields(manager: CustomerManager) -> None:
    c = manager.add_customer("Alice")
    updated = manager.edit_customer(c.customer_id, "Alice Smith", "smith@example.com", "555-9999")
    assert updated.name == "Alice Smith"
    assert updated.email == "smith@example.com"
    assert updated.phone == "555-9999"


def test_edit_customer_not_found(manager: CustomerManager) -> None:
    with pytest.raises(CustomerNotFoundError):
        manager.edit_customer("nonexistent", "X", "", "")


# ------------------------------------------------------------------
# archive_customer / get_customer
# ------------------------------------------------------------------


def test_archive_customer_hides_from_list(manager: CustomerManager) -> None:
    c = manager.add_customer("Alice")
    manager.archive_customer(c.customer_id)
    active = manager.list_customers()
    assert all(cust.customer_id != c.customer_id for cust in active)


def test_archive_customer_included_with_flag(manager: CustomerManager) -> None:
    c = manager.add_customer("Alice")
    manager.archive_customer(c.customer_id)
    all_customers = manager.list_customers(include_archived=True)
    assert any(cust.customer_id == c.customer_id for cust in all_customers)


def test_get_customer_not_found(manager: CustomerManager) -> None:
    with pytest.raises(CustomerNotFoundError):
        manager.get_customer("nonexistent")


def test_get_archived_customer_raises(manager: CustomerManager) -> None:
    c = manager.add_customer("Alice")
    manager.archive_customer(c.customer_id)
    with pytest.raises(CustomerNotFoundError):
        manager.get_customer(c.customer_id)
