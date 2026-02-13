import os
import requests
import time
import urllib.parse
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

# Forzar logs instantáneos en Render
os.environ['PYTHONUNBUFFERED'] = '1'

# ==============================
# 🔐 CONFIGURACIÓN
# ==============================
TELEGRAM_TOKEN = "8306658988:AAGdHj5gHUqfiXiVG6w-nQTG6ycfp5r6hGs"
TELEGRAM_CHAT_ID = "8537030546"
FOOTBALL_API_TOKEN = "9f58d46283da45ae8e210b7b11859da7"
CHECK_MINUTES = 30
RETRY_COUNT = 2
RETRY_SLEEP_SEC = 3

# ==============================
# 🌐 SERVIDOR DE SALUD (Render)
# ==============================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check():
    # Render asigna el puerto automáticamente
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Servidor activo en puerto {port}", flush=True)
    server.serve_forever()

threading.Thread(target=run_health_check, daemon=True).start()

# ==============================
# 📅 UTILIDAD GOOGLE CALENDAR
# ==============================
def crear_link_calendar(rival, fecha_dt):
    """Genera link para añadir al calendario de Google."""
    # Formato UTC requerido por Google: YYYYMMDDTHHMMSSZ
    start_time = fecha_dt.strftime('%Y%m%dT%H%M%SZ')
    end_time = (fecha_dt + timedelta(hours=2)).strftime('%Y%m%dT%H%M%SZ')
    
    titulo = urllib.parse.quote(f"⚽ Real Oviedo vs {rival}")
    url = f"https://www.google.com{titulo}&dates={start_time}/{end_time}"
    return url

# ==============================
# 📡 ENVIAR MENSAJE TELEGRAM
# ==============================
def enviar_telegram(mensaje):
    # Fíjate en la barra después de .org y la palabra bot
    url = f"https://api.telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": mensaje,
        "parse_mode": "Markdown"
    }

# ==============================
# ⚽ OBTENER PARTIDOS (URL CORREGIDA)
# ==============================
def obtener_partidos():
    from datetime import timezone
    hoy = datetime.now(timezone.utc).date()
    date_from = hoy.isoformat()
    date_to = (hoy + timedelta(days=15)).isoformat()
    
    # URL fragmentada para evitar que se pegue al host
    host = "https://api.football-data.org"
    path = "/v4/competitions/PD/matches"
    params = f"?dateFrom={date_from}&dateTo={date_to}"
    url = host + path + params
    
    headers = {
        "X-Auth-Token": FOOTBALL_API_TOKEN, 
        "Accept": "application/json"
    }
    # ... resto de tu código ...

# ==============================
# ▶️ PROGRAMA PRINCIPAL
# ==============================
def main():
    print("🚀 Bot Real Oviedo iniciado (Primera División)...", flush=True)
    enviar_telegram("✅ ¡Bot del Real Oviedo activo!")
    vistos = set()

    while True:
        try:
            print(f"🔄 Revisando ({datetime.now().strftime('%H:%M:%S')})...", flush=True)
            partidos = obtener_partidos()

            if partidos == "ERROR_403":
                pass # Ya imprimió el error arriba
            elif partidos:
                encontrados = 0
                for p in partidos:
                    partido_id = p.get("id")
                    home = p.get("homeTeam", {}).get("name", "")
                    away = p.get("awayTeam", {}).get("name", "")

                    if partido_id in vistos or "Real Oviedo" not in [home, away]:
                        continue

                    # Procesar Fechas
                    utc_iso = p.get("utcDate")
                    fecha_utc = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
                    
                    try:
                        fecha_esp = fecha_utc.astimezone(ZoneInfo("Europe/Madrid"))
                    except:
                        fecha_esp = fecha_utc
                    
                    rival = away if home == "Real Oviedo" else home
                    link_cal = crear_link_calendar(rival, fecha_utc)

                    mensaje = (
                        "📣 *¡Nuevo partido del Real Oviedo!*\n\n"
                        f"🆚 *Rival:* {rival}\n"
                        f"📅 *Fecha:* {fecha_esp.strftime('%d/%m/%Y %H:%M')}\n\n"
                        f"📅 [Añadir a mi Google Calendar]({link_cal})"
                    )

                    if enviar_telegram(mensaje):
                        vistos.add(partido_id)
                        encontrados += 1

                print(f"✔ Revisión OK. Partidos del Oviedo enviados: {encontrados}", flush=True)

        except Exception as e:
            print(f"❌ Error bucle: {e}", flush=True)

        time.sleep(CHECK_MINUTES * 60)

if __name__ == "__main__":
    main()
