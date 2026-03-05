import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import redis

from celery_app import celery_app
from bus_service import fetch_all_buses_sync
from database import SessionLocal
from email_service import send_bus_alert
from models import AlertRegistration
from utils import get_ors_eta_sync, haversine_km

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

CACHE_KEY = "buses:snapshot"
CACHE_TTL = 300  # sec — snapshot expira após 5min se worker parar

ETA_THRESHOLD_MINUTES = 10
# Pré-filtro haversine: só chama ORS para ônibus a menos de 8km em linha reta.
# Ônibus mais distantes que isso não podem ter ETA ≤ 10min, então poupa a cota da ORS.
HAVERSINE_PREFILTER_KM = 8.0

SP_TZ = ZoneInfo("America/Sao_Paulo")


@celery_app.task(bind=True, max_retries=3)
def fetch_and_cache_buses(self):
    """Dá fetch em todas as posições de ônibus da API e armazena-as no cache no Redis.

    Chamada a cada 60s pelo beat. Após cachear o snapshot, dispara a verificação
    de alertas para todos os registros ativos.

    bind=True permite chamar self.retry() em caso de 429 sem cache disponível.
    Retorna o n de ônibus em cache (bom para observar logs).
    """
    try:
        buses = fetch_all_buses_sync()
        redis_client.setex(CACHE_KEY, CACHE_TTL, json.dumps(buses))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raw = redis_client.get(CACHE_KEY)
            if raw:
                # Cache disponível — usa snapshot anterior, seguro continuar
                buses = json.loads(raw)
                print(f"[worker] Rio API 429 — usando cache existente ({len(buses)} ônibus)")
            else:
                # Sem cache (primeiro run) — reagenda para daqui a 30s
                print("[worker] Rio API 429 — sem cache, tentando novamente em 30s")
                raise self.retry(countdown=30, exc=e)
        else:
            raise

    check_alerts(buses)
    return len(buses)


def check_alerts(buses: list[dict]) -> None:
    """Verifica todos os AlertRegistrations contra o snapshot atual de ônibus.

    Para cada registro ativo (dentro da janela de horário, não alertado hoje):
      1. Filtra ônibus da linha registrada
      2. Pré-filtra por distância haversine (< 8km) — evita chamadas ORS desnecessárias
      3. Calcula ETA via ORS para candidatos próximos
      4. Se ETA <= 10min → envia e-mail e marca last_alerted_date

    Usa SessionLocal diretamente (contexto síncrono do worker Celery).
    """
    now = datetime.now(SP_TZ)
    current_time_str = now.strftime("%H:%M:%S")
    today_str = now.strftime("%Y-%m-%d")

    db = SessionLocal()
    try:
        registrations = db.query(AlertRegistration).all()

        for reg in registrations:
            # Pula se já alertou hoje
            if reg.last_alerted_date == today_str:
                continue

            # Pula se fora da janela de horário
            if not (reg.window_start <= current_time_str <= reg.window_end):
                continue

            # Filtra ônibus da linha do registro
            line_buses = [b for b in buses if b["linha"] == reg.bus_line]
            if not line_buses:
                continue

            # Pré-filtro haversine: descarta ônibus muito distantes antes de chamar ORS
            candidates = [
                bus for bus in line_buses
                if haversine_km(bus["latitude"], bus["longitude"], reg.stop_lat, reg.stop_lon)
                < HAVERSINE_PREFILTER_KM
            ]

            # Calcula ETA via ORS para cada candidato próximo
            for bus in candidates:
                result = get_ors_eta_sync(
                    bus_lat=bus["latitude"],
                    bus_lon=bus["longitude"],
                    stop_lat=reg.stop_lat,
                    stop_lon=reg.stop_lon,
                )
                if result is None:
                    continue

                if result["eta_minutes"] <= ETA_THRESHOLD_MINUTES:
                    sent = send_bus_alert(
                        to_email=reg.email,
                        bus_line=reg.bus_line,
                        bus_ordem=bus["ordem"],
                        eta_minutes=result["eta_minutes"],
                        stop_lat=reg.stop_lat,
                        stop_lon=reg.stop_lon,
                    )
                    if sent:
                        reg.last_alerted_date = today_str
                        db.commit()
                    break  # Um alerta por registro por ciclo é suficiente
    finally:
        db.close()
