from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from typing import List
from sqlmodel import Session
from app.db import get_session
from app.models import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.post("/", response_model=Account)
def create_account(account: Account, session: Session = Depends(get_session)):
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

@router.get("/", response_model=List[Account])
def list_accounts(session: Session = Depends(get_session)):
    accounts = session.exec(select(Account)).all()
    return accounts

@router.get("/{account_id}", response_model=Account)
def get_account(account_id: int, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account
