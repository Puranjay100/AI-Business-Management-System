"""Inventory page — product CRUD and low-stock highlights."""

from __future__ import annotations

import streamlit as st

from core.inventory_manager import InventoryManager
from core.models import Business
from exceptions import (
    BmsBaseError,
    DuplicateProductError,
    InvalidPriceError,
    InvalidQuantityError,
    ValidationError,
)
from utils.formatters import format_currency


def render(
    inventory: InventoryManager,
    business: Business | None,
    is_admin: bool,
) -> None:
    st.header("📦 Inventory")

    currency = business.currency if business else "USD"
    threshold = business.low_stock_threshold if business else 5

    products = inventory.list_products()
    low_stock_ids = {p.product_id for p in inventory.get_low_stock_products(threshold)}

    # ------------------------------------------------------------------ #
    # Product table
    # ------------------------------------------------------------------ #
    if not products:
        st.info("No products yet. Add one below.")
    else:
        rows = []
        for p in products:
            rows.append(
                {
                    "ID": p.product_id,
                    "Name": p.name,
                    "Category": p.category,
                    "Price": format_currency(p.price, currency),
                    "Stock": p.quantity_in_stock,
                    "⚠️ Low Stock": "⚠️ Yes" if p.product_id in low_stock_ids else "",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

    if low_stock_ids:
        st.warning(
            f"⚠️ {len(low_stock_ids)} product(s) are at or below the low-stock threshold "
            f"({threshold} units)."
        )

    if not is_admin:
        st.caption("Staff can view inventory but cannot add, edit, or archive products.")
        return

    st.divider()

    # ------------------------------------------------------------------ #
    # Add / Edit form
    # ------------------------------------------------------------------ #
    st.subheader("Add / Edit Product")

    # Select product to edit (optional)
    edit_id: str | None = None
    if products:
        options = ["— Add new product —"] + [f"{p.name} ({p.product_id[:8]}…)" for p in products]
        choice = st.selectbox("Select a product to edit (or add a new one)", options)
        if choice != "— Add new product —":
            idx = options.index(choice) - 1
            edit_id = products[idx].product_id

    editing = edit_id is not None
    prefill = inventory.get_product(edit_id) if editing else None

    with st.form("product_form", clear_on_submit=True):
        name = st.text_input("Name", value=prefill.name if prefill else "")
        category = st.text_input("Category", value=prefill.category if prefill else "")
        price = st.number_input(
            "Price",
            min_value=0.0,
            value=float(prefill.price) if prefill else 0.0,
            step=0.01,
            format="%.2f",
        )
        quantity = st.number_input(
            "Quantity in Stock",
            min_value=0,
            value=int(prefill.quantity_in_stock) if prefill else 0,
            step=1,
        )
        save_btn = st.form_submit_button("💾 Save Product")
        archive_btn = (
            st.form_submit_button("🗑️ Archive Product") if editing else None
        )

    if save_btn:
        try:
            if editing and edit_id:
                inventory.edit_product(edit_id, name, price, int(quantity), category)
                st.success(f"✅ Product '{name}' updated.")
            else:
                inventory.add_product(name, price, int(quantity), category)
                st.success(f"✅ Product '{name}' added.")
            st.rerun()
        except BmsBaseError as exc:
            st.error(str(exc))

    if archive_btn and editing and edit_id:
        try:
            inventory.archive_product(edit_id)
            st.success("Product archived.")
            st.rerun()
        except BmsBaseError as exc:
            st.error(str(exc))
