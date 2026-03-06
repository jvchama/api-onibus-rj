# Maravi — Alertas de Ônibus Rio de Janeiro

Aplicação web que monitora a posição GPS dos ônibus do Rio de Janeiro em tempo real e envia alertas por e-mail quando um ônibus da linha cadastrada está chegando à parada do usuário.

## Funcionalidades

- **Rastreamento ao vivo** — mapa interativo com posição dos ônibus, distância e ETA calculado via OpenRouteService (rota real de rua)
- **Alertas por e-mail** — notificação automática quando um ônibus está a ≤ 10 min da parada, dentro da janela de horário configurada
- **Geocodificação** — busca de endereço por texto (Nominatim/OpenStreetMap), sem necessidade de inserir coordenadas manualmente
- **Atualização automática** — dados dos ônibus atualizados a cada 60 s via Celery + Redis

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI + Uvicorn |
| Banco de dados | SQLite + SQLAlchemy + Alembic |
| Worker | Celery + Redis |
| Frontend | React 19 + Vite + Leaflet |
| GPS | API pública SPPO Rio (`dados.mobilidade.rio`) |
| ETA | OpenRouteService (rota real) + Haversine (pré-filtro) |
| E-mail | SMTP via Mailtrap (sandbox dev) |

## Rodar com Docker

### Pré-requisitos
- Docker e Docker Compose instalados
- Conta gratuita no [OpenRouteService](https://openrouteservice.org) para a chave de API
- Conta no [Mailtrap](https://mailtrap.io) para o sandbox SMTP (dev)

### Configuração

```bash
cp .env.example .env
# Edite .env e preencha: API_KEY, ADMIN_API_KEY, ORS_API_KEY, SMTP_USER, SMTP_PASS, VITE_API_KEY
# Em Docker, use REDIS_URL=redis://redis:6379/0 (hostname do serviço, não localhost)
```

### Subir

```bash
docker compose up --build
```

Serviços disponíveis após o boot:

| URL | Serviço |
|---|---|
| `http://localhost:8000` | Aplicação web (React SPA) |
| `http://localhost:8000/docs` | Swagger UI da API |
| `http://localhost:8081` | Redis Commander (debug) |

Os dados do banco persistem entre restarts via volume Docker (`db-data`).

## Rodar em modo desenvolvimento (Windows)

### Pré-requisitos

- [Python 3.12+](https://www.python.org/downloads/) (marque "Add to PATH" no instalador)
- [Node.js 18+](https://nodejs.org/)
- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) (necessário para o Redis)
- [uv](https://docs.astral.sh/uv/) — instale via PowerShell:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

### Passo a passo

Abra três terminais (PowerShell ou Windows Terminal):

```powershell
# Terminal 1 — Redis (via Docker Desktop)
docker compose up redis -d
```

```powershell
# Terminal 2 — Celery worker + beat
# --pool=solo é necessário no Windows (Celery não suporta prefork nesse OS)
uv run celery -A celery_app worker --beat --loglevel=info --pool=solo
```

```powershell
# Terminal 3 — FastAPI
uv run uvicorn main:app --reload
```

Frontend (quarto terminal):

```powershell
cd frontend
# Crie frontend/.env.local com: VITE_API_KEY=<mesma chave que API_KEY no .env>
npm install
npm run dev   # http://localhost:5173 (proxy para o backend em :8000)
```

Migrações do banco (primeira vez):

```powershell
mkdir data
uv run alembic upgrade head
```

> **Dica:** se `uv run celery` falhar com erro de permissão, execute o terminal como Administrador ou verifique se o caminho do `uv` está no PATH do sistema.

## Variáveis de ambiente

Veja `.env.example` para a lista completa com descrições. As obrigatórias são:

| Variável | Descrição |
|---|---|
| `API_KEY` | Chave para POST e DELETE /registrations |
| `ADMIN_API_KEY` | Chave para GET /registrations (admin) |
| `VITE_API_KEY` | Mesma chave que `API_KEY`, embutida no frontend |
| `ORS_API_KEY` | Chave do OpenRouteService |
| `REDIS_URL` | URL do Redis (`redis://redis:6379/0` em Docker) |
| `SMTP_USER` / `SMTP_PASS` | Credenciais Mailtrap |

## Endpoints da API

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| `GET` | `/buses/{line}` | — | Ônibus da linha; `?stop_lat=&stop_lon=` adiciona ETA |
| `POST` | `/registrations` | `API_KEY` | Cadastrar alerta |
| `GET` | `/registrations` | `ADMIN_API_KEY` | Listar todos os alertas |
| `DELETE` | `/registrations/{id}?email=` | `API_KEY` | Deletar alerta (requer e-mail do dono) |

Autenticação via header `X-API-Key`.
