
import os
import sys
import requests
import time
from datetime import datetime, timedelta  # <-- AÑADIDO timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from zoneinfo import ZoneInfo
from urllib3.exceptions import NameResolutionError

# Forzar logs instantáneos
os.environ['PYTHONUNBUFFERED'] = '1'

# ==============================
# 🔐 CONFIGURACIÓN
# ==============================
TELEGRAM_TOKEN = "8306658988:AAGdHj5gHUqfiXiVG6w-nQTG6ycfp5r6hGs"
TELEGRAM_CHAT_ID = "8537030546"
FOOTBALL_API_TOKEN = "9f58d46283da45ae8e210b7b11859da7"
CHECK_MINUTES = 30

# Retries rápidos internos para llamadas de red (evita bucle infinito si DNS falla)
RETRY_COUNT = 2
RETRY_SLEEP_SEC = 3

# ==============================
# 🌐 SERVIDOR DE SALUD
# ==============================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check():
    try:
        server = HTTPServer(('0.0.0.0', 7860), HealthCheckHandler)
        print("✅ Servidor de salud activo en puerto 7860", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"❌ Error servidor salud: {e}", flush=True)

threading.Thread(target=run_health_check, daemon=True).start()

# ==============================
# 📡 ENVIAR MENSAJE TELEGRAM
# ==============================
def enviar_telegram(mensaje):
    """
    Envía mensaje a Telegram, pero si hay error de DNS o red no revienta el bucle principal.
    Hace un pequeño retry local.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}

    for intento in range(1, RETRY_COUNT + 1):
        try:
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Error Telegram: {e}", flush=True)
            if hasattr(e, 'response') and e.response is not None:
                print(f"🔍 Detalle técnico de Telegram: {e.response.text}", flush=True)
            if intento < RETRY_COUNT:
                time.sleep(RETRY_SLEEP_SEC)
    # No devolvemos excepción para no parar el proceso
    return False

# ==============================
# ⚽ OBTENER PARTIDOS
# ==============================
def obtener_partidos():
    """
    Usa el endpoint v4 de football-data para LaLiga (PD) en un rango de fechas corto.
    Si 403 -> plan no cubre; si 429 -> rate limit, se espera un poco y se devuelve [].
    """
    hoy = datetime.utcnow().date()
    date_from = hoy.isoformat()
    date_to = (hoy + timedelta(days=10)).isoformat()

    url = (
        "https://api.football-data.org/v4/competitions/PD/matches"
        f"?dateFrom={date_from}&dateTo={date_to}"
    )

    headers = {
        "X-Auth-Token": FOOTBALL_API_TOKEN,
        "Accept": "application/json"
    }

    for intento in range(1, RETRY_COUNT + 1):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 403:
                # La capa gratuita podría no cubrir esta competición o el token no vale
                return "ERROR_403"
            if r.status_code == 429:
                print("⚠️ Rate limit 429 en football-data. Esperando 60s...", flush=True)
                time.sleep(60)
                return []

            r.raise_for_status()
            data = r.json()
            return data.get("matches", [])

        except requests.exceptions.JSONDecodeError:
            print(f"❌ Respuesta no JSON de football-data. Status={getattr(r, 'status_code', '?')}\n"
                  f"Cuerpo (500 chars):\n{getattr(r, 'text', '')[:500]}", flush=True)
            return []

        except requests.exceptions.RequestException as e:
            print(f"❌ Error API Fútbol (intento {intento}/{RETRY_COUNT}): {e}", flush=True)
            if intento < RETRY_COUNT:
                time.sleep(RETRY_SLEEP_SEC)

        except Exception as e:
            print(f"❌ Error inesperado API Fútbol: {e}", flush=True)
            return []

    return []

# ==============================
# ▶️ PROGRAMA PRINCIPAL
# ==============================
def main():
    print("🚀 Bot Real Oviedo iniciado (v1.6)...", flush=True)

    ok_tg = enviar_telegram("✅ ¡Bot del Real Oviedo activo!")
    if not ok_tg:
        print("⚠️ No se pudo notificar en Telegram (posible DNS/proxy). Continuo ejecución...", flush=True)

    vistos = set()

    while True:
        try:
            ahora = datetime.now().strftime('%H:%M:%S')
            print(f"🔄 Revisando partidos ({ahora})...", flush=True)

            partidos = obtener_partidos()

            if partidos == "ERROR_403":
                print("⚠️ Error 403: La API/plan no cubre esta competición o token inválido.", flush=True)
            elif not partidos:
                print("✔ No hay partidos nuevos.", flush=True)
            else:
                encontrados = 0
                for p in partidos:
                    partido_id = p.get("id")
                    if not partido_id or partido_id in vistos:
                        continue

                    home = p.get("homeTeam", {}).get("name", "Local")
                    away = p.get("awayTeam", {}).get("name", "Visitante")

                    # Filtrar solo partidos donde juegue el Real Oviedo
                    if "Real Oviedo" not in (home, away):
                        continue

                    # Fecha
                    utc_iso = p.get("utcDate")
                    if not utc_iso:
                        continue
                    fecha = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))

                    # Convertir UTC → Hora España
                    try:
                        fecha_esp = fecha.astimezone(ZoneInfo("Europe/Madrid"))
                    except Exception:
                        # Si por cualquier motivo falla zoneinfo, al menos muestra UTC
                        fecha_esp = fecha

                    rival = away if home == "Real Oviedo" else home

                    mensaje = (
                        "📣 Nuevo partido del Real Oviedo\n\n"
                        f"🆚 Rival: {rival}\n"
                        f"📅 Fecha: {fecha_esp.strftime('%d/%m/%Y %H:%M')}"
                    )

                    enviar_telegram(mensaje)
                    vistos.add(partido_id)
                    encontrados += 1

                print(f"✔ Revisión OK ({len(partidos)} partidos recibidos, {encontrados} del Oviedo)", flush=True)

        except Exception as e:
            print(f"❌ Error bucle: {e}", flush=True)

        time.sleep(CHECK_MINUTES * 60)

if __name__ == "__main__":
    main()
