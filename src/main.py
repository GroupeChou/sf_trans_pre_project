"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import TraceMiddleware, RateLimitMiddleware
from src.api.routes import router
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.app_name} v{settings.version}")
    print(f"LLM model: {settings.llm_model}")
    print(f"Skill timeout: {settings.skill_timeout_seconds}s")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="中转场地在线预测智能体平台 — Multi-tenant SaaS prediction agent platform",
    lifespan=lifespan,
)

app.add_middleware(TraceMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host=settings.host, port=settings.port, reload=settings.debug)
