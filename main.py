import json

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import redis

import models
import schemas
from database import SessionLocal, Base
from bus_service import fetch_buses_by_line, apply_ors_eta
from utils import haversine_km

redis_client = redis.Redis(host="localhost", port=6379, db=0)
CACHE_KEY = "buses:snapshot"

# Reminder to self: full dev setup requires three terminals:
#   Terminal 1 (Redis):  docker compose up -d
#   Terminal 2 (Worker): uv run celery -A celery_app worker --beat --loglevel=info
#   Terminal 3 (API):    uv run uvicorn main:app --reload
# On Day 10 this becomes a Docker Compose service and starts automatically.

app = FastAPI(
    title="Maravi Bus Alert API",
    version="0.1.0",
    description="Bus proximity alert system for Rio de Janeiro",
)

# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_db():
    """Gera uma database session e garante seu fechamento após o request, mesmo
    se uma exceção não-tratada ocorra."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Bus tracking endpoints
# ---------------------------------------------------------------------------

@app.get("/buses/{line}")
async def get_buses(
    line: str,
    stop_lat: float | None = None,
    stop_lon: float | None = None,
):
    """Retorna todos os ônibus de dada linha. 

    Se stop_lat e stop_lon (coordenadas de um ponto) são providenciadas, 
    retorna junto de cada ônibus o ETA em minutos e a distância até dado ponto 
    (eta_minutes & eta_distance_km)

    Ex:
      GET /buses/485
      GET /buses/485?stop_lat=-22.9068&stop_lon=-43.1729
    """
    raw = redis_client.get(CACHE_KEY)

    if raw is None:
        # Cache miss: worker não está rodando ou Redis está down.
        # Cai para uma chamada direta da API para manter a aplicação no ar.
        buses = await fetch_buses_by_line(line, stop_lat, stop_lon)
    else:
        all_buses = json.loads(raw)
        buses = [b for b in all_buses if b["linha"] == line]
        if stop_lat is not None and stop_lon is not None:
            for bus in buses:
                dist = haversine_km(bus["latitude"], bus["longitude"], stop_lat, stop_lon)
                bus["distance_km"] = round(dist, 3)
            await apply_ors_eta(buses, stop_lat, stop_lon)

    return {"line": line, "count": len(buses), "buses": buses}

# ---------------------------------------------------------------------------
# Registration endpoints
# ---------------------------------------------------------------------------

@app.post("/registrations", response_model=schemas.AlertRegistrationRead, status_code=201)
def create_registration(
    registration: schemas.AlertRegistrationCreate,
    db: Session = Depends(get_db),
):
    data = registration.model_dump()
    data["window_start"] = str(data["window_start"])
    data["window_end"] = str(data["window_end"])

    db_reg = models.AlertRegistration(**data)
    db.add(db_reg)
    db.commit()
    db.refresh(db_reg) 
    return db_reg


@app.get("/registrations", response_model=list[schemas.AlertRegistrationRead])
def list_registrations(db: Session = Depends(get_db)):
    return db.query(models.AlertRegistration).all()

@app.delete("/registrations/{registration_id}", status_code=204)
def delete_registration(registration_id: int, db: Session = Depends(get_db)):
    reg = db.get(models.AlertRegistration, registration_id)
    if reg is None:
        raise HTTPException(status_code=404, detail=f"Registration {registration_id} not found")
    db.delete(reg)
    db.commit()