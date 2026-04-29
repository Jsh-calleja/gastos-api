# app/routers/accounts.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel import Session

from app.db import get_session
from app import models
from app.schemas import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, session: Session = Depends(get_session)):
    acc = models.Account.from_orm(payload)
    session.add(acc)
    session.commit()
    session.refresh(acc)
    return acc

@router.get("/", response_model=List[AccountRead])
def list_accounts(session: Session = Depends(get_session)):
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
    session.add(db)
    session.commit()
    session.refresh(db)
    return db

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, session: Session = Depends(get_session)):
    acc = session.get(models.Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    session.delete(acc)
    session.commit()
    return
