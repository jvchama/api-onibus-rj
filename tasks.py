import json
import redis

from celery_app import celery_app
from bus_service import fetch_all_buses_sync

redis_client = redis.Redis(host="localhost", port=6379, db=0)

CACHE_KEY = "buses:snapshot"
CACHE_TTL = 300  # sec — snapshot expira após 5min se worker parar 


@celery_app.task
def fetch_and_cache_buses():
    """Dá fetch em todas as posições de ônibus da API e armazena-as no cache no Redis.
    
    Chamada a cada 60s pelo beat. Armazena o snapshot completo através do CACHE KEY,
    GET /buses/{line} lê localmente ao invés de buscar a API à todo request. Elimina
    o erro 429 observado no dia 3. 

    Retorna o n de ônibus em cache (bom para observar logs).
    """
    buses = fetch_all_buses_sync()
    redis_client.setex(CACHE_KEY, CACHE_TTL, json.dumps(buses))
    return len(buses)
