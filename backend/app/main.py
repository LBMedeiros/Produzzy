import logging
from time import perf_counter

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import PRODUZZY_ALLOWED_ORIGINS, PRODUZZY_API_VERSION
from app.database import engine
from app.routers import (
    audit_logs,
    auth,
    categories,
    dashboard,
    products,
    qrcode,
    replenishment,
    search,
    workspaces,
    stock_movements,
)


CORS_PREFLIGHT_MAX_AGE_SECONDS = 600
REQUEST_TIMING_QUIET_PATHS = {"/health"}
EXPOSED_RESPONSE_HEADERS = [
    "X-Process-Time-Ms",
    "X-Produzzy-API-Version",
]
logger = logging.getLogger(__name__)
request_logger = logging.getLogger("produzzy.requests")

app = FastAPI(
    title="Produzzy API",
    description="API para controle de estoque e produção.",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=PRODUZZY_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=EXPOSED_RESPONSE_HEADERS,
    max_age=CORS_PREFLIGHT_MAX_AGE_SECONDS,
)


@app.middleware("http")
async def add_request_timing(request: Request, call_next):
    started_at = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        duration_ms = round((perf_counter() - started_at) * 1000)
        request_logger.exception(
            "%s %s %s %sms",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
        )
        response = JSONResponse(
            status_code=status_code,
            content={"detail": "Erro interno do servidor."},
        )
        response.headers["X-Process-Time-Ms"] = str(duration_ms)
        response.headers["X-Produzzy-API-Version"] = PRODUZZY_API_VERSION
        return response

    duration_ms = round((perf_counter() - started_at) * 1000)
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    response.headers["X-Produzzy-API-Version"] = PRODUZZY_API_VERSION

    if request.url.path not in REQUEST_TIMING_QUIET_PATHS:
        request_logger.info(
            "%s %s %s %sms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

    return response


app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(audit_logs.router)
app.include_router(dashboard.router)
app.include_router(qrcode.router)
app.include_router(products.router)
app.include_router(stock_movements.router)
app.include_router(categories.router)
app.include_router(replenishment.router)
app.include_router(search.router)


@app.get("/")
def root():
    return {
        "message": "Produzzy API está rodando.",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "API funcionando corretamente.",
        "api_version": PRODUZZY_API_VERSION,
    }


@app.get("/ready")
def readiness_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Readiness check failed.")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready"},
        )

    return {"status": "ready"}
