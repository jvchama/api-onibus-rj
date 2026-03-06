# ── Stage 1: build do frontend ────────────────────────────────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/ ./
# VITE_API_KEY precisa estar disponível em build-time para o Vite embutir no bundle.
# Passada via docker compose build args.
ARG VITE_API_KEY
ENV VITE_API_KEY=$VITE_API_KEY
RUN npm run build

# ── Stage 2: backend Python ───────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copia o bundle do React produzido no stage anterior
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000

# mkdir -p data garante que o diretório do banco existe antes do alembic rodar.
# alembic upgrade head é idempotente — seguro rodar a cada restart.
CMD ["sh", "-c", "mkdir -p data && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
