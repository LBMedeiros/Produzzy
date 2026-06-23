from typing import Optional

from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal
from app import crud, models, schemas


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


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


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


@app.post(
    "/products",
    response_model=schemas.ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: schemas.ProductCreate,
    db: Session = Depends(get_db),
):
    return crud.create_product(product_data, db)


@app.get("/products", response_model=list[schemas.ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    return crud.list_products(
        db=db,
        category=category,
        search=search,
    )


@app.get("/products/low-stock", response_model=list[schemas.ProductResponse])
def list_low_stock_products(db: Session = Depends(get_db)):
    return crud.list_low_stock_products(db)


@app.get("/products/{product_id}", response_model=schemas.ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    return crud.get_product_by_id(product_id, db)


@app.patch("/products/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    product_data: schemas.ProductUpdate,
    db: Session = Depends(get_db),
):
    return crud.update_product(product_id, product_data, db)


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    crud.delete_product(product_id, db)

    return None


@app.post(
    "/products/{product_id}/stock",
    response_model=schemas.StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement(
    product_id: int,
    movement_data: schemas.StockMovementCreate,
    db: Session = Depends(get_db),
):
    return crud.create_stock_movement(product_id, movement_data, db)


@app.get(
    "/products/{product_id}/stock-movements",
    response_model=list[schemas.StockMovementResponse],
)
def list_product_stock_movements(
    product_id: int,
    db: Session = Depends(get_db),
):
    return crud.list_product_stock_movements(product_id, db)