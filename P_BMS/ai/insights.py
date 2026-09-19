"""InsightsEngine — AI-powered business summary using OpenAI gpt-4o-mini.

The engine is fully isolated: it receives pre-aggregated Python dicts from
the business logic layer and never touches the database or Streamlit.
"""

from __future__ import annotations

from typing import Any

from core.models import Business, Product


class InsightsEngine:
    """Builds a prompt from aggregated business data and calls the OpenAI API.

    Parameters
    ----------
    api_key:
        OpenAI API key.  Loaded from the environment by the caller — never
        hard-coded here.
    model:
        OpenAI chat model to use (default: ``"gpt-4o-mini"``).
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._model = model
        # Import lazily so the rest of the app works even if openai is not installed
        try:
            import openai  # type: ignore[import]

            self._client = openai.OpenAI(api_key=api_key)
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for AI insights. "
                "Install it with: pip install openai"
            ) from exc

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def build_prompt(
        self,
        business: Business,
        revenue_summary: dict[str, Any],
        best_sellers: list[dict[str, Any]],
        top_customers: list[dict[str, Any]],
        category_breakdown: dict[str, float],
        low_stock: list[Product],
    ) -> str:
        """Construct the user message that will be sent to the LLM.

        Only aggregated statistics are included — raw database records are
        never transmitted.
        """
        sellers_text = (
            ", ".join(
                f"{p['name']} ({p['units_sold']} units, "
                f"{business.currency} {p['revenue']:.2f})"
                for p in best_sellers
            )
            or "No sales recorded yet."
        )

        customers_text = (
            ", ".join(
                f"{c['name']} ({business.currency} {c['total_spent']:.2f})"
                for c in top_customers
            )
            or "No customer sales recorded yet."
        )

        categories_text = (
            ", ".join(
                f"{cat}: {business.currency} {rev:.2f}"
                for cat, rev in category_breakdown.items()
            )
            or "No sales recorded yet."
        )

        low_stock_text = (
            ", ".join(f"{p.name} ({p.quantity_in_stock} left)" for p in low_stock)
            or "None."
        )

        return (
            f"Business: {business.name}, Currency: {business.currency}\n"
            f"Total revenue all-time: {business.currency} {revenue_summary.get('total', 0):.2f}\n"
            f"Revenue this month: {business.currency} {revenue_summary.get('this_month', 0):.2f} "
            f"vs last month: {business.currency} {revenue_summary.get('last_month', 0):.2f}\n"
            f"Best-selling products: {sellers_text}\n"
            f"Top customers: {customers_text}\n"
            f"Sales by category: {categories_text}\n"
            f"Low-stock alerts: {low_stock_text}\n\n"
            "Please provide:\n"
            "1. A 2-sentence trend summary (this month vs last month).\n"
            "2. The single best-performing category and why.\n"
            "3. One actionable recommendation."
        )

    # ------------------------------------------------------------------
    # API call
    # ------------------------------------------------------------------

    def get_insights(self, prompt: str) -> str:
        """Send *prompt* to the OpenAI API and return the response text.

        Raises
        ------
        openai.APIError
            Propagated unchanged so the UI layer can catch and display it
            gracefully without crashing the app.
        """
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful business analyst. "
                        "Respond concisely in plain English. "
                        "Keep your response under 200 words."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.4,
        )
        return response.choices[0].message.content or ""
