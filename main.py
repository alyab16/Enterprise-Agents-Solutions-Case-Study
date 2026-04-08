from dotenv import load_dotenv
load_dotenv()

from app.tracing import setup_tracing
setup_tracing()

import threading
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.webhook import router as webhook_router
from app.api.demo import router as demo_router

logger = logging.getLogger(__name__)


def _warmup_sentiment_model():
    """Pre-load the DistilBERT sentiment model so the first user request
    doesn't block waiting for a ~250 MB download and weight initialisation.
    Runs in a daemon thread so it never delays server startup."""
    try:
        from app.integrations.sentiment import _load_model
        logger.info("Warming up sentiment model in background...")
        _load_model()
        logger.info("Sentiment model warm-up complete.")
    except Exception as exc:
        logger.warning("Sentiment model warm-up failed (keyword fallback will be used): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_warmup_sentiment_model, daemon=True).start()
    yield


app = FastAPI(
    title="Enterprise Onboarding Agent",
    description="AI-powered Customer Success onboarding automation",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(webhook_router)
app.include_router(demo_router, prefix="/demo", tags=["demo"])


@app.get("/health")
async def health():
    return {"ok": True, "service": "onboarding-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
