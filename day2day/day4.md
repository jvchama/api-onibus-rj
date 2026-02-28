# Dia 4 — Celery + Redis (Workers em Background)

## O que foi construído

Três novos módulos foram adicionados para gerenciar o cache de ônibus e o agendamento de tarefas em background.

```
ps_maravi/
├── celery_app.py   ← instância Celery + configuração do beat schedule
├── tasks.py        ← tarefa periódica fetch_and_cache_buses()
├── bus_service.py  ← nova função fetch_all_buses_sync() + deduplicação
└── main.py         ← GET /buses/{line} agora lê do cache Redis
```

---

## Os quatro componentes

```
┌─────────────────────────────────────────────────────┐
│                    Aplicação                         │
│                                                      │
│  Celery Beat ──► Redis (broker) ──► Celery Worker   │
│  (agendador)      (fila de msgs)   (executa tarefas)│
└─────────────────────────────────────────────────────┘
```

- **Celery Beat** — o relógio. Dispara uma mensagem de tarefa a cada 60 segundos
- **Redis (papel de broker)** — fila de mensagens entre Beat e Worker
- **Celery Worker** — consome mensagens do Redis e executa a função Python da tarefa
- **Redis (papel de cache)** — o worker também escreve os dados de ônibus aqui para que a API leia localmente

O Redis faz dois trabalhos ao mesmo tempo — broker e cache — dispensando o uso de RabbitMQ.

---

## Setup de desenvolvimento (3 terminais)

```bash
# Terminal 1 — Redis (via Docker)
docker compose up -d

# Terminal 2 — Celery worker + beat juntos (válido para dev)
uv run celery -A celery_app worker --beat --loglevel=info

# Terminal 3 — FastAPI
uv run uvicorn main:app --reload
```

No Dia 10, o worker vira um serviço do Docker Compose e sobe automaticamente.

O Redis Commander (UI visual do Redis) fica disponível em `http://localhost:8081`.

---

## 1) `celery_app.py` — configuração do Celery

```python
celery_app = Celery(
    "maravi",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["tasks"],  # onde estão as funções de tarefa
)

celery_app.conf.beat_schedule = {
    "fetch-buses-every-minute": {
        "task": "tasks.fetch_and_cache_buses",
        "schedule": 60.0,  # segundos
    },
}
```

**Atenção:** nunca nomear o arquivo `celery.py` — conflita com o pacote `celery` instalado.

---

## 2) `tasks.py` — tarefa periódica

```python
@celery_app.task
def fetch_and_cache_buses():
    buses = fetch_all_buses_sync()
    redis_client.setex(CACHE_KEY, CACHE_TTL, json.dumps(buses))
    return len(buses)
```

- `setex` — escreve a chave com TTL de 300 segundos. Se o worker parar, o cache expira sozinho em 5 minutos
- O valor retornado (`len(buses)`) aparece nos logs do worker — útil para monitorar se o fetch está funcionando

---

## 3) `bus_service.py` — função síncrona + deduplicação

### Por que uma função síncrona separada?

Workers Celery rodam em contexto síncrono — não suportam `async/await`. O `fetch_buses_by_line` existente usa `httpx.AsyncClient`, que não funciona no worker. A solução é usar `httpx.get` (modo síncrono):

```python
# Async — para endpoints FastAPI
async def fetch_buses_by_line(...):
    async with httpx.AsyncClient() as client:
        response = await client.get(...)

# Síncrono — para o worker Celery
def fetch_all_buses_sync():
    response = httpx.get(API_BASE, params=params, timeout=15.0)
```

### Deduplicação por `ordem`

A API do Rio retorna um registro por ping de GPS. Em uma janela de 3 minutos, o mesmo ônibus físico pode aparecer 5–8 vezes com coordenadas ligeiramente diferentes. Sem deduplicação, `GET /buses/606` retornava 135 registros para apenas 31 ônibus únicos.

```python
def _deduplicate_buses(buses: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for bus in buses:
        ordem = bus["ordem"]
        if ordem not in latest or bus["datahora"] > latest[ordem]["datahora"]:
            latest[ordem] = bus
    return list(latest.values())
```

Mantém apenas o ping mais recente por `ordem`. Aplicado em ambos os caminhos de fetch — síncrono (worker) e assíncrono (fallback da API).

**Impacto:** cache reduziu de ~17.000 para ~2.500 registros. Linha 606: 135 → 23 ônibus.

---

## 4) `main.py` — endpoint lê do cache

```python
raw = redis_client.get(CACHE_KEY)

if raw is None:
    # Cache vazio: worker não está rodando ou Redis caiu.
    # Fallback para chamada direta da API.
    buses = await fetch_buses_by_line(line, stop_lat, stop_lon)
else:
    all_buses = json.loads(raw)
    buses = [b for b in all_buses if b["linha"] == line]
    # aplica distância e ETA se coordenadas foram fornecidas
```

O fallback garante que o endpoint funcione mesmo sem o worker — mas fica sujeito ao erro 429 da API externa novamente.

---

## Problema resolvido: erro 429

No Dia 3, cada chamada a `GET /buses/{line}` batia diretamente na API do Rio, causando erro 429 (rate limit) rapidamente em testes.

Com o Celery:
- A API externa é chamada **uma vez por minuto** pelo worker
- O endpoint lê do Redis — rápido, sem rate limit, sem dependência externa por request

---

## Resultado verificado

| Métrica | Antes (Dia 3) | Depois (Dia 4) |
|---|---|---|
| Chamadas à API externa | 1 por request | 1 por minuto (worker) |
| Erro 429 em testes | Frequente | Eliminado |
| Registros linha 606 | 135 (com duplicatas) | 23 (ônibus únicos) |
| Cache total | ~17.000 registros | ~2.500 registros |

---

## Amanhã (Dia 5)

Dia 5 tem duas partes principais:

**1. TravelTime API — substituir o Haversine**
O cálculo de ETA atual (`distância / velocidade`) ignora curvas de rua, trânsito e paradas. A API TravelTime (ou similar) retorna o tempo de viagem real por rota. Isso é crítico para o alerta de 10 minutos — uma estimativa imprecisa pode disparar o e-mail cedo ou tarde demais.

- Criar conta e obter chave de API em `traveltime.com`
- Escrever cliente para o endpoint *Time Filter* (origem = ponto do usuário, destinos = posições dos ônibus)
- Substituir `haversine_km` + `estimate_eta_minutes` em `utils.py` pelo resultado real da API

**2. Lógica de alertas + e-mail**
Após cachear o snapshot no Redis, a tarefa Celery vai:
- Ler todos os `AlertRegistration` ativos do banco
- Verificar se o horário atual está dentro da janela (`window_start` / `window_end`)
- Usar o TravelTime para calcular o ETA de cada ônibus da linha até o ponto do usuário
- Se algum ônibus estiver ≤ 10 minutos → disparar e-mail
- Registrar `last_alerted_date` para evitar múltiplos alertas no mesmo dia (migração Alembic necessária)
