import os
from pydantic_ai import Agent


def setup_tracing():
    """Initialize optional tracing backends. Each is opt-in via env vars."""

    # Logfire (native Pydantic AI tracing)
    if os.getenv("LOGFIRE_TOKEN"):
        import logfire
        logfire.configure()
        logfire.instrument_pydantic_ai()

    # LangSmith (via OTEL bridge)
    # configure_langsmith sets the global TracerProvider automatically,
    # so Agent.instrument_all() picks it up — no manual wiring needed.
    if os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY"):
        from langsmith.integrations.otel import configure as configure_langsmith
        project = os.getenv("LANGCHAIN_PROJECT", "onboarding-agent")
        configure_langsmith(project_name=project)
        Agent.instrument_all()
