from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from typing import List
from sqlmodel import Session
from app.db import get_session
from app.models import Category

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("/", response_model=Category)
def create_category(category: Category, session: Session = Depends(get_session)):
    session.add(category)
    session.commit()
    session.refresh(category)
    return category

@router.get("/", response_model=List[Category])
def list_categories(session: Session = Depends(get_session)):
    categories = session.exec(select(Category)).all()
    return categories
