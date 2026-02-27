import math

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta entre dois pontos na Terra; usa Haversine equanto
    travel-time API não está implementada (day4-5)."""

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
    """Estima tempo de viagem em min dadas distância e vel. atual."""
    if speed_kmh < 1:
        return None
    return round((distance_km / speed_kmh) * 60, 1)
