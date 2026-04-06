"""
FastMCP server for Customer Sentiment Analysis.

Exposes sentiment scoring, trend analysis, and interaction logging as MCP tools.
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="sentiment",
    instructions=(
        "Customer sentiment analysis system. Analyses inbound customer "
        "interactions (emails, chat, support tickets) to produce sentiment "
        "scores and trend signals. Use to detect at-risk customers before "
        "task-level metrics show problems."
    ),
)


@mcp.tool()
def get_sentiment_score(account_id: str) -> dict:
    """
    Get the aggregate sentiment score for an account.

    Returns score (-1.0 to 1.0), label (positive/neutral/negative),
    interaction count, and recent interaction scores.
    """
    from app.integrations import sentiment

    return sentiment.get_sentiment_score(account_id)


@mcp.tool()
def get_sentiment_trend(account_id: str) -> dict:
    """
    Get the sentiment trend for an account (improving/stable/declining).

    Compares older vs. newer interactions to detect direction changes.
    """
    from app.integrations import sentiment

    return sentiment.get_sentiment_trend(account_id)


@mcp.tool()
def log_interaction(
    account_id: str,
    channel: str,
    direction: str,
    author: str,
    text: str,
) -> dict:
    """
    Record a customer interaction for sentiment tracking.

    Args:
        account_id: The account this interaction belongs to.
        channel: Communication channel (email, chat, support_ticket, call).
        direction: "inbound" (from customer) or "outbound" (from CS team).
        author: Who sent it — "customer" or "cs_team".
        text: The interaction content.
    """
    from app.integrations import sentiment

    return sentiment.add_interaction(account_id, channel, direction, author, text)


if __name__ == "__main__":
    mcp.run()
