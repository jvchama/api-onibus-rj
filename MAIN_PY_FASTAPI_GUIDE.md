# How `main.py` Works (FastAPI Fundamentals)

This guide explains the structure of `main.py` and the core FastAPI concepts behind it.

---

## 1) App setup

At the top of the file, the API app is created:

```python
app = FastAPI(
    title="Maravi Bus Alert API",
    version="0.1.0",
    description="Bus proximity alert system for Rio de Janeiro"
)
```

### Why this matters
- `FastAPI(...)` creates your web application object.
- Metadata (`title`, `version`, `description`) appears in the auto-generated docs UI.
- FastAPI automatically exposes docs endpoints:
  - `GET /docs` (Swagger UI)
  - `GET /redoc` (ReDoc)

---

## 2) Data schemas with Pydantic

You define request/response shapes using classes that inherit from `BaseModel`.

### `Item`
```python
class Item(BaseModel):
    id: int
    name: str
    status: str
```

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

### Why this matters
- Pydantic validates incoming JSON automatically.
- If required fields are missing or wrong type, FastAPI returns `422 Unprocessable Entity` before your endpoint logic runs.
- Type hints are not just documentation: they power validation and docs generation.

### Custom validator in this file
`AlertRegistration` includes:

```python
@field_validator("bus_line")
def bus_line_must_not_be_empty(...)
```

This enforces that `bus_line` is not blank and trims whitespace.

> Note: `EmailStr` is imported but not currently used. If you want email validation, change `email: str` to `email: EmailStr`.

---

## 3) In-memory storage (temporary persistence)

```python
items: list[dict] = [...]
registrations: list[dict] = []
```

### Why this matters
- This is simple and great for learning/prototyping.
- Data resets when the server restarts.
- In production, this is typically replaced by a real database (PostgreSQL, MySQL, etc.).

---

## 4) Routes and HTTP methods

FastAPI uses decorators to bind a Python function to an HTTP route.

## Health/basic routes

### `GET /`
Returns a simple hello message.

### `GET /health`
Returns `{"status": "ok"}` and is commonly used for health checks.

---

## 5) Items endpoints (learning CRUD)

### `GET /items`
```python
def get_items(page: int = 1, limit: int = 10)
```
- `page` and `limit` are **query parameters**.
- Pagination is done by list slicing.

Example:
- `GET /items?page=1&limit=2` returns first 2 items.

### `POST /items` (201 Created)
```python
def create_item(item: Item)
```
- `item` is parsed from JSON body and validated against the `Item` model.
- `status_code=201` indicates successful resource creation.
- `model_dump()` converts the Pydantic object to a plain dict.

### `GET /items/{item_id}`
```python
def read_item(item_id: int)
```
- `item_id` is a **path parameter**.
- If not found, the code raises:
```python
raise HTTPException(status_code=404, detail="...")
```

This is the standard FastAPI way to return proper API errors.

---

## 6) Registration endpoints (project core)

### `POST /registrations` (201 Created)
```python
def create_registration(registration: AlertRegistration)
```
- Validates request body with `AlertRegistration`.
- Adds an auto-increment-style `id`.
- Stores the registration in memory.

### `GET /registrations`
Returns all current registrations.

### `DELETE /registrations/{registration_id}` (204 No Content)
- Deletes one registration by ID.
- Returns no response body on success (`204`).
- Returns `404` if the registration does not exist.

---

## 7) Core FastAPI fundamentals demonstrated here

1. **Routing** with `@app.get`, `@app.post`, `@app.delete`
2. **Validation** using Pydantic models
3. **Type-driven API docs** from Python type hints
4. **Path/query/body parameter parsing**
5. **HTTP semantics** via status codes (`201`, `204`, `404`, `422`)
6. **Error handling** using `HTTPException`

---

## 8) How to explore this API quickly

If your server is running with:

```bash
fastapi dev main.py
```

Use these URLs:
- `http://127.0.0.1:8000/docs` for interactive testing
- `http://127.0.0.1:8000/redoc` for alternate docs view
- `http://127.0.0.1:8000/health` for a quick health check

---

## 9) Good next learning steps

1. Replace in-memory lists with a database.
2. Change `email: str` to `email: EmailStr` for strict email validation.
3. Add response models (`response_model=...`) to make outputs explicit.
4. Split routes into modules (`routers/`) as the app grows.
5. Add tests with `pytest` + FastAPI `TestClient`.

---

## Mental model summary

Think of this file as:
- **FastAPI app object** (the web server interface)
- **Pydantic models** (input contracts)
- **Route functions** (business logic handlers)
- **In-memory lists** (temporary data layer)

That layering is the core pattern you’ll keep using as your FastAPI projects become more advanced.
