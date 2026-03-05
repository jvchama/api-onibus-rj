import asyncio
import httpx
from datetime import datetime, timedelta
from fastapi import HTTPException

from utils import haversine_km, get_ors_eta_sync

# Número de ônibus mais próximos que recebem ETA via ORS.
# Os demais ficam com eta_minutes=None para não gastar cota da API.
ORS_TOP_N = 3

API_BASE = "https://dados.mobilidade.rio/gps/sppo"

# API tem um index lag de 2-min para dados ao vivo
# Realiza o query numa janela terminando sempre 2-min antes. 
LAG_MINUTES = 2
WINDOW_MINUTES = 3  # how far back to look beyond the lag


def _deduplicate_buses(buses: list[dict]) -> list[dict]:
    """Keep only the most recent ping per physical bus (by ordem).

    The API returns one record per GPS ping — within a 3-minute window the
    same bus can appear 5-8 times. We only care about its latest position.
    """
    latest: dict[str, dict] = {}
    for bus in buses:
        ordem = bus["ordem"]
        if ordem not in latest or bus["datahora"] > latest[ordem]["datahora"]:
            latest[ordem] = bus
    return list(latest.values())


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


def fetch_all_buses_sync() -> list[dict]:
    """Fetch síncrono de TODOS os ônibus de TODAS as linhas — (Celery Worker)

    Retorna todos os registros parseados da janela atual, sem filtro por linha.
    O worker armazena esse snapshot completo no Redis; o filtro por linha acontece
    no momento da leitura no endpoint da API.
    """
    now = datetime.now()
    data_final = (now - timedelta(minutes=LAG_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    data_inicial = (now - timedelta(minutes=LAG_MINUTES + WINDOW_MINUTES)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    params = {"dataInicial": data_inicial, "dataFinal": data_final}

    response = httpx.get(API_BASE, params=params, timeout=15.0)
    response.raise_for_status()
    return _deduplicate_buses([_parse_bus(b) for b in response.json()])


async def apply_ors_eta(
    buses: list[dict],
    stop_lat: float,
    stop_lon: float,
) -> None:
    """Aplica ETA via ORS para os ORS_TOP_N ônibus mais próximos.

    Modifica a lista in-place. Pressupõe que bus["distance_km"] (haversine)
    já esteja preenchido — usa esse valor como critério de seleção dos candidatos.

    Para ônibus além do top N, define eta_minutes=None: melhor não mostrar ETA
    do que mostrar um valor enganoso baseado em linha reta.

    get_ors_eta_sync é bloqueante — usamos asyncio.to_thread para não travar
    o event loop do FastAPI.
    """
    buses.sort(key=lambda b: b["distance_km"])

    for bus in buses[:ORS_TOP_N]:
        result = await asyncio.to_thread(
            get_ors_eta_sync,
            bus["latitude"], bus["longitude"],
            stop_lat, stop_lon,
        )
        if result:
            bus["eta_minutes"] = result["eta_minutes"]
            bus["distance_km"] = result["distance_km"]  # distância por rua (mais precisa)
        else:
            bus["eta_minutes"] = None  # ORS falhou → não exibe ETA falso

    for bus in buses[ORS_TOP_N:]:
        bus["eta_minutes"] = None


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

    buses = _deduplicate_buses([_parse_bus(b) for b in raw_buses if b["linha"] == line])

    # Adiciona distância haversine a todos os ônibus; ETA via ORS para os mais próximos
    if stop_lat is not None and stop_lon is not None:
        for bus in buses:
            dist = haversine_km(bus["latitude"], bus["longitude"], stop_lat, stop_lon)
            bus["distance_km"] = round(dist, 3)
        await apply_ors_eta(buses, stop_lat, stop_lon)

    return buses
