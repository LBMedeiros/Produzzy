from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime


from app.database import engine, Base
from app import models


Base.metadata.create_all(bind=engine)


app = FastAPI()


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    quantity: int = Field(ge=0)
    minimum_quantity: int = Field(ge=0)
    location: str = Field(min_length=1)


class ProductUpdate(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    minimum_quantity: int = Field(ge=0)
    location: str = Field(min_length=1)


class StockUpdate(BaseModel):
    quantity: int = Field(ge=0)
    reason: str = Field(min_length=1)


products = [
    {
        "id": 1,
        "name": "Nós e Amarras",
        "category": "Especialidade Fundo Verde",
        "quantity": 20,
        "minimum_quantity": 50,
        "location": "Caixa 1"
    },
    {
        "id": 2,
        "name": "Acampamento 1",
        "category": "Especialidade Fundo Verde",
        "quantity": 65,
        "minimum_quantity": 50,
        "location": "Caixa 2"
    },
    {
        "id": 3,
        "name": "Arte de Acampar",
        "category": "Especialidade Fundo Verde",
        "quantity": 30,
        "minimum_quantity": 50,
        "location": "Caixa 3"
    }
]

next_product_id = 4

stock_movements = []


@app.get("/")
def home():
    return {"message": "Produzzy API rodando"}


@app.get("/status")
def status():
    return {
        "status": "online",
        "app": "Produzzy"
    }


@app.get("/products")
def get_products():
    return products


@app.post("/products")
def create_product(product: ProductCreate):
    global next_product_id

    new_product = {
        "id": next_product_id,
        **product.model_dump()
    }

    products.append(new_product)

    next_product_id += 1

    return new_product


@app.get("/products/low-stock")
def get_low_stock_products():
    low_stock_products = []

    for product in products:
        if product["quantity"] < product["minimum_quantity"]:
            low_stock_products.append(product)

    return low_stock_products


@app.patch("/products/{product_id}/stock")
def update_product_stock(product_id: int, stock: StockUpdate):
    if stock.quantity < 0:
        raise HTTPException(status_code=400, detail="A quantidade não pode ser negativa")
    
    
    for product in products:
        if product["id"] == product_id:
            previous_quantity = product["quantity"]

            product["quantity"] = stock.quantity

            movement = {
                "id": len(stock_movements) + 1,
                "product_id": product["id"],
                "product_name": product["name"],
                "previous_quantity": previous_quantity,
                "new_quantity": stock.quantity,
                "difference": stock.quantity - previous_quantity,
                "reason": stock.reason,
                "user": "Lucas",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            stock_movements.append(movement)

            return {
                "product": product,
                "movement": movement
            }


    raise HTTPException(status_code=404, detail="produto não encontrado")


@app.get("/stock-movements")
def get_stock_movements():
    return stock_movements


@app.get("/products/{product_id}/stock-movements")
def get_product_stock_movements(product_id: int):
    product_exists = False


    for product in products:
        if product["id"] == product_id:
            product_exists = True
            break


    if not product_exists:
        raise HTTPException(status_code=404, detail="produto não encontrado")
    

    product_movements = []


    for movement in stock_movements:
        if movement["product_id"] == product_id:
            product_movements.append(movement)


    return product_movements


@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    for product in products:
        if product["id"] == product_id:
            products.remove(product)
            return {"message": "produto removido com sucesso"}
        
    raise HTTPException(status_code=404, detail="produto não encontrado")
    

@app.put("/products/{product_id}")
def update_product(product_id: int, updated_product: ProductUpdate):
    for product in products:
        if product["id"] == product_id:
            product["name"] = updated_product.name
            product["category"] = updated_product.category
            product["minimum_quantity"] = updated_product.minimum_quantity
            product["location"] = updated_product.location

            return product
        
        raise HTTPException(status_code=404, detail="produto não encontrado")


@app.get("/products/{product_id}")
def get_product_by_id(product_id: int):
    for product in products:
        if product["id"] == product_id:
            return product

    raise HTTPException(status_code=404, detail="produto não encontrado")
