"""
FastMCP server for currency conversion.

Exposes live exchange rate conversion as an MCP tool. Wraps the
Frankfurter API integration module. Can run as a standalone MCP
service or be consumed by the onboarding agent in-process.

Tools:
- convert_currency: Convert an amount between two currencies
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="currency",
    instructions=(
        "Currency conversion service using live ECB exchange rates. "
        "Use this to convert monetary amounts between currencies — "
        "for example, converting USD invoice totals to CAD."
    ),
)


@mcp.tool()
def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> dict:
    """
    Convert an amount from one currency to another using live rates.

    Uses the European Central Bank's published exchange rates via
    the Frankfurter API. No API key required.

    Args:
        amount: The monetary amount to convert.
        from_currency: Source currency code (e.g. "USD").
        to_currency: Target currency code (e.g. "CAD").

    Returns:
        Dict with converted_amount, exchange rate, and date.
    """
    from app.integrations import currency

    return currency.convert_currency(amount, from_currency, to_currency)


if __name__ == "__main__":
    mcp.run()
