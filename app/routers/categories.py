# app/routers/categories.py
# app/routers/categories.py
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, func
from sqlmodel import Session

from app.db import get_session
from app import models
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, session: Session = Depends(get_session)):
    cat = models.Category(**payload.dict())
    try:
        session.add(cat)
        session.commit()
        session.refresh(cat)
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to create category")
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
    try:
        session.add(db)
        session.commit()
        session.refresh(db)
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to update category")
    return db


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, session: Session = Depends(get_session)):
    """
    Prevent deleting a category that has transactions.
    If you prefer cascade delete, change this behavior intentionally.
    """
    cat = session.get(models.Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # check for related transactions
    tx_exists = session.exec(
        select(models.Transaction.id).where(models.Transaction.category_id == category_id).limit(1)
    ).first()
    if tx_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category has transactions and cannot be deleted"
        )

    try:
        session.delete(cat)
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete category")
    return


# -------------------------
# Small helper: totals per category for a month
# -------------------------
@router.get("/{category_id}/summary")
def category_month_summary(
    category_id: int,
    month: Optional[str] = Query(None, description="Month in YYYY-MM format. Defaults to current month."),
    session: Session = Depends(get_session),
):
    """
    Returns totals for the given category and month:
      { "category_id": int, "month": "YYYY-MM", "income": float, "expenses": float, "net": float }
    Classification depends on Transaction.type ('income' or 'expense').
    """
    cat = session.get(models.Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # determine month range
    if month:
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")
    else:
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)

    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)

    income_sum = session.exec(
        select(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .where(models.Transaction.category_id == category_id)
        .where(models.Transaction.type == "income")
        .where(models.Transaction.date >= start.date())
        .where(models.Transaction.date < end.date())
    ).one()

    expense_sum = session.exec(
        select(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .where(models.Transaction.category_id == category_id)
        .where(models.Transaction.type == "expense")
        .where(models.Transaction.date >= start.date())
        .where(models.Transaction.date < end.date())
    ).one()

    income = float(income_sum or 0.0)
    expenses = float(expense_sum or 0.0)
    net = income - expenses

    return {"category_id": category_id, "month": start.strftime("%Y-%m"), "income": income, "expenses": expenses, "net": net}
