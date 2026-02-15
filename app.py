import os
import requests
import time
import urllib.parse
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

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

# ==============================
# 📡 ENVIAR MENSAJE TELEGRAM
# ==============================
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=20)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}", flush=True)
        return False

# ==============================
# ▶️ PROGRAMA PRINCIPAL
# ==============================
def main():
    print("🚀 Bot Real Oviedo v2.0 arrancando...", flush=True)
    threading.Thread(target=run_health_check, daemon=True).start()
    
    vistos = set()

    while True:
        try:
            print(f"\n🔄 REVISIÓN: {datetime.now().strftime('%H:%M:%S')}", flush=True)
            
            # 1. FECHAS (Corregido para evitar el 'deprecated' de utcnow)
            ahora_utc = datetime.now(timezone.utc)
            ayer = (ahora_utc - timedelta(days=1)).strftime('%Y-%m-%d')
            futuro = (ahora_utc + timedelta(days=30)).strftime('%Y-%m-%d')
            
            # 2. URL CONSTRUIDA DE FORMA SEGURA (Evita NameResolutionError)
            # Usamos params separados para que 'requests' monte la URL correctamente
            url_base = "https://api.football-data.org"
            parametros = {
                "dateFrom": ayer,
                "dateTo": futuro
            }
            headers = {
                "X-Auth-Token": FOOTBALL_API_TOKEN, 
                "Accept": "application/json"
            }
            
            print(f"📡 Solicitando partidos desde {ayer} hasta {futuro}...", flush=True)
            
            # Dejamos que la librería 'requests' gestione la unión de la URL y los parámetros
            r = requests.get(url_base, headers=headers, params=parametros, timeout=25)
            
            if r.status_code != 200:
                print(f"⚠️ Error API {r.status_code}: {r.text}", flush=True)
                partidos = []
            else:
                data = r.json()
                partidos = data.get("matches", [])
            
            print(f"📊 Partidos totales en liga recibidos: {len(partidos)}", flush=True)

            # 3. FILTRADO OVIEDO
            for p in partidos:
                home = p.get("homeTeam", {}).get("name", "")
                away = p.get("awayTeam", {}).get("name", "")
                
                if "Oviedo" in home or "Oviedo" in away:
                    p_id = p.get("id")
                    
                    # COMENTA LA SIGUIENTE LÍNEA SI QUIERES QUE TE LLEGUEN AUNQUE YA SE ENVIARAN
                    # if p_id in vistos: continue
                    
                    print(f"💙 ¡DETECTADO!: {home} vs {away}", flush=True)
                    
                    # Fecha y link calendario
                    utc_str = p.get("utcDate")
                    dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
                    
                    rival = away if "Oviedo" in home else home
                    t_start = dt_utc.strftime('%Y%m%dT%H%M%SZ')
                    t_end = (dt_utc + timedelta(hours=2)).strftime('%Y%m%dT%H%M%SZ')
                    
                    titulo_cal = urllib.parse.quote(f"⚽ {home} vs {away}")
                    link = f"https://www.google.com{titulo_cal}&dates={t_start}/{t_end}"
                    
                    mensaje = (
                        "📣 *¡Nuevo partido del Real Oviedo!*\n\n"
                        f"🆚 *Rival:* {rival}\n"
                        f"📅 *Fecha:* {dt_utc.strftime('%d/%m/%Y %H:%M')} UTC\n\n"
                        f"📅 [Añadir a mi Google Calendar]({link})"
                    )

                    if enviar_telegram(mensaje):
                        print(f"✅ Telegram OK: {rival}", flush=True)
                        vistos.add(p_id)

        except Exception as e:
            print(f"❌ Error en el bucle: {e}", flush=True)
        
        print(f"😴 Esperando {CHECK_MINUTES} minutos...", flush=True)
        time.sleep(CHECK_MINUTES * 60)

if __name__ == "__main__":
    main()
