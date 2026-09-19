"""AI Business Management System — Streamlit entry point.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env (if present) before anything else
load_dotenv()

from auth.auth_manager import AuthManager
from core.customer_manager import CustomerManager
from core.inventory_manager import InventoryManager
from core.sales_manager import SalesManager
from data.storage import Storage
from ui import (
    page_customers,
    page_dashboard,
    page_insights,
    page_inventory,
    page_sales,
    page_settings,
)

# ------------------------------------------------------------------ #
# Page configuration
# ------------------------------------------------------------------ #
st.set_page_config(
    page_title="AI Business Management System",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------------ #
# Initialise singletons in session state (once per session)
# ------------------------------------------------------------------ #
def _init_session() -> None:
    if "storage" not in st.session_state:
        st.session_state["storage"] = Storage("bms.db")

    if "inventory" not in st.session_state:
        st.session_state["inventory"] = InventoryManager(st.session_state["storage"])

    if "customer_mgr" not in st.session_state:
        st.session_state["customer_mgr"] = CustomerManager(st.session_state["storage"])

    if "sales_mgr" not in st.session_state:
        st.session_state["sales_mgr"] = SalesManager(
            st.session_state["storage"], st.session_state["inventory"]
        )

    if "insights_engine" not in st.session_state:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            try:
                from ai.insights import InsightsEngine
                st.session_state["insights_engine"] = InsightsEngine(api_key=api_key)
            except Exception:
                st.session_state["insights_engine"] = None
        else:
            st.session_state["insights_engine"] = None


_init_session()

storage: Storage = st.session_state["storage"]
inventory: InventoryManager = st.session_state["inventory"]
customer_mgr: CustomerManager = st.session_state["customer_mgr"]
sales_mgr: SalesManager = st.session_state["sales_mgr"]
insights_engine = st.session_state["insights_engine"]

# ------------------------------------------------------------------ #
# Authentication
# ------------------------------------------------------------------ #
try:
    auth_manager = AuthManager("credentials.yaml")
except FileNotFoundError:
    st.error(
        "`credentials.yaml` not found. "
        "Create it from `credentials.yaml` with your user accounts."
    )
    st.stop()

name, auth_status, username = auth_manager.render_login_widget()

if auth_status is False:
    st.error("Incorrect username or password.")
    st.stop()

if not auth_status:
    st.info("Please log in to continue.")
    st.stop()

# Authenticated from here ─────────────────────────────────────────────
is_admin: bool = auth_manager.is_admin(username or "")  # type: ignore[arg-type]

# ------------------------------------------------------------------ #
# Sidebar — navigation + user info
# ------------------------------------------------------------------ #
with st.sidebar:
    st.title("🏢 BMS")
    st.caption(f"Logged in as **{name}** ({'Admin' if is_admin else 'Staff'})")
    auth_manager.render_logout_button(location="sidebar")
    st.divider()

    # Admin sees all pages; Staff only sees a subset
    all_pages = ["📊 Dashboard", "📦 Inventory", "👥 Customers", "🛒 Sales"]
    admin_pages = ["🤖 AI Insights", "⚙️ Settings"]

    pages = all_pages + (admin_pages if is_admin else [])
    page = st.radio("Navigate", pages, label_visibility="collapsed")

# ------------------------------------------------------------------ #
# Business profile (loaded fresh on every navigation)
# ------------------------------------------------------------------ #
business = storage.load_business()

# ------------------------------------------------------------------ #
# Page routing
# ------------------------------------------------------------------ #
if page == "📊 Dashboard":
    page_dashboard.render(sales_mgr, inventory, business)

elif page == "📦 Inventory":
    page_inventory.render(inventory, business, is_admin)

elif page == "👥 Customers":
    page_customers.render(customer_mgr, is_admin)

elif page == "🛒 Sales":
    page_sales.render(sales_mgr, inventory, customer_mgr, business)

elif page == "🤖 AI Insights" and is_admin:
    page_insights.render(sales_mgr, inventory, business, insights_engine, is_admin)

elif page == "⚙️ Settings" and is_admin:
    page_settings.render(storage, username or "", is_admin)

else:
    st.warning("Page not found or access denied.")
