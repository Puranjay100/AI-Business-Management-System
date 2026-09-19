"""Customers page — customer CRUD (Admin only for add/edit/archive)."""

from __future__ import annotations

import streamlit as st

from core.customer_manager import CustomerManager
from exceptions import BmsBaseError


def render(customer_mgr: CustomerManager, is_admin: bool) -> None:
    st.header("👥 Customers")

    customers = customer_mgr.list_customers()

    # ------------------------------------------------------------------ #
    # Customer table
    # ------------------------------------------------------------------ #
    if not customers:
        st.info("No customers yet. Add one below.")
    else:
        rows = [
            {
                "ID": c.customer_id,
                "Name": c.name,
                "Email": c.email or "—",
                "Phone": c.phone or "—",
                "Since": c.created_at.strftime("%Y-%m-%d"),
            }
            for c in customers
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    if not is_admin:
        st.caption("Staff can view customers but cannot add, edit, or archive them.")
        return

    st.divider()

    # ------------------------------------------------------------------ #
    # Add / Edit form
    # ------------------------------------------------------------------ #
    st.subheader("Add / Edit Customer")

    edit_id: str | None = None
    if customers:
        options = ["— Add new customer —"] + [
            f"{c.name} ({c.customer_id[:8]}…)" for c in customers
        ]
        choice = st.selectbox("Select a customer to edit (or add a new one)", options)
        if choice != "— Add new customer —":
            idx = options.index(choice) - 1
            edit_id = customers[idx].customer_id

    editing = edit_id is not None
    prefill = customer_mgr.get_customer(edit_id) if editing else None

    with st.form("customer_form", clear_on_submit=True):
        name = st.text_input("Full Name", value=prefill.name if prefill else "")
        email = st.text_input("Email (optional)", value=prefill.email if prefill else "")
        phone = st.text_input("Phone (optional)", value=prefill.phone if prefill else "")
        save_btn = st.form_submit_button("💾 Save Customer")
        archive_btn = st.form_submit_button("🗑️ Archive Customer") if editing else None

    if save_btn:
        try:
            if editing and edit_id:
                customer_mgr.edit_customer(edit_id, name, email, phone)
                st.success(f"✅ Customer '{name}' updated.")
            else:
                customer_mgr.add_customer(name, email, phone)
                st.success(f"✅ Customer '{name}' added.")
            st.rerun()
        except BmsBaseError as exc:
            st.error(str(exc))

    if archive_btn and editing and edit_id:
        try:
            customer_mgr.archive_customer(edit_id)
            st.success("Customer archived.")
            st.rerun()
        except BmsBaseError as exc:
            st.error(str(exc))
