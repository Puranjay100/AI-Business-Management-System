"""Sales page — record transactions and view history with filters."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

from core.customer_manager import CustomerManager
from core.inventory_manager import InventoryManager
from core.models import Business
from core.sales_manager import SalesManager
from exceptions import BmsBaseError
from utils.formatters import format_currency


def render(
    sales_mgr: SalesManager,
    inventory: InventoryManager,
    customer_mgr: CustomerManager,
    business: Business | None,
) -> None:
    st.header("🛒 Sales")

    currency = business.currency if business else "USD"
    products = inventory.list_products()
    customers = customer_mgr.list_customers()

    # ------------------------------------------------------------------ #
    # Record a new sale
    # ------------------------------------------------------------------ #
    st.subheader("Record New Sale")

    if not products:
        st.warning("No products available. Add products first.")
    else:
        with st.form("record_sale_form", clear_on_submit=True):
            product_options = {f"{p.name} — {format_currency(p.price, currency)} (stock: {p.quantity_in_stock})": p for p in products}
            product_label = st.selectbox("Product", list(product_options.keys()))
            selected_product = product_options[product_label]

            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

            # Show computed total live
            computed_total = selected_product.price * quantity
            st.caption(f"Total: {format_currency(computed_total, currency)}")

            # Optional customer
            customer_options = {"— Walk-in (no customer) —": None}
            for c in customers:
                customer_options[f"{c.name} ({c.email or c.phone or c.customer_id[:8]})"] = c
            customer_label = st.selectbox("Customer (optional)", list(customer_options.keys()))
            selected_customer = customer_options[customer_label]

            sale_date_input = st.date_input("Sale Date", value=date.today())
            notes = st.text_input("Notes (optional)", "")
            submit_btn = st.form_submit_button("✅ Record Sale")

        if submit_btn:
            try:
                sale_dt = datetime.combine(sale_date_input, datetime.min.time())
                sale = sales_mgr.record_sale(
                    product_id=selected_product.product_id,
                    quantity=int(quantity),
                    sale_date=sale_dt,
                    customer_id=selected_customer.customer_id if selected_customer else None,
                    notes=notes,
                )
                st.success(
                    f"✅ Sale recorded: {int(quantity)} × {selected_product.name} = "
                    f"{format_currency(sale.total_amount, currency)}"
                )
                st.rerun()
            except BmsBaseError as exc:
                st.error(str(exc))

    st.divider()

    # ------------------------------------------------------------------ #
    # Sales history with filters
    # ------------------------------------------------------------------ #
    st.subheader("Sales History")

    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input(
            "From",
            value=date.today() - timedelta(days=30),
            key="sales_start",
        )
    with col2:
        end_date = st.date_input("To", value=date.today(), key="sales_end")
    with col3:
        filter_product = st.selectbox(
            "Filter by Product",
            ["All"] + [p.name for p in products],
            key="sales_prod_filter",
        )

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    product_id_filter: str | None = None
    if filter_product != "All":
        matched = [p for p in products if p.name == filter_product]
        if matched:
            product_id_filter = matched[0].product_id

    filtered = sales_mgr.filter_sales(
        start_date=start_dt, end_date=end_dt, product_id=product_id_filter
    )

    # Build a product name lookup (include archived)
    all_products = inventory.list_products(include_archived=True)
    pid_to_name = {p.product_id: p.name for p in all_products}

    all_customers = customer_mgr.list_customers(include_archived=True)
    cid_to_name = {c.customer_id: c.name for c in all_customers}

    if not filtered:
        st.info("No sales found for the selected filters.")
    else:
        rows = [
            {
                "Date": s.sale_date.strftime("%Y-%m-%d"),
                "Product": pid_to_name.get(s.product_id, s.product_id),
                "Qty": s.quantity_sold,
                "Unit Price": format_currency(s.unit_price_at_sale, currency),
                "Total": format_currency(s.total_amount, currency),
                "Customer": cid_to_name.get(s.customer_id, "Walk-in") if s.customer_id else "Walk-in",
                "Notes": s.notes or "",
            }
            for s in filtered
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

        total = sum(s.total_amount for s in filtered)
        st.metric("Total Revenue (filtered)", format_currency(total, currency))
