from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.api.webhook import router as webhook_router
from app.api.demo import router as demo_router

app = FastAPI(
    title="Enterprise Onboarding Agent",
    description="AI-powered Customer Success onboarding automation",
    version="1.0.0"
)

app.include_router(webhook_router)
app.include_router(demo_router, prefix="/demo", tags=["demo"])


@app.get("/health")
async def health():
    return {"ok": True, "service": "onboarding-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
