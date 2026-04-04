"""
Currency conversion integration using the Frankfurter API.

Supports both historical and latest exchange rates.
Uses the European Central Bank's published rates — no API key required.

API docs: https://frankfurter.dev
"""

import httpx
from typing import Dict, Any, Optional

from app.logging.logger import log_event


FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert an amount between currencies using exchange rates.

    When a date is provided (YYYY-MM-DD), uses the historical rate for that
    date. Otherwise falls back to the latest available rate.

    Args:
        amount: The amount to convert.
        from_currency: ISO 4217 currency code (e.g. "USD").
        to_currency: ISO 4217 currency code (e.g. "CAD").
        date: Optional date string (YYYY-MM-DD) for historical rate lookup.

    Returns:
        Dict with status, converted_amount, rate, and metadata.
        On failure, returns {"status": "API_ERROR", "error": "..."}.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return {
            "status": "OK",
            "from": from_currency,
            "to": to_currency,
            "amount": amount,
            "converted_amount": amount,
            "rate": 1.0,
            "date": date or "latest",
        }

    log_event(
        "currency.convert.request",
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
        date=date or "latest",
    )

    try:
        # Use historical endpoint if date provided, otherwise latest
        endpoint = date if date else "latest"
        resp = httpx.get(
            f"{FRANKFURTER_BASE_URL}/{endpoint}",
            params={"from": from_currency, "to": to_currency, "amount": amount},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if to_currency not in data.get("rates", {}):
            return {
                "status": "API_ERROR",
                "error": f"Unsupported currency: {to_currency}",
                "from": from_currency,
                "to": to_currency,
                "amount": amount,
            }

        converted_amount = round(data["rates"][to_currency], 2)
        rate = round(converted_amount / amount, 6) if amount else 0

        log_event(
            "currency.convert.success",
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            date=data.get("date", ""),
        )

        return {
            "status": "OK",
            "from": from_currency,
            "to": to_currency,
            "amount": amount,
            "converted_amount": converted_amount,
            "rate": rate,
            "date": data.get("date", ""),
        }

    except (httpx.HTTPError, KeyError) as e:
        log_event(
            "currency.convert.error",
            error=str(e),
            from_currency=from_currency,
            to_currency=to_currency,
        )
        return {
            "status": "API_ERROR",
            "error": f"Currency conversion failed: {e}",
            "from": from_currency,
            "to": to_currency,
            "amount": amount,
        }
