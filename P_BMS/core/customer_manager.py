"""CustomerManager — CRUD for customer records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from core.models import Customer
from data.storage import Storage
from exceptions import CustomerNotFoundError, ValidationError
from utils.formatters import validate_email, validate_phone


class CustomerManager:
    """Manages customer records with soft-delete support."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_customer_fields(name: str, email: str, phone: str) -> None:
        name = name.strip()
        if not name:
            raise ValidationError("Customer name must not be empty.")
        if len(name) > 100:
            raise ValidationError("Customer name must be 100 characters or fewer.")
        if not validate_email(email):
            raise ValidationError(f"'{email}' is not a valid email address.")
        if not validate_phone(phone):
            raise ValidationError(f"'{phone}' is not a valid phone number.")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_customer(
        self, name: str, email: str = "", phone: str = ""
    ) -> Customer:
        """Create and persist a new customer.

        Raises
        ------
        ValidationError
            If name is empty/too long, or email/phone format is invalid.
        """
        name = name.strip()
        self._validate_customer_fields(name, email, phone)

        customer = Customer(
            customer_id=str(uuid.uuid4()),
            name=name,
            email=email.strip(),
            phone=phone.strip(),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._storage.insert_customer(customer)
        return customer

    def edit_customer(
        self,
        customer_id: str,
        name: str,
        email: str,
        phone: str,
    ) -> Customer:
        """Update an existing customer's fields.

        Raises
        ------
        CustomerNotFoundError
            If the customer ID does not exist.
        ValidationError
            If any field is invalid.
        """
        name = name.strip()
        self._validate_customer_fields(name, email, phone)

        customer = self._storage.fetch_customer(customer_id)
        if customer is None or customer.is_archived:
            raise CustomerNotFoundError(f"Customer '{customer_id}' not found.")

        customer.name = name
        customer.email = email.strip()
        customer.phone = phone.strip()
        self._storage.update_customer(customer)
        return customer

    def archive_customer(self, customer_id: str) -> None:
        """Soft-delete a customer.

        Raises
        ------
        CustomerNotFoundError
            If the customer ID does not exist.
        """
        customer = self._storage.fetch_customer(customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer '{customer_id}' not found.")
        customer.is_archived = True
        self._storage.update_customer(customer)

    def get_customer(self, customer_id: str) -> Customer:
        """Return an active customer by ID.

        Raises
        ------
        CustomerNotFoundError
            If the customer does not exist or is archived.
        """
        customer = self._storage.fetch_customer(customer_id)
        if customer is None or customer.is_archived:
            raise CustomerNotFoundError(f"Customer '{customer_id}' not found.")
        return customer

    def list_customers(self, include_archived: bool = False) -> list[Customer]:
        """Return all customers, optionally including archived ones."""
        return self._storage.fetch_all_customers(include_archived=include_archived)
