"""
Economic Calendar Alert System
Consulta eventos de alta importancia y envía alertas por WhatsApp via Twilio
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import os
import json

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN - Editar estos valores
# ═══════════════════════════════════════════════════════════════════════════

# Twilio (obtener de https://console.twilio.com)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'tu_account_sid')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'tu_auth_token')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')  # Número Twilio Sandbox

# Números de WhatsApp destino (incluir código país)
WHATSAPP_RECIPIENTS = os.environ.get('WHATSAPP_RECIPIENTS', 'whatsapp:+56912345678').split(',')

# Divisas a monitorear (relacionadas con tus instrumentos)
CURRENCIES_TO_MONITOR = ['USD']

# Minutos antes del evento para alertar
ALERT_MINUTES_BEFORE = 30

# Timezone
TIMEZONE = 'America/Santiago'

# ═══════════════════════════════════════════════════════════════════════════
# SCRAPER DE FOREX FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def get_forex_factory_events():
    """Obtiene eventos de alta importancia de Forex Factory"""
    
    url = "https://www.forexfactory.com/calendar"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        current_date = None
        
        # Buscar filas del calendario
        rows = soup.select('tr.calendar__row')
        
        for row in rows:
            # Obtener fecha si existe en esta fila
            date_cell = row.select_one('td.calendar__date')
            if date_cell and date_cell.get_text(strip=True):
                date_text = date_cell.get_text(strip=True)
                current_date = parse_ff_date(date_text)
            
            # Verificar si es evento de alto impacto
            impact = row.select_one('td.calendar__impact span')
            if not impact:
                continue
                
            impact_class = impact.get('class', [])
            is_high_impact = any('high' in c.lower() for c in impact_class)
            
            if not is_high_impact:
                continue
            
            # Obtener divisa
            currency_cell = row.select_one('td.calendar__currency')
            currency = currency_cell.get_text(strip=True) if currency_cell else ''
            
            if currency not in CURRENCIES_TO_MONITOR:
                continue
            
            # Obtener hora
            time_cell = row.select_one('td.calendar__time')
            time_text = time_cell.get_text(strip=True) if time_cell else ''
            
            # Obtener nombre del evento
            event_cell = row.select_one('td.calendar__event')
            event_name = event_cell.get_text(strip=True) if event_cell else ''
            
            # Obtener forecast y previous
            forecast_cell = row.select_one('td.calendar__forecast')
            forecast = forecast_cell.get_text(strip=True) if forecast_cell else ''
            
            previous_cell = row.select_one('td.calendar__previous')
            previous = previous_cell.get_text(strip=True) if previous_cell else ''
            
            if current_date and time_text and event_name:
                event_datetime = parse_ff_datetime(current_date, time_text)
                if event_datetime:
                    events.append({
                        'datetime': event_datetime,
                        'currency': currency,
                        'event': event_name,
                        'impact': 'HIGH',
                        'forecast': forecast,
                        'previous': previous
                    })
        
        return events
        
    except Exception as e:
        print(f"Error obteniendo calendario: {e}")
        return []


def parse_ff_date(date_text):
    """Parsea fecha de Forex Factory (ej: 'Mon Jan 13')"""
    try:
        current_year = datetime.now().year
        # Agregar año actual
        date_with_year = f"{date_text} {current_year}"
        return datetime.strptime(date_with_year, "%a %b %d %Y").date()
    except:
        return None


def parse_ff_datetime(date_obj, time_text):
    """Combina fecha y hora de Forex Factory"""
    try:
        if not time_text or time_text in ['', 'All Day', 'Tentative']:
            return None
        
        # Limpiar tiempo (puede ser "8:30am" o "8:30pm")
        time_text = time_text.lower().strip()
        
        # Parsear hora (Forex Factory usa ET)
        if 'am' in time_text or 'pm' in time_text:
            time_obj = datetime.strptime(time_text, "%I:%M%p").time()
        else:
            time_obj = datetime.strptime(time_text, "%H:%M").time()
        
        # Combinar fecha y hora
        dt = datetime.combine(date_obj, time_obj)
        
        # Forex Factory usa Eastern Time
        et_tz = pytz.timezone('America/New_York')
        dt_et = et_tz.localize(dt)
        
        # Convertir a UTC para comparaciones
        return dt_et.astimezone(pytz.UTC)
        
    except Exception as e:
        print(f"Error parseando hora '{time_text}': {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# ALTERNATIVA: INVESTING.COM API (más confiable)
# ═══════════════════════════════════════════════════════════════════════════

def get_investing_events():
    """Obtiene eventos de Investing.com via su API interna"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    # Filtrar por países principales
    country_ids = {
        'USD': 5,    # Estados Unidos
        'EUR': 72,   # Eurozona
        'GBP': 4,    # Reino Unido
        'JPY': 35,   # Japón
        'CHF': 12,   # Suiza
        'AUD': 25,   # Australia
        'CAD': 6,    # Canadá
        'NZD': 43,   # Nueva Zelanda
    }
    
    data = {
        'dateFrom': today,
        'dateTo': tomorrow,
        'country[]': [str(v) for v in country_ids.values()],
        'importance[]': ['3'],  # Solo alta importancia
        'timeZone': '8',  # UTC
        'timeFilter': 'timeRemain',
        'currentTab': 'custom',
        'limit_from': '0'
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=30)
        result = response.json()
        
        events = []
        if 'data' in result:
            soup = BeautifulSoup(result['data'], 'html.parser')
            rows = soup.select('tr.js-event-item')
            
            for row in rows:
                # Solo eventos de 3 toros (alta importancia)
                bulls = row.select('td.sentiment i.grayFullBullishIcon')
                if len(bulls) < 3:
                    continue
                
                # Obtener datos
                time_attr = row.get('data-event-datetime', '')
                currency = row.select_one('td.flagCur')
                event_name = row.select_one('td.event')
                
                if time_attr and currency and event_name:
                    dt = datetime.strptime(time_attr, '%Y/%m/%d %H:%M:%S')
                    dt = pytz.UTC.localize(dt)
                    
                    events.append({
                        'datetime': dt,
                        'currency': currency.get_text(strip=True),
                        'event': event_name.get_text(strip=True),
                        'impact': 'HIGH',
                        'forecast': '',
                        'previous': ''
                    })
        
        return events
        
    except Exception as e:
        print(f"Error obteniendo Investing.com: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════
# ENVÍO DE WHATSAPP VIA TWILIO
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


def format_event_message(event):
    """Formatea el mensaje del evento"""
    
    local_tz = pytz.timezone(TIMEZONE)
    local_time = event['datetime'].astimezone(local_tz)
    
    message = f"""
🔴 *EVENTO ALTO IMPACTO*

📅 {local_time.strftime('%d/%m/%Y')}
⏰ {local_time.strftime('%H:%M')} (Chile)
💱 {event['currency']}
📊 {event['event']}

⚠️ Considerar cerrar/reducir posiciones
"""
    
    if event.get('forecast'):
        message += f"\n📈 Forecast: {event['forecast']}"
    if event.get('previous'):
        message += f"\n📉 Previous: {event['previous']}"
    
    return message.strip()


# ═══════════════════════════════════════════════════════════════════════════
# LÓGICA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

def get_upcoming_events():
    """Obtiene eventos próximos que requieren alerta"""
    
    now = datetime.now(pytz.UTC)
    alert_window_start = now
    alert_window_end = now + timedelta(minutes=ALERT_MINUTES_BEFORE + 5)
    
    # Intentar Forex Factory primero, luego Investing.com
    events = get_forex_factory_events()
    if not events:
        print("Forex Factory sin resultados, intentando Investing.com...")
        events = get_investing_events()
    
    # Filtrar eventos dentro de la ventana de alerta
    upcoming = []
    for event in events:
        if event['datetime'] and alert_window_start <= event['datetime'] <= alert_window_end:
            upcoming.append(event)
    
    return upcoming


# Archivo para trackear eventos ya notificados (evitar duplicados)
NOTIFIED_FILE = '/tmp/notified_events.json'

def load_notified_events():
    """Carga eventos ya notificados"""
    try:
        with open(NOTIFIED_FILE, 'r') as f:
            data = json.load(f)
            # Limpiar eventos viejos (más de 24 horas)
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
            return {k: v for k, v in data.items() if v > cutoff}
    except:
        return {}


def save_notified_event(event_id):
    """Guarda evento como notificado"""
    notified = load_notified_events()
    notified[event_id] = datetime.now().isoformat()
    with open(NOTIFIED_FILE, 'w') as f:
        json.dump(notified, f)


def get_event_id(event):
    """Genera ID único para un evento"""
    return f"{event['datetime'].isoformat()}_{event['currency']}_{event['event'][:20]}"


def main():
    """Función principal"""
    
    print(f"\n{'='*50}")
    print(f"Economic Calendar Alert - {datetime.now()}")
    print(f"{'='*50}\n")
    
    # Obtener eventos próximos
    events = get_upcoming_events()
    
    if not events:
        print("No hay eventos de alto impacto próximos.")
        return
    
    print(f"Encontrados {len(events)} eventos próximos de alto impacto")
    
    # Cargar eventos ya notificados
    notified = load_notified_events()
    
    # Enviar alertas para eventos no notificados
    for event in events:
        event_id = get_event_id(event)
        
        if event_id in notified:
            print(f"Evento ya notificado: {event['event']}")
            continue
        
        print(f"\nEnviando alerta: {event['event']}")
        message = format_event_message(event)
        send_whatsapp(message)
        save_notified_event(event_id)
    
    print("\n✓ Proceso completado")


if __name__ == "__main__":
    main()
