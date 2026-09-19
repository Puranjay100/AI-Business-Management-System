"""Unit tests for ai/insights.py — all OpenAI calls are mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.models import Business, Product


# We patch openai.OpenAI at import time so InsightsEngine can be imported
# without a real API key.


@pytest.fixture()
def engine():
    """Return an InsightsEngine with a mocked OpenAI client."""
    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        from ai.insights import InsightsEngine  # noqa: PLC0415

        eng = InsightsEngine(api_key="test-key")
        eng._client = mock_client  # store for assertion access in tests
        return eng


def _business() -> Business:
    return Business(name="Acme Corp", owner="Alice", currency="USD")


def _revenue() -> dict:
    return {"total": 12500.0, "this_month": 3200.0, "last_month": 2800.0}


def _best_sellers() -> list[dict]:
    return [{"name": "Widget A", "units_sold": 120, "revenue": 2400.0}]


def _top_customers() -> list[dict]:
    return [{"customer_id": "c1", "name": "Bob", "total_spent": 4500.0}]


def _categories() -> dict:
    return {"Electronics": 7000.0, "Clothing": 5500.0}


def _low_stock() -> list[Product]:
    from core.models import Product
    from datetime import datetime
    return [
        Product(
            product_id="p99",
            name="Widget B",
            price=5.0,
            quantity_in_stock=2,
            category="Electronics",
            created_at=datetime(2024, 1, 1),
        )
    ]


# ------------------------------------------------------------------
# build_prompt
# ------------------------------------------------------------------


def test_build_prompt_contains_business_name(engine) -> None:
    prompt = engine.build_prompt(
        _business(), _revenue(), _best_sellers(), _top_customers(), _categories(), _low_stock()
    )
    assert "Acme Corp" in prompt


def test_build_prompt_contains_revenue(engine) -> None:
    prompt = engine.build_prompt(
        _business(), _revenue(), _best_sellers(), _top_customers(), _categories(), _low_stock()
    )
    assert "12500.00" in prompt


def test_build_prompt_contains_best_seller(engine) -> None:
    prompt = engine.build_prompt(
        _business(), _revenue(), _best_sellers(), _top_customers(), _categories(), _low_stock()
    )
    assert "Widget A" in prompt


def test_build_prompt_contains_low_stock(engine) -> None:
    prompt = engine.build_prompt(
        _business(), _revenue(), _best_sellers(), _top_customers(), _categories(), _low_stock()
    )
    assert "Widget B" in prompt


def test_build_prompt_empty_data_does_not_crash(engine) -> None:
    """When there are no sales yet the prompt should still be generated cleanly."""
    prompt = engine.build_prompt(
        _business(), {"total": 0, "this_month": 0, "last_month": 0}, [], [], {}, []
    )
    assert "Acme Corp" in prompt
    assert "No sales recorded yet" in prompt


# ------------------------------------------------------------------
# get_insights
# ------------------------------------------------------------------


def test_get_insights_calls_openai(engine) -> None:
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Great insight!"
    engine._client.chat.completions.create.return_value = mock_response

    engine.get_insights("some prompt")

    engine._client.chat.completions.create.assert_called_once()


def test_get_insights_returns_response_text(engine) -> None:
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Revenue is up 14% this month."
    engine._client.chat.completions.create.return_value = mock_response

    result = engine.get_insights("some prompt")

    assert result == "Revenue is up 14% this month."


def test_get_insights_api_failure_propagates(engine) -> None:
    """The engine must not swallow API errors — the UI catches them."""
    import openai  # type: ignore[import]

    engine._client.chat.completions.create.side_effect = openai.APIError(
        "rate limit", request=MagicMock(), body=None
    )

    with pytest.raises(openai.APIError):
        engine.get_insights("some prompt")
