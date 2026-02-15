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
# ⚽ OBTENER PARTIDOS (CON LOGS EXTRA)
# ==============================
def obtener_partidos():
    from datetime import timezone
    # Buscamos desde AYER para asegurar que pille el de hoy
    ayer = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    date_from = ayer.isoformat()
    date_to = (ayer + timedelta(days=30)).isoformat()
    
    url = f"https://api.football-data.org{date_from}&dateTo={date_to}"
    headers = {"X-Auth-Token": FOOTBALL_API_TOKEN, "Accept": "application/json"}

    try:
        r = requests.get(url, headers=headers, timeout=20)
        print(f"📡 API responde con Status: {r.status_code}", flush=True)
        
        if r.status_code != 200:
            print(f"❌ Error API: {r.text}", flush=True)
            return []

        data = r.json()
        partidos = data.get("matches", [])
        print(f"📊 Total partidos recibidos de la API (toda la liga): {len(partidos)}", flush=True)
        return partidos
    except Exception as e:
        print(f"❌ Fallo total en la llamada API: {e}", flush=True)
        return []
# ==============================
# ▶️ PROGRAMA PRINCIPAL
# ==============================
# ==============================
# ⚽ OBTENER PARTIDOS (CON LOGS EXTRA)
# ==============================
def obtener_partidos():
    from datetime import timezone
    # Buscamos desde AYER para asegurar que pille el de hoy
    ayer = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    date_from = ayer.isoformat()
    date_to = (ayer + timedelta(days=30)).isoformat()
    
    url = f"https://api.football-data.org{date_from}&dateTo={date_to}"
    headers = {"X-Auth-Token": FOOTBALL_API_TOKEN, "Accept": "application/json"}

    try:
        r = requests.get(url, headers=headers, timeout=20)
        print(f"📡 API responde con Status: {r.status_code}", flush=True)
        
        if r.status_code != 200:
            print(f"❌ Error API: {r.text}", flush=True)
            return []

        data = r.json()
        partidos = data.get("matches", [])
        print(f"📊 Total partidos recibidos de la API (toda la liga): {len(partidos)}", flush=True)
        return partidos
    except Exception as e:
        print(f"❌ Fallo total en la llamada API: {e}", flush=True)
        return []

# ==============================
# ▶️ PROGRAMA PRINCIPAL (CON LOGS DE FILTRO)
# ==============================
def main():
    print("🚀 Bot iniciado. Vigilando al Real Oviedo...", flush=True)
    vistos = set()

    while True:
        try:
            print(f"\n--- 🔄 NUEVA REVISIÓN ({datetime.now().strftime('%H:%M:%S')}) ---", flush=True)
            partidos = obtener_partidos()

            encontrados_oviedo = 0
            for p in partidos:
                home = p.get("homeTeam", {}).get("name", "")
                away = p.get("awayTeam", {}).get("name", "")
                
                # LOG DE DEPURACIÓN: Ver cada partido que procesa
                # print(f"DEBUG: Procesando {home} vs {away}", flush=True)

                if "Oviedo" in home or "Oviedo" in away:
                    encontrados_oviedo += 1
                    partido_id = p.get("id")
                    
                    print(f"💙 ¡PARTIDO DEL OVIEDO DETECTADO!: {home} vs {away} (ID: {partido_id})", flush=True)

                    # Si quieres que te avise SIEMPRE para probar, comenta la línea de 'vistos'
                    # if partido_id in vistos: continue 

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

                    print(f"📤 Intentando enviar a Telegram...", flush=True)
                    if enviar_telegram(mensaje):
                        print(f"✅ Envío exitoso a Telegram.", flush=True)
                        vistos.add(partido_id)
                    else:
                        print(f"❌ Falló el envío a Telegram.", flush=True)

            if encontrados_oviedo == 0:
                print("ℹ️ No se encontró ningún partido del Oviedo en la lista recibida.", flush=True)

        except Exception as e:
            print(f"❌ Error en el bucle principal: {e}", flush=True)

        print(f"😴 Durmiendo {CHECK_MINUTES} min...", flush=True)
        time.sleep(CHECK_MINUTES * 60)
