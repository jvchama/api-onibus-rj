import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./riobus.db")

# connect_args é específico do SQLite: permite reusar a mesma conexão entre
# threads, necessário no FastAPI (thread pool). Ignorado para outros bancos.
connect_args = (
    {"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    else {}
)
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# Each request gets its own session from this factory.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All ORM models inherit from this — it gives Alembic the metadata it
    needs to detect changes and generate migrations."""
    pass
