"""SalesManager — record transactions and compute analytics."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from core.inventory_manager import InventoryManager
from core.models import Sale
from data.storage import Storage
from exceptions import (
    CustomerNotFoundError,
    InvalidQuantityError,
    ProductNotFoundError,
    ValidationError,
)


class SalesManager:
    """Records immutable sales transactions and computes business analytics."""

    def __init__(self, storage: Storage, inventory: InventoryManager) -> None:
        self._storage = storage
        self._inventory = inventory

    # ------------------------------------------------------------------
    # Record a sale
    # ------------------------------------------------------------------

    def record_sale(
        self,
        product_id: str,
        quantity: int,
        sale_date: datetime,
        customer_id: Optional[str] = None,
        notes: str = "",
    ) -> Sale:
        """Validate inputs, decrement stock, and persist a new sale.

        Raises
        ------
        InvalidQuantityError
            If *quantity* is less than 1.
        ValidationError
            If *sale_date* is in the future.
        ProductNotFoundError
            If *product_id* does not match an active product.
        CustomerNotFoundError
            If *customer_id* is provided but does not match an active customer.
        InsufficientStockError
            If *quantity* exceeds available stock (raised by InventoryManager).
        """
        if quantity < 1:
            raise InvalidQuantityError(f"Quantity must be ≥ 1, got {quantity}.")

        if sale_date > datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValidationError("Sale date cannot be in the future.")

        # Validate product (also raises ProductNotFoundError if missing/archived)
        product = self._inventory.get_product(product_id)

        # Validate optional customer
        if customer_id is not None:
            customer = self._storage.fetch_customer(customer_id)
            if customer is None or customer.is_archived:
                raise CustomerNotFoundError(f"Customer '{customer_id}' not found.")

        # Decrement stock (raises InsufficientStockError if not enough)
        self._inventory.decrement_stock(product_id, quantity)

        total = round(product.price * quantity, 2)
        sale = Sale(
            sale_id=str(uuid.uuid4()),
            product_id=product_id,
            quantity_sold=quantity,
            unit_price_at_sale=product.price,
            total_amount=total,
            sale_date=sale_date,
            customer_id=customer_id,
            notes=notes,
        )
        self._storage.insert_sale(sale)
        return sale

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_sales(self) -> list[Sale]:
        """Return all sales, most recent first."""
        return self._storage.fetch_all_sales()

    def filter_sales(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        product_id: Optional[str] = None,
    ) -> list[Sale]:
        """Return sales matching the given filters.

        If both *start_date* and *end_date* are provided the database handles
        the range query; otherwise all sales are loaded and filtered in memory.
        """
        if start_date and end_date:
            # Swap silently if caller reverses order
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            sales = self._storage.fetch_sales_in_range(start_date, end_date)
        else:
            sales = self._storage.fetch_all_sales()

        if product_id:
            sales = [s for s in sales if s.product_id == product_id]

        return sales

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def total_revenue(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """Sum of total_amount across filtered sales."""
        sales = self.filter_sales(start_date=start_date, end_date=end_date)
        return round(sum(s.total_amount for s in sales), 2)

    def best_selling_products(self, top_n: int = 5) -> list[dict]:
        """Return top *top_n* products ranked by units sold.

        Each entry: ``{"product_id": ..., "name": ..., "units_sold": ..., "revenue": ...}``
        """
        units: dict[str, int] = defaultdict(int)
        revenue: dict[str, float] = defaultdict(float)

        for sale in self._storage.fetch_all_sales():
            units[sale.product_id] += sale.quantity_sold
            revenue[sale.product_id] += sale.total_amount

        ranked = sorted(units.items(), key=lambda x: x[1], reverse=True)[:top_n]

        result = []
        for pid, qty in ranked:
            # Try to get the product name (it may be archived)
            product = self._storage.fetch_product(pid)
            name = product.name if product else pid
            result.append(
                {
                    "product_id": pid,
                    "name": name,
                    "units_sold": qty,
                    "revenue": round(revenue[pid], 2),
                }
            )
        return result

    def top_customers(self, top_n: int = 5) -> list[dict]:
        """Return top *top_n* customers ranked by total spend.

        Walk-in sales (customer_id = None) are excluded.
        Each entry: ``{"customer_id": ..., "name": ..., "total_spent": ...}``
        """
        spent: dict[str, float] = defaultdict(float)

        for sale in self._storage.fetch_all_sales():
            if sale.customer_id is not None:
                spent[sale.customer_id] += sale.total_amount

        ranked = sorted(spent.items(), key=lambda x: x[1], reverse=True)[:top_n]

        result = []
        for cid, total in ranked:
            customer = self._storage.fetch_customer(cid)
            name = customer.name if customer else cid
            result.append(
                {
                    "customer_id": cid,
                    "name": name,
                    "total_spent": round(total, 2),
                }
            )
        return result

    def sales_by_category(self) -> dict[str, float]:
        """Return total revenue grouped by product category."""
        category_revenue: dict[str, float] = defaultdict(float)

        for sale in self._storage.fetch_all_sales():
            product = self._storage.fetch_product(sale.product_id)
            category = product.category if product else "Unknown"
            category_revenue[category] += sale.total_amount

        return {k: round(v, 2) for k, v in category_revenue.items()}
