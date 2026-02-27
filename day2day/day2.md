# Day 2 — Database Layer & Project Design Decisions

## What was built

The single `main.py` from Day 1 was split into four focused modules, and a real SQLite database replaced the in-memory lists.

```
ps_maravi/
├── main.py         ← routes only
├── database.py     ← engine, session factory, Base
├── models.py       ← SQLAlchemy ORM (DB table definitions)
├── schemas.py      ← Pydantic schemas (API contract)
├── alembic/        ← migration files
│   └── versions/
│       └── e226d031d9d3_create_alert_registrations_table.py
├── alembic.ini     ← points at sqlite:///./maravi.db
└── maravi.db       ← the actual SQLite database
```

---

## Core concept: models.py vs schemas.py

This is the most important distinction introduced on Day 2.

| | `models.py` (SQLAlchemy) | `schemas.py` (Pydantic) |
|---|---|---|
| Purpose | Maps Python classes to DB tables | Validates HTTP request/response data |
| Lives in | Database layer | API boundary |
| Example | A row in `alert_registrations` | JSON body sent by the client |

They often look similar but serve completely different roles. A Pydantic schema validates what comes *in* over HTTP; a SQLAlchemy model defines what gets *stored* in the database.

---

## 1) `database.py` — connection setup

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite:///./maravi.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific, needed by FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass
```

- `engine` — the actual connection to the database file
- `SessionLocal` — a factory that creates one session per request
- `Base` — all ORM models inherit from this; Alembic reads `Base.metadata` to detect schema changes

---

## 2) `models.py` — ORM table definition

```python
class AlertRegistration(Base):
    __tablename__ = "alert_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    bus_line: Mapped[str] = mapped_column(String, nullable=False, index=True)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    window_start: Mapped[str] = mapped_column(String, nullable=False)
    window_end: Mapped[str] = mapped_column(String, nullable=False)
```

`window_start` and `window_end` are stored as plain strings (`"HH:MM:SS"`) because SQLite has no native TIME type. Pydantic converts them back to `datetime.time` when reading.

---

## 3) `schemas.py` — API data contracts

```python
class AlertRegistrationCreate(BaseModel):
    """What the client sends in the request body."""
    email: str
    bus_line: str
    stop_lat: float
    stop_lon: float
    window_start: time
    window_end: time

class AlertRegistrationRead(AlertRegistrationCreate):
    """What the API returns — same fields plus the DB-assigned id."""
    id: int
    model_config = {"from_attributes": True}
```

`from_attributes=True` tells Pydantic it can read values directly from SQLAlchemy ORM object attributes instead of expecting a dict.

---

## 4) Dependency injection — `get_db`

FastAPI's `Depends()` system injects resources into endpoint functions automatically.

```python
def get_db():
    db = SessionLocal()   # open a session
    try:
        yield db          # hand it to the endpoint
    finally:
        db.close()        # always runs after the request, even on error

@app.post("/registrations")
def create_registration(data: schemas.AlertRegistrationCreate, db: Session = Depends(get_db)):
    ...
```

The `yield` makes `get_db` a generator. FastAPI runs the code after `yield` as cleanup once the response is sent. This guarantees sessions are never leaked.

---

## 5) The DB write cycle

Every write to the database follows three steps:

```python
db_reg = models.AlertRegistration(**data)  # 1. create the ORM object
db.add(db_reg)                             # 2. stage it (not written yet)
db.commit()                                # 3. write to disk
db.refresh(db_reg)                         # 4. reload from DB to get auto-assigned id
return db_reg
```

`db.refresh()` is necessary because SQLite assigns the `id` only after the commit. Without it, `db_reg.id` would still be `None`.

---

## 6) Alembic — migrations

Without Alembic, changing a model would require deleting the `.db` file and losing all data. Alembic tracks schema changes as versioned migration files.

```bash
# Detect changes in models.py and generate a migration file
uv run alembic revision --autogenerate -m "create alert_registrations table"

# Apply all pending migrations to the actual DB
uv run alembic upgrade head
```

For Alembic to detect model changes, `alembic/env.py` must import `Base` and all models:

```python
from database import Base
import models  # registers tables on Base.metadata
target_metadata = Base.metadata
```

---

## Day 2 endpoint behaviour (verified)

| Request | Result |
|---|---|
| `POST /registrations` (valid) | 201, row saved to DB, id returned |
| `POST /registrations` (invalid) | 422, Pydantic error detail |
| `GET /registrations` | 200, all rows from DB |
| `DELETE /registrations/1` | 204, row deleted |
| `DELETE /registrations/99` | 404, not found |

Data now **persists across server restarts** — restarting uvicorn and calling `GET /registrations` still returns previously created rows.

---

## Design conversations

### Does the app need user accounts?

Discussed three options:

1. **Email-only (no accounts)** — anyone submits an alert config, email is just the notification destination
2. **Email-based account** — no password, but a token lets you manage your own alerts
3. **Full user accounts** — register/login with JWT

**Decision: email-only.** The spec doesn't require authentication, and full auth (bcrypt, JWT, middleware) would consume significant time better spent on the core features.

### Can one email have multiple stops?

Yes — already supported by the current model. There is no unique constraint on `email`, so the same address can have multiple `AlertRegistration` rows with different lines, stops, and time windows. A `label` field (e.g. `"Home"`, `"Work"`) was identified as a useful addition to distinguish them, but deferred to avoid unnecessary migrations before the model stabilises.

### How often should alert emails be sent?

Concern: with buses running every 8 minutes and a 1-hour window, a user could receive 7+ emails per session.

Evaluated options:
- **One alert per day per registration** — send once, suppress until tomorrow
- **Cooldown window** — suppress for N minutes after firing
- **On-demand (one-shot)** — user arms the alert manually; fires once then deactivates

The on-demand model was explored in depth: it removes time windows, adds a `status` field (`active` | `sent`), and fits naturally into the tracking screen (a "Notify me" button on the bus table). History retention was also considered — keeping past alerts so the user can re-arm a previous stop quickly.

**Final decision: follow the spec as written** — time-window based scheduled alerts, one alert per registration per day (suppression logic to be implemented in the Celery worker on Day 4). The on-demand feature was evaluated as a valid future extension but out of scope for the MVP, as the project already covers a demanding stack for a 2-week learning pace.
