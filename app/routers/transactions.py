# app/routers/transactions.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel import Session

from app.db import get_session
from app import models
from app.schemas import TransactionCreate, TransactionRead, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("/", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, session: Session = Depends(get_session)):
    tx = models.Transaction.from_orm(payload)
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx

@router.get("/", response_model=List[TransactionRead])
def list_transactions(session: Session = Depends(get_session)):
    return session.exec(select(models.Transaction).order_by(models.Transaction.date.desc())).all()

@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: int, session: Session = Depends(get_session)):
    tx = session.get(models.Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx

@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(transaction_id: int, payload: TransactionUpdate, session: Session = Depends(get_session)):
    db = session.get(models.Transaction, transaction_id)
    if not db:
        raise HTTPException(status_code=404, detail="Transaction not found")
    update_data = payload.dict(exclude_unset=True)
    for key, val in update_data.items():
        setattr(db, key, val)
    session.add(db)
    session.commit()
    session.refresh(db)
    return db

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, session: Session = Depends(get_session)):
    tx = session.get(models.Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    session.delete(tx)
    session.commit()
    return
