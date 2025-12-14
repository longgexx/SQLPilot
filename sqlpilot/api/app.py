from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlpilot.api.routes import optimize, health

app = FastAPI(
    title="SQLPilot API",
    description="LLM Agent based SQL optimization and verification platform",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(optimize.router, prefix="/api/v1", tags=["optimize"])
app.include_router(health.router, tags=["health"])
