from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, categories, dashboard, products, qrcode, workspaces


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


app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(dashboard.router)
app.include_router(qrcode.router)
app.include_router(products.router)
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
