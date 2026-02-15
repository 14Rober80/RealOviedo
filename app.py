import os
import requests
import time
import urllib.parse
import threading
from datetime import datetime, timedelta, timezone  # <-- Añadido timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

# Forzar logs instantáneos
os.environ['PYTHONUNBUFFERED'] = '1'

# ==============================
# 🔐 CONFIGURACIÓN
# ==============================
TELEGRAM_TOKEN = "8306658988:AAGdHj5gHUqfiXiVG6w-nQTG6ycfp5r6hGs"
TELEGRAM_CHAT_ID = "8537030546"
FOOTBALL_API_TOKEN = "9f58d46283da45ae8e210b7b11859da7"
CHECK_MINUTES = 30

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
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Servidor de salud activo en puerto {port}", flush=True)
    server.serve_forever()

threading.Thread(target=run_health_check, daemon=True).start()

# ==============================
# 📅 UTILIDAD CALENDARIO
# ==============================
def crear_link_calendar(rival, fecha_dt):
    start_time = fecha_dt.strftime('%Y%m%dT%H%M%SZ')
    end_time = (fecha_dt + timedelta(hours=2)).strftime('%Y%m%dT%H%M%SZ')
    titulo = urllib.parse.quote(f"⚽ Real Oviedo vs {rival}")
    url = f"https://www.google.com{titulo}&dates={start_time}/{end_time}"
    return url

# ==============================
# 📡 ENVIAR TELEGRAM
# ==============================
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=30)
        return r.status_code == 200
    except:
        return False

# ==============================
# ⚽ OBTENER PARTIDOS
# ==============================
def obtener_partidos():
    # Usamos timezone.utc corregido
    ayer = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    date_from = ayer.isoformat()
    date_to = (ayer + timedelta(days=30)).isoformat()
    
    url = f"https://api.football-data.org{date_from}&dateTo={date_to}"
    headers = {"X-Auth-Token": FOOTBALL_API_TOKEN, "Accept": "application/json"}

    try:
        r = requests.get(url, headers=headers, timeout=20)
        print(f"📡 API responde: {r.status_code}", flush=True)
        if r.status_code != 200: return []
        data = r.json()
        return data.get("matches", [])
    except Exception as e:
        print(f"❌ Error API: {e}", flush=True)
        return []

# ==============================
# ▶️ MAIN
# ==============================
def main():
    print("🚀 Bot iniciado correctamente...", flush=True)
    vistos = set()

    while True:
        try:
            print(f"🔄 Revisando partidos...", flush=True)
            partidos = obtener_partidos()
            print(f"📊 Partidos recibidos: {len(partidos)}", flush=True)

            for p in partidos:
                home = p.get("homeTeam", {}).get("name", "")
                away = p.get("awayTeam", {}).get("name", "")
                
                if "Oviedo" in home or "Oviedo" in away:
                    partido_id = p.get("id")
                    # COMENTA LA SIGUIENTE LÍNEA PARA QUE TE LLEGUEN TODOS AHORA:
                    # if partido_id in vistos: continue
                    
                    print(f"💙 Oviedo detectado: {home} vs {away}", flush=True)
                    
                    utc_iso = p.get("utcDate")
                    fecha_utc = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
                    rival = away if "Oviedo" in home else home
                    link_cal = crear_link_calendar(rival, fecha_utc)

                    mensaje = (
                        "📣 *¡Nuevo partido del Real Oviedo!*\n\n"
                        f"🆚 *Rival:* {rival}\n"
                        f"📅 *Fecha:* {fecha_utc.strftime('%d/%m/%Y %H:%M')} UTC\n\n"
                        f"📅 [Añadir a mi Google Calendar]({link_cal})"
                    )

                    if enviar_telegram(mensaje):
                        print("✅ Telegram OK", flush=True)
                        vistos.add(partido_id)
                    else:
                        print("❌ Telegram FAIL", flush=True)

        except Exception as e:
            print(f"❌ Error bucle: {e}", flush=True)

        time.sleep(CHECK_MINUTES * 60)

if __name__ == "__main__":
    main()
