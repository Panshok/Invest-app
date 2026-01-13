"""
Economic Calendar Alert System v3
Usa mirror público de Forex Factory (no bloquea IPs de datacenter)
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

# Twilio
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'tu_account_sid')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'tu_auth_token')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

# Números destino (separados por coma)
WHATSAPP_RECIPIENTS = os.environ.get('WHATSAPP_RECIPIENTS', 'whatsapp:+56912345678').split(',')

# Países/divisas a monitorear
CURRENCIES_TO_MONITOR = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']

# Minutos antes del evento para alertar
ALERT_MINUTES_BEFORE = 30

# Timezone
TIMEZONE = 'America/Santiago'

# Archivos de estado
NOTIFIED_FILE = '/tmp/notified_events.json'
RESULTS_FILE = '/tmp/pending_results.json'

# ═══════════════════════════════════════════════════════════════════════════
# FOREX FACTORY JSON (Mirror público - no bloquea)
# ═══════════════════════════════════════════════════════════════════════════

def get_ff_calendar_events():
    """Obtiene eventos de Forex Factory via mirror JSON público"""
    
    # Mirror público mantenido por faireconomy.media
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; EconomicCalendarBot/1.0)',
        'Accept': 'application/json'
    }
    
    try:
        print(f"Consultando: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        events = []
        now = datetime.now(pytz.UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = today_start + timedelta(days=2)
        
        for item in data:
            # Filtrar solo alto impacto
            impact = item.get('impact', '').lower()
            if impact not in ['high', 'holiday']:
                continue
            
            # Filtrar por moneda
            currency = item.get('country', '')
            if currency not in CURRENCIES_TO_MONITOR:
                continue
            
            # Parsear fecha/hora
            date_str = item.get('date', '')  # formato: "2026-01-13 08:30:00"
            if not date_str:
                continue
            
            try:
                # El calendario puede venir en formato ISO con timezone
                date_str = date_str.strip()
                
                # Intentar formato ISO primero (2026-01-13T08:30:00-05:00)
                if 'T' in date_str:
                    dt_utc = datetime.fromisoformat(date_str).astimezone(pytz.UTC)
                else:
                    # Formato alternativo: 2026-01-13 08:30:00 (Eastern Time)
                    et_tz = pytz.timezone('America/New_York')
                    dt_naive = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    dt_et = et_tz.localize(dt_naive)
                    dt_utc = dt_et.astimezone(pytz.UTC)
                
                # Solo eventos de hoy y mañana
                if not (today_start <= dt_utc <= tomorrow_end):
                    continue
                
            except Exception as e:
                print(f"Error parseando fecha '{date_str}': {e}")
                continue
            
            events.append({
                'id': f"{date_str}_{currency}_{item.get('title', '')[:20]}",
                'datetime': dt_utc,
                'country': currency,
                'event': item.get('title', ''),
                'impact': impact.upper(),
                'estimate': item.get('forecast', ''),
                'prev': item.get('previous', ''),
                'actual': item.get('actual', ''),
            })
        
        return events
        
    except Exception as e:
        print(f"Error obteniendo calendario FF: {e}")
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
    
    # Mapeo de monedas a banderas
    flags = {
        'USD': '🇺🇸', 'EUR': '🇪🇺', 'GBP': '🇬🇧', 'JPY': '🇯🇵',
        'AUD': '🇦🇺', 'CAD': '🇨🇦', 'CHF': '🇨🇭', 'NZD': '🇳🇿'
    }
    flag = flags.get(event['country'], '🌍')
    
    estimate = event.get('estimate') or 'N/A'
    prev = event.get('prev') or 'N/A'
    
    message = f"""🔴 *EVENTO PRÓXIMO* {flag}

📅 {local_time.strftime('%d/%m/%Y')}
⏰ {local_time.strftime('%H:%M')} (Chile)
💱 {event['country']}
📊 {event['event']}

📈 Pronóstico: {estimate}
📉 Anterior: {prev}

⚠️ Considerar gestionar posiciones"""
    
    return message


def format_post_event_message(event):
    """Formatea mensaje POST-evento con resultados"""
    
    local_tz = pytz.timezone(TIMEZONE)
    local_time = event['datetime'].astimezone(local_tz)
    
    flags = {
        'USD': '🇺🇸', 'EUR': '🇪🇺', 'GBP': '🇬🇧', 'JPY': '🇯🇵',
        'AUD': '🇦🇺', 'CAD': '🇨🇦', 'CHF': '🇨🇭', 'NZD': '🇳🇿'
    }
    flag = flags.get(event['country'], '🌍')
    
    actual = event.get('actual') or 'N/A'
    estimate = event.get('estimate') or 'N/A'
    prev = event.get('prev') or 'N/A'
    
    # Determinar si fue mejor o peor de lo esperado
    sentiment = ""
    if actual != 'N/A' and actual != '' and estimate != 'N/A' and estimate != '':
        try:
            # Limpiar valores para comparar
            def clean_value(v):
                v = str(v).replace('%', '').replace(',', '').replace('K', '000').replace('M', '000000').replace('B', '000000000')
                v = v.replace('<', '').replace('>', '').strip()
                return float(v) if v else None
            
            actual_val = clean_value(actual)
            estimate_val = clean_value(estimate)
            
            if actual_val is not None and estimate_val is not None:
                if actual_val > estimate_val:
                    sentiment = "\n\n📈 *MEJOR* de lo esperado"
                elif actual_val < estimate_val:
                    sentiment = "\n\n📉 *PEOR* de lo esperado"
                else:
                    sentiment = "\n\n➡️ *IGUAL* a lo esperado"
        except:
            pass
    
    message = f"""✅ *RESULTADO PUBLICADO* {flag}

📊 {event['event']}
⏰ {local_time.strftime('%H:%M')} (Chile)

🎯 *Actual: {actual}*
📈 Pronóstico: {estimate}
📉 Anterior: {prev}{sentiment}"""
    
    return message


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
                ts = v.get('timestamp', '') if isinstance(v, dict) else str(v)
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
    dt_str = event['datetime'].strftime('%Y%m%d_%H%M')
    return f"{dt_str}_{event['country']}_{event['event'][:25]}"


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
    
    notified_count = 0
    
    for event in events:
        event_id = get_event_id(event)
        
        # Verificar si el evento está en la ventana de alerta
        if not (alert_window_start <= event['datetime'] <= alert_window_end):
            continue
        
        # Verificar si ya fue notificado
        pre_key = f"{event_id}_pre"
        if pre_key in notified:
            continue
        
        print(f"\n📢 Notificando evento próximo: {event['event']}")
        message = format_pre_event_message(event)
        send_whatsapp(message)
        notified_count += 1
        
        # Marcar como notificado
        notified[pre_key] = {'timestamp': datetime.now().isoformat(), 'type': 'pre'}
        
        # Agregar a pendientes de resultado
        pending_results[event_id] = {
            'timestamp': datetime.now().isoformat(),
            'event_time': event['datetime'].isoformat(),
            'country': event['country'],
            'event': event['event'],
            'estimate': event.get('estimate', ''),
            'prev': event.get('prev', '')
        }
    
    save_json_file(NOTIFIED_FILE, notified)
    save_json_file(RESULTS_FILE, pending_results)
    
    return notified_count


def check_post_events(events):
    """Verifica y notifica resultados de eventos pasados"""
    
    now = datetime.now(pytz.UTC)
    pending_results = load_json_file(RESULTS_FILE)
    notified = load_json_file(NOTIFIED_FILE)
    
    # Crear mapa de eventos por características
    events_map = {}
    for event in events:
        # Crear varias keys para matching flexible
        event_id = get_event_id(event)
        events_map[event_id] = event
    
    to_remove = []
    notified_count = 0
    
    for event_id, pending in list(pending_results.items()):
        # Verificar si ya pasó el evento (al menos 10 minutos)
        try:
            event_time_str = pending.get('event_time', '')
            if not event_time_str:
                continue
            event_time = datetime.fromisoformat(event_time_str)
            if event_time.tzinfo is None:
                event_time = pytz.UTC.localize(event_time)
        except:
            continue
        
        if now < event_time + timedelta(minutes=10):
            continue  # Aún no ha pasado suficiente tiempo
        
        # Buscar el evento actualizado con resultados
        if event_id in events_map:
            event = events_map[event_id]
            actual = event.get('actual', '')
            
            if actual and actual.strip():
                # Verificar si ya notificamos el resultado
                post_key = f"{event_id}_post"
                if post_key not in notified:
                    print(f"\n📊 Notificando resultado: {event['event']} = {actual}")
                    message = format_post_event_message(event)
                    send_whatsapp(message)
                    notified_count += 1
                    
                    notified[post_key] = {'timestamp': datetime.now().isoformat(), 'type': 'post'}
                    to_remove.append(event_id)
        
        # Si pasaron más de 3 horas sin resultado, eliminar de pendientes
        if now > event_time + timedelta(hours=3):
            print(f"⏰ Evento expirado sin resultado: {pending.get('event', event_id)}")
            to_remove.append(event_id)
    
    # Limpiar pendientes procesados
    for event_id in set(to_remove):
        if event_id in pending_results:
            del pending_results[event_id]
    
    save_json_file(RESULTS_FILE, pending_results)
    save_json_file(NOTIFIED_FILE, notified)
    
    return notified_count


def main():
    """Función principal"""
    
    print(f"\n{'='*55}")
    print(f"Economic Calendar Alert v3 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}\n")
    
    # Obtener eventos
    events = get_ff_calendar_events()
    
    if not events:
        print("No se encontraron eventos de alto impacto para hoy/mañana.")
        print("Esto puede ser normal si no hay eventos programados.")
        return
    
    print(f"✓ Encontrados {len(events)} eventos de alto impacto\n")
    
    # Listar eventos
    local_tz = pytz.timezone(TIMEZONE)
    print("Eventos programados:")
    print("-" * 55)
    for e in sorted(events, key=lambda x: x['datetime']):
        local_time = e['datetime'].astimezone(local_tz)
        actual_str = f" → Actual: {e['actual']}" if e.get('actual') else ""
        print(f"  {local_time.strftime('%d/%m %H:%M')} | {e['country']} | {e['event'][:35]}{actual_str}")
    print("-" * 55)
    
    # Verificar eventos próximos (PRE)
    print("\nVerificando eventos próximos (ventana de 30 min)...")
    pre_count = check_pre_events(events)
    print(f"  → {pre_count} notificaciones PRE enviadas")
    
    # Verificar resultados pendientes (POST)
    print("\nVerificando resultados pendientes...")
    post_count = check_post_events(events)
    print(f"  → {post_count} notificaciones POST enviadas")
    
    # Mostrar pendientes
    pending = load_json_file(RESULTS_FILE)
    if pending:
        print(f"\n📋 Eventos pendientes de resultado: {len(pending)}")
        for pid, pdata in pending.items():
            print(f"  - {pdata.get('event', pid)[:40]}")
    
    print("\n✓ Proceso completado")


if __name__ == "__main__":
    main()
