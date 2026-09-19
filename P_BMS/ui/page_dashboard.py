"""Dashboard page — KPI overview accessible to all roles."""

from __future__ import annotations

from datetime import datetime, timezone
from calendar import monthrange

import streamlit as st

from core.inventory_manager import InventoryManager
from core.models import Business
from core.sales_manager import SalesManager
from utils.formatters import format_currency


def render(
    sales_mgr: SalesManager,
    inventory: InventoryManager,
    business: Business | None,
) -> None:
    st.header("📊 Dashboard")

    if business is None:
        st.warning("Please configure your business profile in **Settings** first.")
        return

    currency = business.currency
    threshold = business.low_stock_threshold
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # ------------------------------------------------------------------ #
    # Date ranges for this month / last month
    # ------------------------------------------------------------------ #
    first_this_month = datetime(now.year, now.month, 1)
    last_month_end = first_this_month
    last_month_start = datetime(
        now.year if now.month > 1 else now.year - 1,
        now.month - 1 if now.month > 1 else 12,
        1,
    )

    revenue_all = sales_mgr.total_revenue()
    revenue_this_month = sales_mgr.total_revenue(
        start_date=first_this_month, end_date=now
    )
    revenue_last_month = sales_mgr.total_revenue(
        start_date=last_month_start, end_date=last_month_end
    )

    all_sales = sales_mgr.list_sales()
    low_stock = inventory.get_low_stock_products(threshold)
    best_sellers = sales_mgr.best_selling_products(top_n=1)
    top_product_name = best_sellers[0]["name"] if best_sellers else "—"

    # ------------------------------------------------------------------ #
    # KPI metrics row
    # ------------------------------------------------------------------ #
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue (all-time)", format_currency(revenue_all, currency))
    col2.metric(
        "Revenue This Month",
        format_currency(revenue_this_month, currency),
        delta=f"{format_currency(revenue_this_month - revenue_last_month, currency)} vs last month",
    )
    col3.metric("Total Sales", len(all_sales))
    col4.metric("Low-Stock Items ⚠️", len(low_stock))

    st.divider()

    # ------------------------------------------------------------------ #
    # Sales by category bar chart
    # ------------------------------------------------------------------ #
    st.subheader("Revenue by Category")
    category_data = sales_mgr.sales_by_category()
    if category_data:
        st.bar_chart(category_data)
    else:
        st.info("No sales data yet.")

    st.divider()

    # ------------------------------------------------------------------ #
    # Best sellers + top customers side by side
    # ------------------------------------------------------------------ #
    left, right = st.columns(2)

    with left:
        st.subheader("🏆 Best-Selling Products")
        best = sales_mgr.best_selling_products(top_n=5)
        if best:
            st.dataframe(
                [{"Product": b["name"], "Units Sold": b["units_sold"], "Revenue": format_currency(b["revenue"], currency)} for b in best],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No sales recorded yet.")

    with right:
        st.subheader("⭐ Top Customers")
        top = sales_mgr.top_customers(top_n=5)
        if top:
            st.dataframe(
                [{"Customer": t["name"], "Total Spent": format_currency(t["total_spent"], currency)} for t in top],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No customer sales recorded yet.")

    # ------------------------------------------------------------------ #
    # Low-stock table
    # ------------------------------------------------------------------ #
    if low_stock:
        st.divider()
        st.subheader(f"⚠️ Low-Stock Products (≤ {threshold} units)")
        st.dataframe(
            [{"Product": p.name, "Category": p.category, "Stock": p.quantity_in_stock} for p in low_stock],
            use_container_width=True,
            hide_index=True,
        )
