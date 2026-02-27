# Day 3 — External API Integration & Async HTTP

## What was built

Two new modules were added to handle all bus-related logic, and a new endpoint exposes live bus data filtered by line.

```
ps_maravi/
├── bus_service.py  ← fetches and parses data from the Rio GPS API
├── utils.py        ← haversine distance + ETA math
└── main.py         ← new GET /buses/{line} endpoint added
```

---

## The Rio de Janeiro Bus GPS API

**Base URL:** `https://dados.mobilidade.rio/gps/sppo`

**Parameters:**

| Parameter | Format | Example |
|---|---|---|
| `dataInicial` | `YYYY-MM-DD HH:MM:SS` | `2026-02-27 08:00:00` |
| `dataFinal` | `YYYY-MM-DD HH:MM:SS` | `2026-02-27 08:03:00` |

**Response:** JSON array — one object per bus record in the time window.

```json
{
  "ordem": "B31047",
  "latitude": "-22,91227",
  "longitude": "-43,19525",
  "datahora": "1706553591000",
  "velocidade": "37",
  "linha": "485",
  "datahoraenvio": "1706553600000",
  "datahoraservidor": "1706553604000"
}
```

**Field reference:**

| Field | Type (raw) | Description |
|---|---|---|
| `ordem` | string | Unique bus vehicle identifier |
| `latitude` | string | Latitude — comma as decimal separator |
| `longitude` | string | Longitude — comma as decimal separator |
| `datahora` | string | GPS timestamp in Unix milliseconds |
| `velocidade` | string | Speed in km/h |
| `linha` | string | Bus line identifier (e.g. `"485"`) |
| `datahoraenvio` | string | Timestamp when data was sent by the vehicle |
| `datahoraservidor` | string | Timestamp when data was received by the server |

---

## Three parsing quirks

These are the key issues to handle when consuming the API:

### 1. All values are strings
The API returns numbers and timestamps as JSON strings, not native types.
```python
# Raw
{"velocidade": "37", "linha": "485"}

# Parsed
{"velocidade": 37, "linha": "485"}  # int cast needed
```

### 2. Latitude and longitude use commas as decimal separators
Brazilian locale uses `,` instead of `.` — `float("-22,91227")` raises a `ValueError`.
```python
latitude = float(raw["latitude"].replace(",", "."))
```

### 3. Timestamps are Unix milliseconds as strings
```python
datahora = datetime.fromtimestamp(int(raw["datahora"]) / 1000).isoformat()
```

---

## Two operational quirks

### Live data lag
Querying the current timestamp returns 0 results. The API has approximately 2 minutes of indexing lag on live data. The fix is to always query a window ending 2 minutes ago:

```python
LAG_MINUTES = 2
WINDOW_MINUTES = 3

now = datetime.now()
data_final   = (now - timedelta(minutes=LAG_MINUTES)).strftime(...)
data_inicial = (now - timedelta(minutes=LAG_MINUTES + WINDOW_MINUTES)).strftime(...)
```

### No line filtering on the API side
A 3-minute window returns ~25,000 records covering **all lines in Rio**. There is no `linha` query parameter — filtering by line is done in Python after fetching:

```python
buses = [_parse_bus(b) for b in raw_buses if b["linha"] == line]
```

This is fast enough in memory for a 25k list but worth knowing for future optimisation.

---

## 1) `utils.py` — distance and ETA math

### Haversine formula
Calculates straight-line distance between two coordinates accounting for Earth's curvature.

```python
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))
```

### ETA estimate
```python
def estimate_eta_minutes(distance_km, speed_kmh) -> float | None:
    if speed_kmh < 1:
        return None  # bus is stopped — result would be meaningless
    return round((distance_km / speed_kmh) * 60, 1)
```

**Known limitation:** both functions assume the bus travels in a straight line at constant speed. This is a rough estimate — road curves, traffic, and stops are ignored. A routing API (TravelTime or OSRM) would give better results and may be integrated on Day 5.

---

## 2) `bus_service.py` — service layer

Keeps all external API logic isolated from `main.py`. The main function:

```python
async def fetch_buses_by_line(
    line: str,
    stop_lat: float | None = None,
    stop_lon: float | None = None,
) -> list[dict]:
```

- Builds the time window (with lag offset)
- Calls the API with `httpx.AsyncClient`
- Filters by line
- If `stop_lat` / `stop_lon` are provided, attaches `distance_km` and `eta_minutes` to each bus

### Why `httpx` instead of `requests`?
`requests` is synchronous — it blocks the entire server while waiting for the HTTP response. `httpx` supports `async/await`, so FastAPI can handle other requests while waiting for the Rio API to respond.

```python
async with httpx.AsyncClient(timeout=15.0) as client:
    response = await client.get(API_BASE, params=params)
    response.raise_for_status()  # raises an exception on 4xx/5xx status codes
```

---

## 3) `GET /buses/{line}` endpoint

```python
@app.get("/buses/{line}")
async def get_buses(
    line: str,
    stop_lat: float | None = None,
    stop_lon: float | None = None,
):
```

Note the `async def` — required because the function calls `await fetch_buses_by_line(...)`. Forgetting `async` on an endpoint that uses `await` is a common mistake that causes a runtime error.

**Usage:**
```
GET /buses/485
→ returns all active buses on line 485, no distance info

GET /buses/485?stop_lat=-22.9068&stop_lon=-43.1729
→ same, plus distance_km and eta_minutes per bus
```

**Response shape:**
```json
{
  "line": "485",
  "count": 12,
  "buses": [
    {
      "ordem": "B31047",
      "linha": "485",
      "latitude": -22.91227,
      "longitude": -43.19525,
      "velocidade": 18,
      "datahora": "2026-02-27T09:58:50",
      "distance_km": 2.369,
      "eta_minutes": 7.9
    }
  ]
}
```

---

## Day 3 results (verified against live API)

| Request | Result |
|---|---|
| `GET /buses/485` | 12 active buses, correct coordinates and speeds |
| `GET /buses/485?stop_lat=...&stop_lon=...` | 12 buses with `distance_km` and `eta_minutes` |
| `GET /buses/NONEXISTENT` | `count: 0`, empty `buses` array — no error |

---

## Tomorrow (Day 4 preview)

Set up Redis with Docker and wire Celery to run `fetch_buses_by_line` every 60 seconds automatically. This creates the background heartbeat that will later power the alert notifications — instead of waiting for an HTTP request to fetch bus data, the system will always have fresh data ready.
