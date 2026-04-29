# app/schemas.py
from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field

# -------------------------
# Category schemas
# -------------------------
class CategoryBase(SQLModel):
    name: str
    type: str  # "income" or "expense"

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    type: Optional[str] = None

class CategoryRead(CategoryBase):
    id: int

# -------------------------
# Account schemas
# -------------------------
class AccountBase(SQLModel):
    name: str
    balance: float = 0.0

class AccountCreate(AccountBase):
    pass

class AccountUpdate(SQLModel):
    name: Optional[str] = None
    balance: Optional[float] = None

class AccountRead(AccountBase):
    id: int

# -------------------------
# Transaction schemas
# -------------------------
class TransactionBase(SQLModel):
    type: str  # "income" or "expense"
    date: date
    amount: float
    category_id: int
    account_id: int
    note: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(SQLModel):
    type: Optional[str] = None
    date: Optional[date] = None
    amount: Optional[float] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    note: Optional[str] = None

class TransactionRead(TransactionBase):
    id: int
