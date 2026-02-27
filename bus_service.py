import httpx
from datetime import datetime, timedelta
from fastapi import HTTPException

from utils import haversine_km, estimate_eta_minutes

API_BASE = "https://dados.mobilidade.rio/gps/sppo"

# API tem um index lag de 2-min para dados ao vivo
# Realiza o query numa janela terminando sempre 2-min antes. 
LAG_MINUTES = 2
WINDOW_MINUTES = 3  # how far back to look beyond the lag


def _parse_bus(raw: dict) -> dict:
    """Limpa a API, convertando os dados brutos em tipos limpos"""
    return {
        "ordem": raw["ordem"],
        "linha": raw["linha"],
        "latitude": float(raw["latitude"].replace(",", ".")),
        "longitude": float(raw["longitude"].replace(",", ".")),
        "velocidade": int(raw["velocidade"]),
        "datahora": datetime.fromtimestamp(int(raw["datahora"]) / 1000).isoformat(),
    }


async def fetch_buses_by_line(
    line: str,
    stop_lat: float | None = None,
    stop_lon: float | None = None,
) -> list[dict]:
    """Realiza o fetch de todos os ônibus de dada linha. 

    Se stop_lat e stop_lon (coordenadas de um ponto) são providenciadas, 
    retorna junto de cada ônibus o ETA em minutos e a distância até dado ponto 
    (eta_minutes & eta_distance_km)

    API retorna todos os ônibus de todas as linhas para uma janela - filtro por 
    linha após o fetch. 
    """
    now = datetime.now()
    data_final = (now - timedelta(minutes=LAG_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    data_inicial = (now - timedelta(minutes=LAG_MINUTES + WINDOW_MINUTES)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    params = {"dataInicial": data_inicial, "dataFinal": data_final}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(API_BASE, params=params)
        response.raise_for_status()
        raw_buses = response.json()

    buses = [_parse_bus(b) for b in raw_buses if b["linha"] == line]

    # adiciona distância e ETA dadas lat/lon
    if stop_lat is not None and stop_lon is not None:
        for bus in buses:
            dist = haversine_km(bus["latitude"], bus["longitude"], stop_lat, stop_lon)
            bus["distance_km"] = round(dist, 3)
            bus["eta_minutes"] = estimate_eta_minutes(dist, bus["velocidade"])

    return buses
