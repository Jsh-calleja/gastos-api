# tests/test_transactions.py
from datetime import date, datetime
import pytest
import sys, os

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app.main import app
import app.db as app_db
from app.db import get_session
from app.models import Account, Category, RecurringPayment, TransactionType, Transaction as TransactionModel

# --- Fixtures: engine, session, client (in-memory SQLite) ---

@pytest.fixture(scope="session")
def engine():
    # Engine en memoria compartida entre conexiones (StaticPool)
    #Keep the StaticPool approach for in-memory tests to avoid SQLite per-connection isolation issues. 
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Asegúrate de que app.models esté importado antes de crear tablas
    # (import app.models al inicio del archivo tests ya lo hace)
    SQLModel.metadata.create_all(engine)

    # Reasignar el engine global de la app para que use el mismo engine de pruebas
    # Esto hace que get_session (si usa app_db.engine) y cualquier código que
    # dependa de app_db.engine trabajen con el engine de pruebas.
    try:
        app_db.engine = engine
    except Exception:
        pass

    # Debug opcional (temporal): confirma que las tablas existen
    # print("Tables in metadata:", list(SQLModel.metadata.tables.keys()))

    return engine

@pytest.fixture
def client(engine, session):
    # override de get_session para que use el engine de pruebas
    def _get_session_override():
        from sqlmodel import Session
        with Session(engine) as s:
            yield s

    app.dependency_overrides[app_db.get_session] = _get_session_override
    from fastapi.testclient import TestClient as _TC
    with _TC(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s

@pytest.fixture
def client(session):
    # override dependency to use the test session
    def _get_session_override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_session] = _get_session_override
    from fastapi.testclient import TestClient as _TC
    with _TC(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- Helpers ---

def create_account(session, name="Test Account", balance=0.0):
    acc = Account(name=name, balance=balance)
    session.add(acc)
    session.commit()
    session.refresh(acc)
    return acc

def create_category(session, name="Comida", type_="expense"):
    cat = Category(name=name, type=type_)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat

def create_recurring(session, account_id, amount=10.0, next_due=None, active=True, description="Rec", frequency="monthly"):
    # Asegúrate de pasar 'frequency' si el modelo lo requiere NOT NULL
    rec = RecurringPayment(
        account_id=account_id,
        amount=amount,
        next_due=next_due or datetime.utcnow().date(),
        active=active,
        description=description,
        frequency=frequency,
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec

# --- Tests ---

def test_create_transaction_updates_account_balance(client, session):
    acc = create_account(session, balance=100.0)
    cat = create_category(session, name="Comida", type_="expense")

    payload = {
        "type": "expense",
        "date": "2026-04-17",
        "amount": 12.5,
        "category_id": cat.id,
        "account_id": acc.id,
        "note": "Café"
    }

    resp = client.post("/transactions/", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["amount"] == 12.5
    assert data["type"] == "expense"
    assert data["account_id"] == acc.id

    # refresh account from DB and check balance updated
    session.refresh(acc)
    assert acc.balance == pytest.approx(100.0 - 12.5)

def test_pay_recurring_creates_transaction_and_advances_next_due(client, session):
    acc = create_account(session, balance=200.0)
    # create a recurring payment with a known next_due and frequency
    start_due = date(2026, 4, 1)
    rec = create_recurring(session, account_id=acc.id, amount=50.0, next_due=start_due, active=True, description="Subscripción", frequency="monthly")

    resp = client.post(f"/transactions/recurring/{rec.id}/pay")
    assert resp.status_code == 200, resp.text
    tx = resp.json()
    assert tx["amount"] == 50.0
    assert tx["account_id"] == acc.id
    assert tx["recurring_id"] == rec.id

    # reload recurring and account
    session.refresh(rec)
    session.refresh(acc)

    # next_due should have advanced by roughly one month (app uses relativedelta months=+1)
    assert rec.next_due > start_due

    # account balance should be decreased by the recurring amount
    assert acc.balance == pytest.approx(200.0 - 50.0)

def test_avg_salary_per_month_report(client, session):
    # create category "Salario"
    salary_cat = create_category(session, name="Salario", type_="income")
    acc = create_account(session, balance=0.0)

    # create three income transactions across two months
    txs = [
        {"type": "income", "date": "2026-01-05", "amount": 1000.0, "category_id": salary_cat.id, "account_id": acc.id},
        {"type": "income", "date": "2026-01-20", "amount": 500.0, "category_id": salary_cat.id, "account_id": acc.id},
        {"type": "income", "date": "2026-02-10", "amount": 1500.0, "category_id": salary_cat.id, "account_id": acc.id},
    ]

    for p in txs:
        r = client.post("/transactions/", json=p)
        assert r.status_code == 200, r.text

    resp = client.get("/transactions/reports/avg-salary-per-month")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # January total = 1500, February total = 1500 => average = (1500 + 1500) / 2 = 1500
    assert "average_per_month" in body
    assert body["average_per_month"] == pytest.approx(1500.0)
    assert isinstance(body["months"], list)
    totals = [m["total"] for m in body["months"]]
    assert all(isinstance(t, (int, float)) for t in totals)
