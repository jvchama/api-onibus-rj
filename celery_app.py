from dotenv import load_dotenv
load_dotenv()  # carrega o .env antes de inicializar o Celery (worker não passa pelo main.py)

from celery import Celery

#NÃO NOMEIE celery.py

celery_app = Celery(
    "maravi",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
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
