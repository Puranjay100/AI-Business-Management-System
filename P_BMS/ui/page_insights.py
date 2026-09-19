"""Insights page — AI-generated business summary (Admin only)."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from ai.insights import InsightsEngine
from core.inventory_manager import InventoryManager
from core.models import Business
from core.sales_manager import SalesManager


def render(
    sales_mgr: SalesManager,
    inventory: InventoryManager,
    business: Business | None,
    insights_engine: InsightsEngine | None,
    is_admin: bool,
) -> None:
    st.header("🤖 AI Insights")

    if not is_admin:
        st.warning("Only Admins can access AI Insights.")
        return

    if insights_engine is None:
        st.error(
            "AI Insights are unavailable. "
            "Set `OPENAI_API_KEY` in your `.env` file and restart the app."
        )
        return

    if business is None:
        st.warning("Please configure your business profile in **Settings** first.")
        return

    st.write(
        "Click **Generate Insights** to get an AI-powered summary of your business "
        "performance. Only aggregated statistics are sent to the AI — no raw customer "
        "or transaction data."
    )

    if st.button("✨ Generate Insights", type="primary"):
        with st.spinner("Analysing your business data…"):
            try:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                first_this_month = datetime(now.year, now.month, 1)
                last_month_start = datetime(
                    now.year if now.month > 1 else now.year - 1,
                    now.month - 1 if now.month > 1 else 12,
                    1,
                )

                revenue_summary = {
                    "total": sales_mgr.total_revenue(),
                    "this_month": sales_mgr.total_revenue(
                        start_date=first_this_month, end_date=now
                    ),
                    "last_month": sales_mgr.total_revenue(
                        start_date=last_month_start, end_date=first_this_month
                    ),
                }

                best_sellers = sales_mgr.best_selling_products(top_n=5)
                top_customers = sales_mgr.top_customers(top_n=5)
                category_breakdown = sales_mgr.sales_by_category()
                low_stock = inventory.get_low_stock_products(business.low_stock_threshold)

                prompt = insights_engine.build_prompt(
                    business=business,
                    revenue_summary=revenue_summary,
                    best_sellers=best_sellers,
                    top_customers=top_customers,
                    category_breakdown=category_breakdown,
                    low_stock=low_stock,
                )

                insight_text = insights_engine.get_insights(prompt)
                st.session_state["last_insight"] = insight_text

            except Exception as exc:  # noqa: BLE001
                st.error(f"AI Insights unavailable: {exc}")

    if "last_insight" in st.session_state:
        st.subheader("📋 Latest Insight")
        st.info(st.session_state["last_insight"])
