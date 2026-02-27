from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class AlertRegistration(Base):
    """SQLAlchemy ORM model — represents a row in the alert_registrations table.

    Note: window_start / window_end are stored as plain strings ("HH:MM:SS")
    because SQLite has no native TIME type. They are converted back to
    datetime.time by Pydantic when the API reads them.
    """
    __tablename__ = "alert_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    bus_line: Mapped[str] = mapped_column(String, nullable=False, index=True)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    window_start: Mapped[str] = mapped_column(String, nullable=False)  # "HH:MM:SS"
    window_end: Mapped[str] = mapped_column(String, nullable=False)    # "HH:MM:SS"
