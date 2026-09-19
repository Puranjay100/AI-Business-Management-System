"""InventoryManager — CRUD and stock management for products."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from core.models import Product
from data.storage import Storage
from exceptions import (
    DuplicateProductError,
    InsufficientStockError,
    InvalidPriceError,
    InvalidQuantityError,
    ProductNotFoundError,
    ValidationError,
)


class InventoryManager:
    """Manages the product catalogue and stock levels.

    All validation is performed here before any write reaches storage.
    """

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_product_fields(name: str, price: float, quantity: int, category: str) -> None:
        name = name.strip()
        if not name:
            raise ValidationError("Product name must not be empty.")
        if len(name) > 100:
            raise ValidationError("Product name must be 100 characters or fewer.")
        if not category.strip():
            raise ValidationError("Product category must not be empty.")
        if price < 0:
            raise InvalidPriceError(f"Price must be ≥ 0, got {price}.")
        if quantity < 0:
            raise InvalidQuantityError(f"Initial quantity must be ≥ 0, got {quantity}.")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_product(
        self, name: str, price: float, quantity: int, category: str
    ) -> Product:
        """Create and persist a new product.

        Raises
        ------
        ValidationError
            If name or category is empty / too long.
        InvalidPriceError
            If price is negative.
        InvalidQuantityError
            If initial quantity is negative.
        DuplicateProductError
            If an active product with the same name + category already exists.
        """
        name = name.strip()
        category = category.strip()
        self._validate_product_fields(name, price, quantity, category)

        existing = self._storage.fetch_all_products(include_archived=False)
        for p in existing:
            if p.name.lower() == name.lower() and p.category.lower() == category.lower():
                raise DuplicateProductError(
                    f"An active product named '{name}' in category '{category}' already exists."
                )

        product = Product(
            product_id=str(uuid.uuid4()),
            name=name,
            price=price,
            quantity_in_stock=quantity,
            category=category,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._storage.insert_product(product)
        return product

    def edit_product(
        self,
        product_id: str,
        name: str,
        price: float,
        quantity: int,
        category: str,
    ) -> Product:
        """Update an existing product's fields.

        Raises
        ------
        ProductNotFoundError
            If the product ID does not exist.
        DuplicateProductError
            If the new name + category combination belongs to a *different* active product.
        """
        name = name.strip()
        category = category.strip()
        self._validate_product_fields(name, price, quantity, category)

        product = self._storage.fetch_product(product_id)
        if product is None or product.is_archived:
            raise ProductNotFoundError(f"Product '{product_id}' not found.")

        # Check for duplicate among OTHER active products
        existing = self._storage.fetch_all_products(include_archived=False)
        for p in existing:
            if (
                p.product_id != product_id
                and p.name.lower() == name.lower()
                and p.category.lower() == category.lower()
            ):
                raise DuplicateProductError(
                    f"Another active product named '{name}' in '{category}' already exists."
                )

        product.name = name
        product.price = price
        product.quantity_in_stock = quantity
        product.category = category
        self._storage.update_product(product)
        return product

    def archive_product(self, product_id: str) -> None:
        """Soft-delete a product (sets is_archived = True).

        Raises
        ------
        ProductNotFoundError
            If the product ID does not exist.
        """
        product = self._storage.fetch_product(product_id)
        if product is None:
            raise ProductNotFoundError(f"Product '{product_id}' not found.")
        product.is_archived = True
        self._storage.update_product(product)

    def get_product(self, product_id: str) -> Product:
        """Return an active product by ID.

        Raises
        ------
        ProductNotFoundError
            If the product does not exist or is archived.
        """
        product = self._storage.fetch_product(product_id)
        if product is None or product.is_archived:
            raise ProductNotFoundError(f"Product '{product_id}' not found.")
        return product

    def list_products(self, include_archived: bool = False) -> list[Product]:
        """Return all products, optionally including archived ones."""
        return self._storage.fetch_all_products(include_archived=include_archived)

    def get_low_stock_products(self, threshold: Optional[int] = None) -> list[Product]:
        """Return active products whose stock is at or below *threshold*.

        If *threshold* is None the business default will be used by the caller;
        here we simply accept whatever integer is passed.
        """
        if threshold is None:
            threshold = 5
        return [
            p
            for p in self._storage.fetch_all_products(include_archived=False)
            if p.quantity_in_stock <= threshold
        ]

    def search_products(self, query: str) -> list[Product]:
        """Return active products whose name or category contains *query* (case-insensitive)."""
        q = query.strip().lower()
        return [
            p
            for p in self._storage.fetch_all_products(include_archived=False)
            if q in p.name.lower() or q in p.category.lower()
        ]

    def decrement_stock(self, product_id: str, quantity: int) -> None:
        """Reduce stock for *product_id* by *quantity*.

        Raises
        ------
        ProductNotFoundError
            If the product does not exist or is archived.
        InsufficientStockError
            If *quantity* exceeds current stock.
        """
        product = self.get_product(product_id)
        if product.quantity_in_stock < quantity:
            raise InsufficientStockError(
                f"Only {product.quantity_in_stock} units in stock; "
                f"cannot decrement by {quantity}."
            )
        product.quantity_in_stock -= quantity
        self._storage.update_product(product)
