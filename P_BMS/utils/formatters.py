"""Formatting helpers and field validators used across layers."""

from __future__ import annotations

import re
from datetime import datetime


def format_currency(amount: float, currency_code: str) -> str:
    """Return a human-readable currency string, e.g. 'USD 1,250.00'."""
    return f"{currency_code.upper()} {amount:,.2f}"


def format_date(dt: datetime) -> str:
    """Return a consistent date string, e.g. '2024-06-15'."""
    return dt.strftime("%Y-%m-%d")


def validate_email(email: str) -> bool:
    """Return True if *email* is a plausible email address or is empty."""
    if not email:
        return True  # email is optional
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Return True if *phone* contains only digits, spaces, +, -, (, ) or is empty."""
    if not phone:
        return True  # phone is optional
    pattern = r"^[\d\s\+\-\(\)]+$"
    return bool(re.match(pattern, phone))


def validate_currency_code(code: str) -> bool:
    """Return True if *code* is exactly 3 uppercase ASCII letters."""
    return bool(re.match(r"^[A-Z]{3}$", code))
