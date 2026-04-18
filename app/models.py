from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field
from enum import Enum

class TransactionType(str, Enum):
    expense = "expense"
    income = "income"

class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    balance: Optional[float] = 0.0

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: TransactionType

class RecurringPayment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str
    amount: float
    frequency: str
    next_due: Optional[date] = None
    active: bool = True
    account_id: Optional[int] = Field(default=None, foreign_key="account.id")

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: TransactionType
    date: date
    amount: float
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    account_id: Optional[int] = Field(default=None, foreign_key="account.id")
    note: Optional[str] = None
    recurring_id: Optional[int] = Field(default=None, foreign_key="recurringpayment.id")
