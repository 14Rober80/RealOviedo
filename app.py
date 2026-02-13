import os
import sys
import requests
import time
import urllib.parse
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Forzar logs instantáneos
os.environ['PYTHONUNBUFFERED'] = '1'

# ==============================
# 🔐 CONFIGURACIÓN
# ==============================
TELEGRAM_TOKEN = "8306658988:AAGdHj5gHUqfiXiVG6w-nQTG6ycfp5r6hGs"
TELEGRAM_CHAT_ID = "8537030546"
FOOTBALL_API_TOKEN = "9f58d46283da45ae8e210b7b11859da7"
CHECK_MINUTES = 30

# Forzar logs instantáneos en Render
os.environ['PYTHONUNBUFFERED'] = '1'

# ==============================
# 🌐 SERVIDOR DE SALUD (Para Render)
# ==============================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check():
    # Render asigna el puerto automáticamente en la variable PORT
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Servidor de salud activo en puerto {port}", flush=True)
    server.serve_forever()

# ==============================
# 📅 UTILIDAD CALENDARIO
# ==============================
def crear_link_google_calendar(partido, fecha_iso):
    """
    Convierte una fecha de la API (2026-02-15T21:00:00Z) 
    al formato de Google (20260215T210000Z).
    """
    formato_google = fecha_iso.replace("-", "").replace(":", "")
    titulo = urllib.parse.quote(f"⚽ {partido}")
    url = f"https://www.google.com{titulo}&dates={formato_google}/{formato_google}"
    return url

# ==============================
# 📡 ENVIAR MENSAJE TELEGRAM
# ==============================
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": mensaje,
        "parse_mode": "Markdown"  # Permite enlaces clicables
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        print("📤 Mensaje enviado a Telegram", flush=True)
    except Exception as e:
        print(f"❌ Error Telegram: {e}", flush=True)

# ==============================
# ⚽ LÓGICA PRINCIPAL
# ==============================
def buscar_partidos():
    print("🔍 Buscando partidos...", flush=True)
    url = "https://api.football-data.org"
    headers = {"X-Auth-Token": FOOTBALL_API_TOKEN}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        for match in data.get('matches', []):
            home_team = match['homeTeam']['name']
            away_team = match['awayTeam']['name']
            fecha = match['utcDate'] # Ejemplo: 2026-02-15T21:00:00Z
            
            partido_txt = f"{home_team} vs {away_team}"
            link_cal = crear_link_google_calendar(partido_txt, fecha)
            
            mensaje = (
                f"📌 *Nuevo Partido Encontrado*\n"
                f"🏟️ {partido_txt}\n"
                f"⏰ {fecha}\n\n"
                f"➕ [Añadir a mi Google Calendar]({link_cal})"
            )
            
            enviar_telegram(mensaje)
            
    except Exception as e:
        print(f"❌ Error API Fútbol: {e}", flush=True)

# ==============================
# 🚀 ARRANQUE
# ==============================
if __name__ == "__main__":
    # 1. Iniciar servidor de salud en un hilo separado
    threading.Thread(target=run_health_check, daemon=True).start()
    
    # 2. Bucle infinito de búsqueda
    while True:
        buscar_partidos()
        print(f"😴 Durmiendo 30 minutos...", flush=True)
        time.sleep(1800) # 30 minutos
