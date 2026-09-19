"""Settings page — business profile and user management (Admin only)."""

from __future__ import annotations

import streamlit as st

from core.models import Business
from data.storage import Storage
from exceptions import ValidationError
from utils.formatters import validate_currency_code


def render(storage: Storage, username: str, is_admin: bool) -> None:
    st.header("⚙️ Business Settings")

    if not is_admin:
        st.warning("Only Admins can access this page.")
        return

    business = storage.load_business()

    st.subheader("Business Profile")
    with st.form("business_profile_form"):
        name = st.text_input("Business Name", value=business.name if business else "")
        owner = st.text_input("Owner Name", value=business.owner if business else "")
        currency = st.text_input(
            "Currency Code (ISO-4217, e.g. USD)",
            value=business.currency if business else "USD",
            max_chars=3,
        ).upper()
        threshold = st.number_input(
            "Low-Stock Alert Threshold (units)",
            min_value=0,
            value=business.low_stock_threshold if business else 5,
            step=1,
        )
        submitted = st.form_submit_button("Save Profile")

    if submitted:
        errors: list[str] = []
        if not name.strip():
            errors.append("Business name must not be empty.")
        if not owner.strip():
            errors.append("Owner name must not be empty.")
        if not validate_currency_code(currency):
            errors.append("Currency must be exactly 3 uppercase letters (e.g. USD).")
        if errors:
            for err in errors:
                st.error(err)
        else:
            storage.save_business(
                Business(
                    name=name.strip(),
                    owner=owner.strip(),
                    currency=currency,
                    low_stock_threshold=int(threshold),
                )
            )
            st.success("✅ Business profile saved.")
            st.rerun()

    st.divider()
    st.subheader("User Accounts")
    st.info(
        "User accounts are managed in `credentials.yaml`. "
        "To add a new user, add an entry under `credentials.usernames` "
        "with the desired username, plain-text password (auto-hashed on next start), "
        "email, name, and role (`admin` or `staff`)."
    )
