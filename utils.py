import math
import os

import openrouteservice

# ---------------------------------------------------------------------------
# Haversine — distância em linha reta (usado no GET /buses/{line} para display
# rápido e como pré-filtro antes de chamar a ORS no alert checker)
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta entre dois pontos na Terra."""
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


def estimate_eta_minutes(distance_km: float, speed_kmh: float) -> float | None:
    """Estima tempo de viagem em min dadas distância e vel. atual.
    Usado no GET /buses/{line} — cálculo rápido sem chamada de API externa."""
    if speed_kmh < 1:
        return None
    return round((distance_km / speed_kmh) * 60, 1)


# ---------------------------------------------------------------------------
# OpenRouteService — ETA por rota real de rua (usado no alert checker)
# ---------------------------------------------------------------------------

ORS_API_KEY = os.getenv("ORS_API_KEY", "")

def get_ors_eta_sync(
    bus_lat: float,
    bus_lon: float,
    stop_lat: float,
    stop_lon: float,
) -> dict | None:
    """Calcula ETA e distância via OpenRouteService (rota real de rua).

    Usado apenas no alert checker (tasks.py) — onde a precisão importa para
    o limiar de 10 minutos. O GET /buses/{line} continua usando haversine
    para evitar gastar a cota diária da ORS (2.000 req/dia).

    Retorna {"eta_minutes": float, "distance_km": float} ou None se falhar.
    Coordenadas são passadas como (lon, lat) — convenção ORS.
    """
    if not ORS_API_KEY:
        return None

    try:
        client = openrouteservice.Client(key=ORS_API_KEY)
        coords = ((bus_lon, bus_lat), (stop_lon, stop_lat))
        routes = client.directions(coords, profile="driving-car")
        summary = routes["routes"][0]["summary"]
        # ORS retorna summary vazio ({}) quando origem == destino (ônibus no ponto)
        duration = summary.get("duration", 0)
        distance = summary.get("distance", 0)
        return {
            "eta_minutes": round(duration / 60, 1),
            "distance_km": round(distance / 1000, 3),
        }
    except Exception as e:
        print(f"[ORS] Falha na chamada: {e}")
        return None
