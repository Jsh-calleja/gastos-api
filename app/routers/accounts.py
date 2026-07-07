# app/routers/accounts.py
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, func
from sqlmodel import Session

from app.db import get_session
from app import models
from app.schemas import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, session: Session = Depends(get_session)):
    acc = models.Account(**payload.dict())
    try:
        session.add(acc)
        session.commit()
        session.refresh(acc)
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to create account")
    return acc


@router.get("/", response_model=List[AccountRead])
def list_accounts(session: Session = Depends(get_session)):
    return session.exec(select(models.Account)).all()


@router.get("/with-balances", response_model=List[AccountRead])
def list_accounts_with_balances(session: Session = Depends(get_session)):
    """
    Return accounts with their stored balance field.
    If you want a computed balance (base + transactions), see the example below or extend this endpoint.
    """
    return session.exec(select(models.Account)).all()


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, session: Session = Depends(get_session)):
    acc = session.get(models.Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


@router.put("/{account_id}", response_model=AccountRead)
def update_account(account_id: int, payload: AccountUpdate, session: Session = Depends(get_session)):
    db = session.get(models.Account, account_id)
    if not db:
        raise HTTPException(status_code=404, detail="Account not found")
    update_data = payload.dict(exclude_unset=True)
    for key, val in update_data.items():
        setattr(db, key, val)
    try:
        session.add(db)
        session.commit()
        session.refresh(db)
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to update account")
    return db


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, session: Session = Depends(get_session)):
    """
    Prevent deleting an account that has transactions.
    If you prefer cascade delete, change this behavior intentionally.
    """
    acc = session.get(models.Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    # check for related transactions
    tx_exists = session.exec(
        select(models.Transaction.id).where(models.Transaction.account_id == account_id).limit(1)
    ).first()
    if tx_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account has transactions and cannot be deleted"
        )

    try:
        session.delete(acc)
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete account")
    return


# -------------------------
# Small helpers for your monthly-expense workflow
# -------------------------
@router.get("/{account_id}/summary")
def account_month_summary(
    account_id: int,
    month: Optional[str] = Query(None, description="Month in YYYY-MM format. Defaults to current month."),
    session: Session = Depends(get_session),
):
    """
    Returns totals for the given account and month:
      { "income": float, "expenses": float, "net": float, "month": "YYYY-MM" }
    Income/expense classification depends on Transaction.type (expected 'income' or 'expense').
    """
    acc = session.get(models.Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    # determine month range
    if month:
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")
    else:
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)
    # compute end as first day of next month
    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)

    # aggregate sums by type
    income_sum = session.exec(
        select(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .where(models.Transaction.account_id == account_id)
        .where(models.Transaction.type == "income")
        .where(models.Transaction.date >= start.date())
        .where(models.Transaction.date < end.date())
    ).one()

    expense_sum = session.exec(
        select(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .where(models.Transaction.account_id == account_id)
        .where(models.Transaction.type == "expense")
        .where(models.Transaction.date >= start.date())
        .where(models.Transaction.date < end.date())
    ).one()

    income = float(income_sum or 0.0)
    expenses = float(expense_sum or 0.0)
    net = income - expenses

    return {"account_id": account_id, "month": start.strftime("%Y-%m"), "income": income, "expenses": expenses, "net": net}
