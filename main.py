"""
Economic Calendar Alert System v2
Usa Finnhub API (gratuita y confiable) para obtener eventos económicos
Notifica ANTES y DESPUÉS del evento con resultados
"""

import requests
from datetime import datetime, timedelta
import pytz
import os
import json

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════

# Finnhub API (obtener gratis en https://finnhub.io/register)
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', 'tu_finnhub_api_key')

# Twilio
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'tu_account_sid')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'tu_auth_token')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

# Números destino (separados por coma)
WHATSAPP_RECIPIENTS = os.environ.get('WHATSAPP_RECIPIENTS', 'whatsapp:+56912345678').split(',')

# Países/divisas a monitorear
COUNTRIES_TO_MONITOR = ['US', 'EU', 'GB', 'JP', 'AU', 'CA', 'CH', 'NZ']

# Minutos antes del evento para alertar
ALERT_MINUTES_BEFORE = 30

# Timezone
TIMEZONE = 'America/Santiago'

# Archivo para trackear eventos notificados
NOTIFIED_FILE = '/tmp/notified_events.json'
RESULTS_FILE = '/tmp/pending_results.json'

# ═══════════════════════════════════════════════════════════════════════════
# FINNHUB API
# ═══════════════════════════════════════════════════════════════════════════

def get_finnhub_events():
    """Obtiene eventos económicos de Finnhub API"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    url = "https://finnhub.io/api/v1/calendar/economic"
    params = {
        'from': today,
        'to': tomorrow,
        'token': FINNHUB_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        events = []
        for item in data.get('economicCalendar', []):
            # Filtrar solo alto impacto y países monitoreados
            impact = item.get('impact', '').lower()
            country = item.get('country', '')
            
            if impact != 'high':
                continue
            
            if country not in COUNTRIES_TO_MONITOR:
                continue
            
            # Parsear fecha/hora
            event_time = item.get('time', '')
            if not event_time:
                continue
            
            try:
                # Finnhub usa formato ISO
                dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                dt_utc = dt.astimezone(pytz.UTC)
            except:
                continue
            
            events.append({
                'id': item.get('id', ''),
                'datetime': dt_utc,
                'country': country,
                'event': item.get('event', ''),
                'impact': 'HIGH',
                'estimate': item.get('estimate'),
                'prev': item.get('prev'),
                'actual': item.get('actual'),
                'unit': item.get('unit', '')
            })
        
        return events
        
    except Exception as e:
        print(f"Error Finnhub: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════
# ALTERNATIVA: FCS API (gratuita)
# ═══════════════════════════════════════════════════════════════════════════

def get_fcsapi_events():
    """Alternativa usando FCS API (gratuita, requiere registro)"""
    
    # FCS API key (obtener en https://fcsapi.com/)
    FCS_API_KEY = os.environ.get('FCS_API_KEY', '')
    
    if not FCS_API_KEY:
        return []
    
    url = "https://fcsapi.com/api-v3/forex/economy_cal"
    params = {
        'access_key': FCS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        events = []
        for item in data.get('response', []):
            if item.get('impact', '').lower() != 'high':
                continue
            
            country = item.get('country', '')
            if country not in COUNTRIES_TO_MONITOR:
                continue
            
            # Parsear fecha/hora
            date_str = item.get('date', '')
            time_str = item.get('time', '')
            
            if date_str and time_str:
                try:
                    dt_str = f"{date_str} {time_str}"
                    dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                    dt_utc = pytz.UTC.localize(dt)
                    
                    events.append({
                        'id': item.get('id', ''),
                        'datetime': dt_utc,
                        'country': country,
                        'event': item.get('title', ''),
                        'impact': 'HIGH',
                        'estimate': item.get('forecast'),
                        'prev': item.get('previous'),
                        'actual': item.get('actual'),
                        'unit': ''
                    })
                except:
                    continue
        
        return events
        
    except Exception as e:
        print(f"Error FCS API: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════
# WHATSAPP VIA TWILIO
# ═══════════════════════════════════════════════════════════════════════════

def send_whatsapp(message):
    """Envía mensaje de WhatsApp via Twilio"""
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    
    for recipient in WHATSAPP_RECIPIENTS:
        recipient = recipient.strip()
        
        data = {
            'From': TWILIO_WHATSAPP_FROM,
            'To': recipient,
            'Body': message
        }
        
        try:
            response = requests.post(
                url,
                data=data,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                timeout=30
            )
            
            if response.status_code == 201:
                print(f"✓ WhatsApp enviado a {recipient}")
            else:
                print(f"✗ Error enviando a {recipient}: {response.text}")
                
        except Exception as e:
            print(f"✗ Excepción enviando a {recipient}: {e}")


def format_pre_event_message(event):
    """Formatea mensaje PRE-evento"""
    
    local_tz = pytz.timezone(TIMEZONE)
    local_time = event['datetime'].astimezone(local_tz)
    
    # Mapeo de países a banderas
    flags = {
        'US': '🇺🇸', 'EU': '🇪🇺', 'GB': '🇬🇧', 'JP': '🇯🇵',
        'AU': '🇦🇺', 'CA': '🇨🇦', 'CH': '🇨🇭', 'NZ': '🇳🇿'
    }
    flag = flags.get(event['country'], '🌍')
    
    message = f"""
🔴 *EVENTO PRÓXIMO* {flag}

📅 {local_time.strftime('%d/%m/%Y')}
⏰ {local_time.strftime('%H:%M')} (Chile)
🏛️ {event['country']}
📊 {event['event']}

📈 Pronóstico: {event.get('estimate') or 'N/A'}
📉 Anterior: {event.get('prev') or 'N/A'}

⚠️ Considerar gestionar posiciones
"""
    return message.strip()


def format_post_event_message(event):
    """Formatea mensaje POST-evento con resultados"""
    
    local_tz = pytz.timezone(TIMEZONE)
    local_time = event['datetime'].astimezone(local_tz)
    
    flags = {
        'US': '🇺🇸', 'EU': '🇪🇺', 'GB': '🇬🇧', 'JP': '🇯🇵',
        'AU': '🇦🇺', 'CA': '🇨🇦', 'CH': '🇨🇭', 'NZ': '🇳🇿'
    }
    flag = flags.get(event['country'], '🌍')
    
    actual = event.get('actual')
    estimate = event.get('estimate')
    prev = event.get('prev')
    
    # Determinar si fue mejor o peor de lo esperado
    sentiment = ""
    if actual is not None and estimate is not None:
        try:
            actual_val = float(str(actual).replace('%', '').replace(',', '').replace('K', '000').replace('M', '000000'))
            estimate_val = float(str(estimate).replace('%', '').replace(',', '').replace('K', '000').replace('M', '000000'))
            if actual_val > estimate_val:
                sentiment = "📈 *MEJOR* de lo esperado"
            elif actual_val < estimate_val:
                sentiment = "📉 *PEOR* de lo esperado"
            else:
                sentiment = "➡️ *IGUAL* a lo esperado"
        except:
            sentiment = ""
    
    message = f"""
✅ *RESULTADO PUBLICADO* {flag}

📊 {event['event']}
⏰ {local_time.strftime('%H:%M')} (Chile)

🎯 *Actual: {actual or 'N/A'}*
📈 Pronóstico: {estimate or 'N/A'}
📉 Anterior: {prev or 'N/A'}

{sentiment}
"""
    return message.strip()


# ═══════════════════════════════════════════════════════════════════════════
# GESTIÓN DE ESTADO
# ═══════════════════════════════════════════════════════════════════════════

def load_json_file(filepath):
    """Carga archivo JSON"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Limpiar eventos viejos (más de 48 horas)
            cutoff = (datetime.now() - timedelta(hours=48)).isoformat()
            cleaned = {}
            for k, v in data.items():
                ts = v.get('timestamp', v) if isinstance(v, dict) else v
                if ts > cutoff:
                    cleaned[k] = v
            return cleaned
    except:
        return {}


def save_json_file(filepath, data):
    """Guarda archivo JSON"""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error guardando {filepath}: {e}")


def get_event_id(event):
    """Genera ID único para un evento"""
    return f"{event['datetime'].isoformat()}_{event['country']}_{event['event'][:30]}"


# ═══════════════════════════════════════════════════════════════════════════
# LÓGICA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

def check_pre_events(events):
    """Verifica y notifica eventos próximos"""
    
    now = datetime.now(pytz.UTC)
    alert_window_start = now
    alert_window_end = now + timedelta(minutes=ALERT_MINUTES_BEFORE + 5)
    
    notified = load_json_file(NOTIFIED_FILE)
    pending_results = load_json_file(RESULTS_FILE)
    
    for event in events:
        event_id = get_event_id(event)
        
        # Verificar si el evento está en la ventana de alerta
        if not (alert_window_start <= event['datetime'] <= alert_window_end):
            continue
        
        # Verificar si ya fue notificado
        if event_id in notified:
            continue
        
        print(f"\n📢 Notificando evento próximo: {event['event']}")
        message = format_pre_event_message(event)
        send_whatsapp(message)
        
        # Marcar como notificado
        notified[event_id] = {'timestamp': datetime.now().isoformat(), 'type': 'pre'}
        
        # Agregar a pendientes de resultado
        pending_results[event_id] = {
            'timestamp': datetime.now().isoformat(),
            'event_time': event['datetime'].isoformat(),
            'country': event['country'],
            'event': event['event'],
            'estimate': event.get('estimate'),
            'prev': event.get('prev')
        }
    
    save_json_file(NOTIFIED_FILE, notified)
    save_json_file(RESULTS_FILE, pending_results)


def check_post_events(events):
    """Verifica y notifica resultados de eventos pasados"""
    
    now = datetime.now(pytz.UTC)
    pending_results = load_json_file(RESULTS_FILE)
    notified = load_json_file(NOTIFIED_FILE)
    
    events_by_id = {}
    for event in events:
        event_id = get_event_id(event)
        events_by_id[event_id] = event
    
    to_remove = []
    
    for event_id, pending in pending_results.items():
        # Verificar si ya pasó el evento (al menos 5 minutos)
        try:
            event_time = datetime.fromisoformat(pending['event_time'])
            if event_time.tzinfo is None:
                event_time = pytz.UTC.localize(event_time)
        except:
            continue
        
        if now < event_time + timedelta(minutes=5):
            continue  # Aún no ha pasado suficiente tiempo
        
        # Buscar el evento actualizado con resultados
        if event_id in events_by_id:
            event = events_by_id[event_id]
            actual = event.get('actual')
            
            if actual is not None:
                # Verificar si ya notificamos el resultado
                result_key = f"{event_id}_result"
                if result_key not in notified:
                    print(f"\n📊 Notificando resultado: {event['event']} = {actual}")
                    message = format_post_event_message(event)
                    send_whatsapp(message)
                    
                    notified[result_key] = {'timestamp': datetime.now().isoformat(), 'type': 'post'}
                    to_remove.append(event_id)
        
        # Si pasaron más de 2 horas sin resultado, eliminar de pendientes
        if now > event_time + timedelta(hours=2):
            to_remove.append(event_id)
    
    # Limpiar pendientes procesados
    for event_id in to_remove:
        if event_id in pending_results:
            del pending_results[event_id]
    
    save_json_file(RESULTS_FILE, pending_results)
    save_json_file(NOTIFIED_FILE, notified)


def main():
    """Función principal"""
    
    print(f"\n{'='*50}")
    print(f"Economic Calendar Alert v2 - {datetime.now()}")
    print(f"{'='*50}\n")
    
    # Obtener eventos (intentar Finnhub primero)
    print("Consultando Finnhub API...")
    events = get_finnhub_events()
    
    if not events:
        print("Finnhub sin resultados, intentando FCS API...")
        events = get_fcsapi_events()
    
    if not events:
        print("No se pudieron obtener eventos de ninguna fuente.")
        print("Verifica que FINNHUB_API_KEY esté configurado correctamente.")
        return
    
    print(f"Encontrados {len(events)} eventos de alto impacto")
    
    # Listar eventos del día
    local_tz = pytz.timezone(TIMEZONE)
    print("\nEventos de hoy:")
    for e in sorted(events, key=lambda x: x['datetime']):
        local_time = e['datetime'].astimezone(local_tz)
        actual_str = f" | Actual: {e['actual']}" if e.get('actual') else ""
        print(f"  {local_time.strftime('%H:%M')} - {e['country']} - {e['event']}{actual_str}")
    
    # Verificar eventos próximos (PRE)
    print("\nVerificando eventos próximos...")
    check_pre_events(events)
    
    # Verificar resultados pendientes (POST)
    print("\nVerificando resultados pendientes...")
    check_post_events(events)
    
    print("\n✓ Proceso completado")


if __name__ == "__main__":
    main()
