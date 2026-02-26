from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from datetime import time

app = FastAPI(
    title="Maravi Bus Alert API",
    version="0.1.0",
    description="Bus proximity alert system for Rio de Janeiro"
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class Item(BaseModel):
    id: int
    name: str
    status: str  # FastAPI rejects requests that don't match this shape


class AlertRegistration(BaseModel):
    """Represents a user's request to be notified about a specific bus line."""
    email: str
    bus_line: str          # e.g. "485"
    stop_lat: float        # latitude of the user's boarding stop
    stop_lon: float        # longitude of the user's boarding stop
    window_start: time     # start of the time window, e.g. 07:30
    window_end: time       # end of the time window,   e.g. 08:30

    @field_validator("bus_line")
    @classmethod
    def bus_line_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("bus_line cannot be blank")
        return v.strip()


# ---------------------------------------------------------------------------
# In-memory stores (replaced by a real DB on Day 2)
# ---------------------------------------------------------------------------

items: list[dict] = [
    {"id": 1, "name": "Issue 1", "status": "open"},
    {"id": 2, "name": "Issue 2", "status": "closed"},
    {"id": 3, "name": "Issue 3", "status": "wip"},
]

registrations: list[dict] = []


# ---------------------------------------------------------------------------
# Generic / health endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Hello World!"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Items endpoints (learning exercise)
# ---------------------------------------------------------------------------

@app.get("/items")
def get_items(page: int = 1, limit: int = 10) -> list[dict]:
    start = (page - 1) * limit
    end = start + limit
    return items[start:end]


@app.post("/items", status_code=201)
def create_item(item: Item) -> dict:
    # item is already validated by Pydantic — if id/name/status are missing
    # or wrong type, FastAPI returns 422 before this line runs
    items.append(item.model_dump())
    return item.model_dump()


@app.get("/items/{item_id}")
def read_item(item_id: int) -> dict:
    for item in items:
        if item["id"] == item_id:
            return item
    # HTTPException produces a proper 404 JSON response instead of a 200 with {"error": ...}
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


# ---------------------------------------------------------------------------
# Alert registration endpoints (the real project)
# ---------------------------------------------------------------------------

@app.post("/registrations", status_code=201)
def create_registration(registration: AlertRegistration) -> dict:
    entry = registration.model_dump()
    entry["id"] = len(registrations) + 1
    registrations.append(entry)
    return entry


@app.get("/registrations")
def list_registrations() -> list[dict]:
    return registrations


@app.delete("/registrations/{registration_id}", status_code=204)
def delete_registration(registration_id: int):
    for i, reg in enumerate(registrations):
        if reg["id"] == registration_id:
            registrations.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Registration {registration_id} not found")
