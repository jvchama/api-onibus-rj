"""
Diagnóstico da resposta ORS quando origem == destino.

Uso:
    docker exec ps_maravi-worker-1 mkdir -p /app/scripts
    docker cp scripts/debug_ors.py ps_maravi-worker-1:/app/scripts/debug_ors.py
    docker exec -it ps_maravi-worker-1 python3 /app/scripts/debug_ors.py
"""
import sys
sys.path.insert(0, "/app")

import os
import json
import openrouteservice

key = os.getenv("ORS_API_KEY", "")
if not key:
    print("ORS_API_KEY não está configurada.")
    sys.exit(1)

client = openrouteservice.Client(key=key)

lat, lon = -22.9068, -43.1729

# Teste 1: mesmas coordenadas (o que test_alert.py faz)
print("=== Teste 1: origem == destino (distância 0) ===")
try:
    result = client.directions(((lon, lat), (lon, lat)), profile="driving-car")
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Erro: {e}")

print()

# Teste 2: coordenadas levemente diferentes (~500m de distância)
print("=== Teste 2: origem a ~500m do destino ===")
try:
    result = client.directions(((lon, lat), (lon + 0.005, lat + 0.003)), profile="driving-car")
    summary = result["routes"][0]["summary"]
    print(f"duration: {summary.get('duration')} s")
    print(f"distance: {summary.get('distance')} m")
except Exception as e:
    print(f"Erro: {e}")
