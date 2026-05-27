from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from routers import cp_bites, my_problems, random_topic, telegram_notifications
from services.daily_my_problem_scheduler import daily_my_problem_telegram_scheduler

settings = get_settings()

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


@app.on_event("startup")
async def startup_event():
    daily_my_problem_telegram_scheduler.start()


@app.on_event("shutdown")
async def shutdown_event():
    await daily_my_problem_telegram_scheduler.stop()


async def _count_problems() -> int:
    try:
        from routers.my_problems import _read_problem_records

        return len(await _read_problem_records())
    except Exception:
        return 0


@app.get("/api/health")
async def health():
    return {"status": "ok", "provider": settings.LLM_PROVIDER, "problems_count": await _count_problems()}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "request_error", "detail": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred"},
    )
