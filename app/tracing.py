import os
from pydantic_ai import Agent


def setup_tracing():
    """Initialize optional tracing backends. Each is opt-in via env vars."""

    logfire_enabled = bool(os.getenv("LOGFIRE_TOKEN"))
    langsmith_enabled = bool(
        os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    )

    # Logfire (native Pydantic AI tracing)
    if logfire_enabled:
        import logfire
        logfire.configure()
        logfire.instrument_pydantic_ai()

    # LangSmith (via OTEL bridge)
    if langsmith_enabled:
        project = os.getenv("LANGCHAIN_PROJECT", "onboarding-agent")

        if logfire_enabled:
            # Logfire already owns the TracerProvider — add LangSmith as a
            # span processor on the existing provider instead of replacing it.
            from opentelemetry import trace
            from langsmith.integrations.otel import OtelSpanProcessor

            provider = trace.get_tracer_provider()
            provider.add_span_processor(OtelSpanProcessor(project=project))
        else:
            # No existing provider — let LangSmith set up its own.
            from langsmith.integrations.otel import configure as configure_langsmith
            configure_langsmith(project_name=project)

        Agent.instrument_all()
