import os
import requests
import time
import urllib.parse
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configuración
TELEGRAM_TOKEN = "8306658988:AAGdHj5gHUqfiXiVG6w-nQTG6ycfp5r6hGs"
TELEGRAM_CHAT_ID = "8537030546"
FOOTBALL_API_TOKEN = "9f58d46283da45ae8e210b7b11859da7"

# Servidor de Salud
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    httpd = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    httpd.serve_forever()

# Función enviar Telegram
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=20)
        return r.status_code == 200
    except:
        return False

# Bucle Principal
def main():
    print("🚀 Bot arrancando...", flush=True)
    threading.Thread(target=run_health_check, daemon=True).start()
    
    while True:
        try:
            print("🔄 Revisando partidos...", flush=True)
            ayer = (datetime.now(timezone.utc) - timedelta(days=1)).date()
            url = f"https://api.football-data.org{ayer.isoformat()}&dateTo={(ayer + timedelta(days=30)).isoformat()}"
            headers = {"X-Auth-Token": FOOTBALL_API_TOKEN}
            
            r = requests.get(url, headers=headers, timeout=20)
            partidos = r.json().get("matches", [])
            print(f"📊 Partidos en liga: {len(partidos)}", flush=True)

            for p in partidos:
                home = p.get("homeTeam", {}).get("name", "")
                away = p.get("awayTeam", {}).get("name", "")
                
                if "Oviedo" in home or "Oviedo" in away:
                    print(f"💙 Oviedo: {home} vs {away}", flush=True)
                    utc_iso = p.get("utcDate").replace("Z", "+00:00")
                    dt = datetime.fromisoformat(utc_iso)
                    
                    # Link Google Calendar
                    titulo = urllib.parse.quote(f"⚽ {home} vs {away}")
                    t_start = dt.strftime('%Y%m%dT%H%M%SZ')
                    t_end = (dt + timedelta(hours=2)).strftime('%Y%m%dT%H%M%SZ')
                    link = f"https://www.google.com{titulo}&dates={t_start}/{t_end}"
                    
                    msg = f"📣 *Partido del Oviedo*\n🆚 {home} vs {away}\n📅 {dt.strftime('%d/%m %H:%M')} UTC\n\n[Añadir a Google Calendar]({link})"
                    enviar_telegram(msg)

        except Exception as e:
            print(f"❌ Error: {e}", flush=True)
        
        time.sleep(1800)

if __name__ == "__main__":
    main()
