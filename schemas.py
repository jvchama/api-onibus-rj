from pydantic import BaseModel, field_validator
from datetime import time

class AlertRegistrationCreate(BaseModel):
    """Schema para POST /registrations — o que o cliente recebe."""
    email: str
    bus_line: str
    stop_lat: float
    stop_lon: float
    window_start: time
    window_end: time

    @field_validator("bus_line")
    @classmethod
    def bus_line_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("bus_line cannot be blank")
        return v.strip()


class AlertRegistrationRead(AlertRegistrationCreate):
    """Schema para respostas - mesmos campos que Create + o id atibuído pela DB.

    model_config from_attributes=True comunica ao Pydantic  que consegue ler valores
    de atributos de objetos ORM ao invés de dict keys. 
    """
    id: int
    last_alerted_date: str | None = None

    model_config = {"from_attributes": True}
