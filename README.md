# 📊 Economic Calendar Alert System

Sistema automático que consulta eventos económicos de alto impacto y envía alertas por WhatsApp.

---

## 🚀 PASO 1: Configurar Twilio (WhatsApp)

### 1.1 Crear cuenta Twilio
1. Ve a https://www.twilio.com/try-twilio
2. Crea cuenta gratuita (te dan ~$15 de crédito)
3. Verifica tu número de teléfono

### 1.2 Activar WhatsApp Sandbox
1. En la consola Twilio, ve a: **Messaging → Try it out → Send a WhatsApp message**
2. Twilio te mostrará un número (ej: `+14155238886`) y un código (ej: `join example-word`)
3. Desde tu teléfono, envía ese código al número de Twilio por WhatsApp
4. Recibirás confirmación de que estás conectado al Sandbox

### 1.3 Obtener credenciales
En la consola Twilio (https://console.twilio.com), copia:
- **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Auth Token**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **WhatsApp From**: `whatsapp:+14155238886` (el número del sandbox)

### 1.4 Agregar más números al grupo
Cada persona que quiera recibir alertas debe:
1. Enviar el código de join al número Twilio por WhatsApp
2. Esperar confirmación

---

## 🚀 PASO 2: Deploy en Railway (Gratis)

### 2.1 Crear cuenta Railway
1. Ve a https://railway.app
2. Haz login con GitHub

### 2.2 Crear proyecto
1. Click en **"New Project"**
2. Selecciona **"Deploy from GitHub repo"**
3. Si no tienes el código en GitHub:
   - Click en **"Empty Project"**
   - Luego **"Add Service" → "GitHub Repo"**
   
### 2.3 Subir código a GitHub (si no lo tienes)
```bash
# En tu computador
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/economic-alerts.git
git push -u origin main
```

### 2.4 Configurar variables de entorno
En Railway, ve a tu servicio → **Variables** y agrega:

| Variable | Valor |
|----------|-------|
| `TWILIO_ACCOUNT_SID` | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` |
| `WHATSAPP_RECIPIENTS` | `whatsapp:+56912345678,whatsapp:+56987654321` |

**Nota:** Para múltiples destinatarios, sepáralos con comas.

### 2.5 Verificar Cron Job
El archivo `railway.json` ya configura ejecución cada 5 minutos:
```json
"cronSchedule": "*/5 * * * *"
```

Si quieres cambiar la frecuencia:
- `*/5 * * * *` = cada 5 minutos
- `*/10 * * * *` = cada 10 minutos
- `*/15 * * * *` = cada 15 minutos

---

## ⚙️ CONFIGURACIÓN ADICIONAL

### Modificar divisas monitoreadas
En `main.py`, edita la lista:
```python
CURRENCIES_TO_MONITOR = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']
```

Para solo USD (oro/XAUUSD):
```python
CURRENCIES_TO_MONITOR = ['USD']
```

### Cambiar tiempo de alerta anticipada
```python
ALERT_MINUTES_BEFORE = 30  # Alertar 30 minutos antes
```

### Cambiar timezone
```python
TIMEZONE = 'America/Santiago'  # Chile
```

---

## 💰 COSTOS

### Twilio
- Cuenta nueva: ~$15 crédito gratis
- Costo por mensaje WhatsApp: ~$0.005 USD
- ~3000 mensajes con crédito gratis

### Railway
- Plan gratuito: 500 horas/mes
- Cron job cada 5 min = ~720 ejecuciones/mes
- Cada ejecución ~30 segundos = ~6 horas/mes
- **Gratis para este uso**

---

## 🧪 PROBAR LOCALMENTE

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables (Linux/Mac)
export TWILIO_ACCOUNT_SID="ACxxx..."
export TWILIO_AUTH_TOKEN="xxx..."
export TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"
export WHATSAPP_RECIPIENTS="whatsapp:+56912345678"

# Ejecutar
python main.py
```

---

## 📱 EJEMPLO DE MENSAJE

```
🔴 *EVENTO ALTO IMPACTO*

📅 13/01/2026
⏰ 10:30 (Chile)
💱 USD
📊 Non-Farm Payrolls

⚠️ Considerar cerrar/reducir posiciones

📈 Forecast: 180K
📉 Previous: 227K
```

---

## ❓ TROUBLESHOOTING

### No recibo mensajes
1. Verifica que enviaste el código de join a Twilio
2. Revisa logs en Railway → tu servicio → **Deployments → View Logs**
3. Verifica que las credenciales están correctas

### Error de scraping
Si Forex Factory bloquea, el sistema automáticamente intenta con Investing.com.

### Mensajes duplicados
El sistema guarda eventos ya notificados en `/tmp/notified_events.json` para evitar duplicados.

---

## 🔄 ACTUALIZACIÓN A PRODUCCIÓN

Para WhatsApp en producción (sin sandbox):
1. Solicita acceso a WhatsApp Business API en Twilio
2. Registra un número dedicado
3. Actualiza `TWILIO_WHATSAPP_FROM` con tu número aprobado

Esto elimina el requisito de que cada usuario envíe el código de join.
