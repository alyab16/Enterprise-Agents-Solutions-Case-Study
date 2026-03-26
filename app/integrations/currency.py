"""
Currency conversion integration using the ExchangeRate API.

Uses the free open.er-api.com service for live exchange rates.
No API key required.

API docs: https://www.exchangerate-api.com/docs/free
"""

import httpx
from typing import Dict, Any

from app.logging.logger import log_event


EXCHANGE_RATE_BASE_URL = "https://open.er-api.com/v6/latest"


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> Dict[str, Any]:
    """
    Convert an amount between currencies using live exchange rates.

    Args:
        amount: The amount to convert.
        from_currency: ISO 4217 currency code (e.g. "USD").
        to_currency: ISO 4217 currency code (e.g. "CAD").

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
        }

    log_event(
        "currency.convert.request",
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
    )

    try:
        resp = httpx.get(
            f"{EXCHANGE_RATE_BASE_URL}/{from_currency}",
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

        rate = data["rates"][to_currency]
        converted_amount = round(amount * rate, 2)

        log_event(
            "currency.convert.success",
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
        )

        return {
            "status": "OK",
            "from": from_currency,
            "to": to_currency,
            "amount": amount,
            "converted_amount": converted_amount,
            "rate": round(rate, 6),
            "date": data.get("time_last_update_utc", ""),
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
