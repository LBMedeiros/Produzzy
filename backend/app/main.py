from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import PRODUZZY_ALLOWED_ORIGINS
from app.routers import (
    audit_logs,
    auth,
    categories,
    dashboard,
    products,
    qrcode,
    workspaces,
    stock_movements,
)


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
)


app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(audit_logs.router)
app.include_router(dashboard.router)
app.include_router(qrcode.router)
app.include_router(products.router)
app.include_router(stock_movements.router)
app.include_router(categories.router)


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
    }
