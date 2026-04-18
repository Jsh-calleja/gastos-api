from fastapi import FastAPI
from sqlmodel import SQLModel
from app.db import engine
from app import models

# Importa explícitamente los routers que vas a usar
from app.routers import transactions, categories, accounts, recurring

app = FastAPI(title="Gastos API")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(accounts.router)
app.include_router(recurring.router)

@app.get("/health")
def health():
    return {"status": "ok"}
