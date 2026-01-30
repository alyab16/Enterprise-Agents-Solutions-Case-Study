from dotenv import load_dotenv
load_dotenv()

import langchain
from fastapi import FastAPI
from app.api.webhook import router as webhook_router

app = FastAPI(title="Enterprise Onboarding Agent")
app.include_router(webhook_router)


@app.get("/health")
async def health():
    return {"ok": True}
