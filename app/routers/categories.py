# app/routers/categories.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel import Session

from app.db import get_session
from app import models
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, session: Session = Depends(get_session)):
    cat = models.Category.from_orm(payload)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat

@router.get("/", response_model=List[CategoryRead])
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(models.Category)).all()

@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, session: Session = Depends(get_session)):
    cat = session.get(models.Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat

@router.put("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, session: Session = Depends(get_session)):
    db = session.get(models.Category, category_id)
    if not db:
        raise HTTPException(status_code=404, detail="Category not found")
    update_data = payload.dict(exclude_unset=True)
    for key, val in update_data.items():
        setattr(db, key, val)
    session.add(db)
    session.commit()
    session.refresh(db)
    return db

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, session: Session = Depends(get_session)):
    cat = session.get(models.Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    session.delete(cat)
    session.commit()
    return
