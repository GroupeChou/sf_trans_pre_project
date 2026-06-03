"""API middleware — Auth, rate limiting, and tracing."""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class TraceMiddleware(BaseHTTPMiddleware):
    """Inject trace_id into every request for full-chain observability."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = request.headers.get("X-Trace-ID", f"tr_{uuid.uuid4().hex[:12]}")
        request.state.trace_id = trace_id
        request.state.start_time = time.monotonic()

        response = await call_next(request)

        duration_ms = int((time.monotonic() - request.state.start_time) * 1000)
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per tenant."""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID", "default")

        now = time.monotonic()
        if tenant_id not in self._buckets:
            self._buckets[tenant_id] = []

        self._buckets[tenant_id] = [
            t for t in self._buckets[tenant_id]
            if now - t < self.window_seconds
        ]

        if len(self._buckets[tenant_id]) >= self.max_requests:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after_seconds": self.window_seconds},
            )

        self._buckets[tenant_id].append(now)
        return await call_next(request)
