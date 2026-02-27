from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite:///./riobus.db"

# connect_args is SQLite-specific: it allows the same connection to be used
# across threads, which FastAPI needs (it runs handlers in a thread pool).
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Each request gets its own session from this factory.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All ORM models inherit from this — it gives Alembic the metadata it
    needs to detect changes and generate migrations."""
    pass
