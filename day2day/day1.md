# How `main.py` Works (FastAPI Fundamentals)

This file defines a small FastAPI app with two feature areas:

1. **`/items`**: a learning/demo API.
2. **`/registrations`**: the project’s bus alert registration API.

It also demonstrates the core FastAPI stack:

- **FastAPI** for routing and HTTP behavior.
- **Pydantic** for request validation and data parsing.
- **OpenAPI/Swagger UI** (auto-generated docs).

---

## 1) App setup

```python
app = FastAPI(
    title="Maravi Bus Alert API",
    version="0.1.0",
    description="Bus proximity alert system for Rio de Janeiro"
)
```

### What this does
- Creates the ASGI application object.
- Adds API metadata (`title`, `version`, `description`) that appears in docs.

### Related FastAPI tool
- Start dev server: `fastapi dev main.py`
- Swagger UI docs: `http://127.0.0.1:8000/docs`
- ReDoc docs: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON schema: `http://127.0.0.1:8000/openapi.json`

---

## 2) Pydantic schemas (data contracts)

### `Item`
```python
class Item(BaseModel):
    id: int
    name: str
    status: str
```
This is the expected shape for `POST /items` request bodies.

### `AlertRegistration`
```python
class AlertRegistration(BaseModel):
    email: str
    bus_line: str
    stop_lat: float
    stop_lon: float
    window_start: time
    window_end: time
```
This is the expected shape for `POST /registrations`.

### Validation example
```python
@field_validator("bus_line")
def bus_line_must_not_be_empty(...)
```
- Runs automatically during request parsing.
- Rejects blank bus lines by raising `ValueError`.
- FastAPI converts that into a **422 Unprocessable Entity** response.

> Note: `EmailStr` is imported but not used yet. If you change `email: str` to `email: EmailStr`, Pydantic will validate email format automatically.

---

## 3) In-memory storage

```python
items = [...]
registrations = []
```

- Data is stored in Python lists (RAM only).
- Good for learning and quick prototypes.
- Data is lost when the server restarts.
- In production, this is replaced by a real database.

---

## 4) Endpoints and routing

FastAPI decorators map HTTP methods + paths to Python functions.

## `GET /`
Returns a hello message.

## `GET /health`
Returns a simple health status.

## `GET /items?page=1&limit=10`
- Uses query parameters (`page`, `limit`) with defaults.
- Slices the `items` list for basic pagination.

## `POST /items`
- Accepts JSON body matching `Item`.
- If valid, stores item and returns it.
- Returns HTTP **201 Created** because of `status_code=201`.

## `GET /items/{item_id}`
- Uses a **path parameter** (`item_id: int`).
- Returns matching item or raises:
  ```python
  HTTPException(status_code=404, detail="...")
  ```

## `POST /registrations`
- Accepts JSON body matching `AlertRegistration`.
- Assigns an `id`, stores record, and returns it.
- Returns **201 Created**.

## `GET /registrations`
Returns all saved registrations.

## `DELETE /registrations/{registration_id}`
- Finds and removes a registration.
- Returns **204 No Content** on success.
- Returns **404 Not Found** if not found.

---

## 5) Request lifecycle (important FastAPI concept)

When a request arrives (example: `POST /registrations`):

1. FastAPI matches route and method.
2. It reads and parses JSON body.
3. Pydantic validates/coerces values to the schema types.
4. Field validators run (e.g., `bus_line` check).
5. If validation fails, FastAPI returns **422** automatically.
6. If valid, your endpoint function executes.
7. Return value is serialized to JSON response.

---

## 6) Why this is useful for fundamentals

This single file teaches the core FastAPI ideas you’ll use everywhere:

- Route declaration with decorators.
- Query parameters vs path parameters vs request body.
- Validation with Pydantic models.
- Automatic error responses (`422`) and manual ones (`HTTPException`).
- Correct use of HTTP status codes (`200`, `201`, `204`, `404`).
- Auto-generated API docs via OpenAPI.

---

## 7) Small improvements you can try next

1. Change `email: str` to `email: EmailStr` for real email validation.
2. Add `response_model=...` to endpoints for stricter response schemas.
3. Move storage from lists to a database (SQLite/PostgreSQL).
4. Split routes by feature into multiple files (`routers/items.py`, `routers/registrations.py`).
