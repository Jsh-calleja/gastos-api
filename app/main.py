from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel
from app.db import engine
from app import models

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

# Frontend: static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", include_in_schema=False)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
