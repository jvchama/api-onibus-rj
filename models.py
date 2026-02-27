from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class AlertRegistration(Base):
    """SQLAlchemy ORM model — representa uma linha na tabela "alert_registration".

    NTS: window_start / window_end são armazenadas como strings; SQLite não tem
    datetime type. Sào convertidas quando Pydantic lê a API.

    """
    __tablename__ = "alert_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    bus_line: Mapped[str] = mapped_column(String, nullable=False, index=True)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    window_start: Mapped[str] = mapped_column(String, nullable=False)  # "HH:MM:SS"
    window_end: Mapped[str] = mapped_column(String, nullable=False)    # "HH:MM:SS"
