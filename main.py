from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, SessionLocal, Base

# Create tables that don't exist yet. In production you'd use Alembic
# migrations instead, but this is a safe fallback for development.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Maravi Bus Alert API",
    version="0.1.0",
    description="Bus proximity alert system for Rio de Janeiro",
)

# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_db():
    """Yields a database session and guarantees it's closed after the request,
    even if an unhandled exception occurs."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Alert registration endpoints
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
    db.refresh(db_reg)  # reload from DB to get the auto-assigned id
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