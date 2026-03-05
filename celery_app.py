import os

from dotenv import load_dotenv
load_dotenv()  # carrega o .env antes de inicializar o Celery (worker não passa pelo main.py)

from celery import Celery

#NÃO NOMEIE celery.py

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "maravi",
    broker=_REDIS_URL,
    backend=_REDIS_URL,
    include=["tasks"],
)

# Celery Beat -- define o que roda e quando; configura o schedule de 1min 
celery_app.conf.beat_schedule = {
    "fetch-buses-every-minute": {
        "task": "tasks.fetch_and_cache_buses",
        "schedule": 60.0,  # seconds
    },
}

celery_app.conf.timezone = "America/Sao_Paulo"
