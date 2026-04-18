from datetime import datetime, date as date_cls
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from sqlalchemy import func
from dateutil.relativedelta import relativedelta

from app.db import get_session
from app.models import (
    Transaction as TransactionModel,
    Account,
    TransactionType,
    RecurringPayment,
    Category,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransactionCreate(BaseModel):
    type: TransactionType
    date: Optional[date_cls] = None
    amount: float
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    note: Optional[str] = None
    recurring_id: Optional[int] = None


class TransactionRead(BaseModel):
    id: int
    type: TransactionType
    date: date_cls
    amount: float
    category_id: Optional[int]
    account_id: Optional[int]
    note: Optional[str]
    recurring_id: Optional[int]


@router.post("/", response_model=TransactionRead)
def create_transaction(tx_in: TransactionCreate, session: Session = Depends(get_session)):
    # Normalizar/parsear fecha
    tx_date = tx_in.date
    if isinstance(tx_date, str):
        try:
            tx_date = datetime.strptime(tx_date, "%Y-%m-%d").date()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    if tx_date is None:
        tx_date = datetime.utcnow().date()

    # Construir instancia SQLModel
    tx = TransactionModel(
        type=tx_in.type,
        date=tx_date,
        amount=tx_in.amount,
        category_id=tx_in.category_id,
        account_id=tx_in.account_id,
        note=tx_in.note,
        recurring_id=tx_in.recurring_id,
    )

    try:
        session.add(tx)

        # Ajustar balance de la cuenta (si aplica) antes del commit
        if tx.account_id:
            account = session.get(Account, tx.account_id)
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
            if tx.type == TransactionType.expense:
                account.balance = (account.balance or 0.0) - tx.amount
            else:  # income
                account.balance = (account.balance or 0.0) + tx.amount
            session.add(account)

        session.commit()
        session.refresh(tx)

        return TransactionRead(
            id=tx.id,
            type=tx.type,
            date=tx.date,
            amount=tx.amount,
            category_id=tx.category_id,
            account_id=tx.account_id,
            note=tx.note,
            recurring_id=tx.recurring_id,
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recurring/{rec_id}/pay", response_model=TransactionRead)
def pay_recurring(rec_id: int, session: Session = Depends(get_session)):
    """
    Marca un RecurringPayment como pagado: crea la transacción, actualiza balance y next_due.
    La lógica de frecuencia aquí es un ejemplo simple que avanza 1 mes.
    """
    rec = session.get(RecurringPayment, rec_id)
    if not rec or not getattr(rec, "active", True):
        raise HTTPException(status_code=404, detail="Recurring payment not found or inactive")

    tx_date = rec.next_due or datetime.utcnow().date()

    tx = TransactionModel(
        type=TransactionType.expense if getattr(rec, "type", "expense") == "expense" else TransactionType.income,
        date=tx_date,
        amount=rec.amount,
        category_id=rec.category_id if hasattr(rec, "category_id") else None,
        account_id=rec.account_id,
        note=f"Recurring: {getattr(rec, 'description', '')}",
        recurring_id=rec.id,
    )

    try:
        session.add(tx)

        # Ajustar balance de la cuenta
        if tx.account_id:
            account = session.get(Account, tx.account_id)
            if account:
                if tx.type == TransactionType.expense:
                    account.balance = (account.balance or 0.0) - tx.amount
                else:
                    account.balance = (account.balance or 0.0) + tx.amount
                session.add(account)

        # Actualizar next_due (ejemplo: sumar 1 mes)
        current_next = rec.next_due or datetime.utcnow().date()
        rec.next_due = current_next + relativedelta(months=+1)
        session.add(rec)

        session.commit()
        session.refresh(tx)
        return TransactionRead(
            id=tx.id,
            type=tx.type,
            date=tx.date,
            amount=tx.amount,
            category_id=tx.category_id,
            account_id=tx.account_id,
            note=tx.note,
            recurring_id=tx.recurring_id,
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/avg-salary-per-month")
def avg_salary_per_month(session: Session = Depends(get_session)):
    """
    Calcula el promedio mensual de ingresos para la categoría 'Salario'.
    Devuelve average_per_month y el detalle por mes.
    """
    # Asegurarse de que exista la categoría "Salario"
    cat_stmt = select(Category).where(Category.name == "Salario")
    cat = session.exec(cat_stmt).first()
    if not cat:
        return {"average_per_month": 0.0, "months": []}

    # SQLite: usar strftime para agrupar por año-mes
    stmt = (
        select(
            func.strftime("%Y-%m", TransactionModel.date).label("month"),
            func.sum(TransactionModel.amount).label("total"),
        )
        .where(TransactionModel.type == TransactionType.income, TransactionModel.category_id == cat.id)
        .group_by("month")
        .order_by("month")
    )

    rows = session.exec(stmt).all()
    if not rows:
        return {"average_per_month": 0.0, "months": []}

    totals = [r.total for r in rows]
    avg = sum(totals) / len(totals)
    months = [{"month": r.month, "total": r.total} for r in rows]
    return {"average_per_month": avg, "months": months}
