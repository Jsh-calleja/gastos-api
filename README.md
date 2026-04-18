Gastos API
A small FastAPI service for personal expense tracking built with SQLModel and SQLite. This repository includes the application code, models, routers, and a test suite configured to run against a shared in‑memory SQLite database so tests and the TestClient see the same tables and data.

Key features
REST API for accounts, categories, transactions, and recurring payments

SQLModel models and migrations-free SQLite storage for development

Test suite using pytest with a shared in‑memory database (StaticPool) to avoid per-connection isolation issues

Requirements
Python 3.10+ (virtual environment recommended)

Dependencies listed in pyproject.toml or requirements.txt (typical packages used: fastapi, uvicorn, sqlmodel, sqlalchemy, pytest, httpx)

Quick start
Create and activate a virtual environment

bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
Install dependencies

bash
pip install -r requirements.txt
Run the app locally

bash
uvicorn app.main:app --reload
Open http://127.0.0.1:8000/docs to explore the API with the interactive OpenAPI UI.

Tests
The test suite uses a shared in‑memory SQLite database so the application (TestClient) and pytest fixtures see the same tables and data. This avoids errors such as no such table: transaction that occur when each connection gets its own in‑memory database.

Why StaticPool
By default sqlite:///:memory: creates a separate in‑memory database per connection. Using StaticPool forces all connections to reuse the same connection, so tables created with SQLModel.metadata.create_all(engine) are visible to the sessions opened by TestClient.

How it works
tests/conftest.py creates a test engine with StaticPool.

app.models is imported and SQLModel.metadata.create_all(engine) is executed to create tables on the test engine.

app.db.engine is reassigned (if present) and the app’s get_session dependency is overridden so TestClient uses sessions from the test engine.

Run tests
From the project root:

bash
pytest -q
To run a single test and see debug prints:

bash
pytest -q tests/test_transactions.py::test_avg_salary_per_month_report -s
Example tests fixture
Add the following tests/conftest.py to centralize fixtures and ensure the app and tests share the same in‑memory DB:

python
# tests/conftest.py
from sqlmodel import SQLModel, create_engine
from sqlalchemy.pool import StaticPool
import pytest
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app.models
import app.db as app_db
from app.main import app

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    SQLModel.metadata.create_all(engine)
    try:
        app_db.engine = engine
    except Exception:
        pass
    return engine

@pytest.fixture
def session(engine):
    from sqlmodel import Session
    with Session(engine) as s:
        yield s

@pytest.fixture
def client(engine, session):
    def _get_session_override():
        from sqlmodel import Session
        with Session(engine) as s:
            yield s

    app.dependency_overrides[app_db.get_session] = _get_session_override
    from fastapi.testclient import TestClient as _TC
    with _TC(app) as c:
        yield c
    app.dependency_overrides.clear()
Notes

Remove temporary debug print statements and any sys.path hacks in individual tests once conftest.py is in place.

Add a short comment in conftest.py explaining why StaticPool is used for future contributors.

Project structure
Typical layout

Code
.
├─ app
│  ├─ __init__.py
│  ├─ main.py
│  ├─ db.py
│  ├─ models.py
│  └─ routers
│     └─ transactions.py
├─ tests
│  ├─ conftest.py
│  └─ test_transactions.py
├─ README.md
└─ requirements.txt
Contributing
Create a branch for your feature or fix:

bash
git checkout -b feature/your-feature
Run tests locally:

bash
pytest -q
Commit and push your branch, then open a Pull Request.

CI suggestion
Add a GitHub Actions workflow that runs pytest on push and pull requests. Ensure the workflow installs dependencies and runs tests from the repository root.
