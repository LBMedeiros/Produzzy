from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app import models
from app.routers import products


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Produzzy API",
    description="API para controle de estoque e produção.",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Depois podemos trocar pelo domínio real do front-end
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(products.router)


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