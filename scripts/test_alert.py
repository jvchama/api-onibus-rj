"""
Teste manual do fluxo de alerta de e-mail.

Uso dentro do container worker:
    docker cp scripts/test_alert.py ps_maravi-worker-1:/app/scripts/test_alert.py
    docker exec -it ps_maravi-worker-1 python3 /app/scripts/test_alert.py

Uso dentro do container worker:
    docker exec -it ps_maravi-worker-1 python3 scripts/test_alert.py

O script:
  1. Lista os registros ativos no banco
  2. Reseta last_alerted_date para permitir o envio
  3. Chama check_alerts com um ônibus fictício posicionado em cima de cada parada
  4. O ETA resultante é 0 min → abaixo do threshold de 10 min → e-mail disparado

Verifique o recebimento na inbox do Mailtrap após a execução.
"""

import sys
sys.path.insert(0, "/app")

from database import SessionLocal
from models import AlertRegistration
from tasks import check_alerts


def main():
    db = SessionLocal()
    try:
        registros = db.query(AlertRegistration).all()

        if not registros:
            print("Nenhum registro encontrado no banco. Cadastre um alerta primeiro.")
            return

        print(f"Registros encontrados: {len(registros)}\n")
        for r in registros:
            print(f"  ID {r.id} | linha {r.bus_line} | {r.email} | janela {r.window_start}–{r.window_end}")

        # Reseta last_alerted_date para que check_alerts não pule nenhum registro
        for r in registros:
            r.last_alerted_date = None
        db.commit()
        print("\nlast_alerted_date resetado para todos os registros.")

        # Monta um ônibus fictício por registro, deslocado ~500m da parada
        # (evita edge case origem==destino que causa summary vazio na ORS)
        onibus_falsos = [
            {
                "ordem":      f"TESTE{r.id:02d}",
                "linha":      r.bus_line,
                "latitude":   r.stop_lat + 0.003,
                "longitude":  r.stop_lon + 0.005,
                "velocidade": 30,
                "datahora":   "2026-03-05T18:00:00",
            }
            for r in registros
        ]

        print("\nDisparando check_alerts com ônibus fictícios...\n")
        check_alerts(onibus_falsos)
        print("Feito. Verifique a inbox do Mailtrap.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
