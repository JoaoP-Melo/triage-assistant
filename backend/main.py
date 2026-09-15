from fastapi import FastAPI
from app.auth.router import router as auth_router

app = FastAPI(title="Triage Assistant API", version="1.0.0")

app.include_router(auth_router)