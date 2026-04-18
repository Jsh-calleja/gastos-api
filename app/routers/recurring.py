from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from typing import List
from sqlmodel import Session
from datetime import date
from app.db import get_session
from app.models import RecurringPayment

router = APIRouter(prefix="/recurring", tags=["recurring"])

@router.post("/", response_model=RecurringPayment)
def create_recurring(r: RecurringPayment, session: Session = Depends(get_session)):
    session.add(r)
    session.commit()
    session.refresh(r)
    return r

@router.get("/", response_model=List[RecurringPayment])
def list_recurring(session: Session = Depends(get_session)):
    items = session.exec(select(RecurringPayment)).all()
    return items

@router.patch("/{rec_id}", response_model=RecurringPayment)
def update_recurring(rec_id: int, r: RecurringPayment, session: Session = Depends(get_session)):
    existing = session.get(RecurringPayment, rec_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recurring payment not found")
    for key, value in r.dict(exclude_unset=True).items():
        setattr(existing, key, value)
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing
