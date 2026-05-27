import time
import uuid
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from logging_config import request_id_var, setup_logging
from routers import cp_bites, my_problems, random_topic, telegram_notifications
from services.daily_my_problem_scheduler import daily_my_problem_telegram_scheduler

settings = get_settings()
setup_logging(settings.LOG_LEVEL)

logger = logging.getLogger(__name__)

app = FastAPI(title="Daily DSA Refresher", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(random_topic.router, prefix="/api")
app.include_router(my_problems.router, prefix="/api")
app.include_router(cp_bites.router, prefix="/api")
app.include_router(telegram_notifications.router, prefix="/api")


# ---------------------------------------------------------------------------
# Request-ID + access-log middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_var.set(request_id)

    start = time.perf_counter()
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query) or None,
            "client_ip": request.client.host if request.client else None,
        },
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.exception(
            "Unhandled exception escaped middleware",
            extra={"request_id": request_id, "duration_ms": duration_ms},
        )
        raise
    finally:
        request_id_var.reset(token)

    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    logger.log(
        level,
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up", extra={"provider": settings.LLM_PROVIDER})
    daily_my_problem_telegram_scheduler.start()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")
    await daily_my_problem_telegram_scheduler.stop()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
async def _count_problems() -> int:
    try:
        from routers.my_problems import _read_problem_records

        return len(await _read_problem_records())
    except Exception:
        return 0


@app.get("/api/health")
async def health():
    return {"status": "ok", "provider": settings.LLM_PROVIDER, "problems_count": await _count_problems()}


# ---------------------------------------------------------------------------
# Exception handlers — all failures are now logged before returning
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        "HTTP error",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "detail": str(exc.detail),
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "request_error", "detail": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Request validation error",
        extra={
            "method": request.method,
            "path": request.url.path,
            "detail": str(exc),
        },
    )
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled internal error",
        extra={
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred"},
    )
