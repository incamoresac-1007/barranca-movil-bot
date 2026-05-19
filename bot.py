import os
import json
import time
import asyncio
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

WHATSAPP_TOKEN    = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID   = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN      = os.getenv("VERIFY_TOKEN", "barranca_movil_2025")
GOOGLE_MAPS_KEY   = os.getenv("GOOGLE_MAPS_KEY")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
GRUPO_CONDUCTORES = os.getenv("GRUPO_CONDUCTORES", "")
OPERADOR_WA       = os.getenv("OPERADOR_WA", "")
MINUTOS_CALIFICAR = int(os.getenv("MINUTOS_CALIFICAR", "30"))
META_APP_ID       = os.getenv("META_APP_ID", "")
META_APP_SECRET   = os.getenv("META_APP_SECRET", "")

groq_client = Groq(api_key=GROQ_API_KEY)

# ── Renovador automático de token ────────────────────────────────────────────
async def renovar_token():
    """Renueva el token de WhatsApp cada 23 horas automáticamente."""
    global WHATSAPP_TOKEN
    while True:
        await asyncio.sleep(23 * 3600)  # esperar 23 horas
        try:
            url = f"https://graph.facebook.com/oauth/access_token"
            params = {
                "grant_type": "client_credentials",
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET
            }
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url, params=params)
                data = r.json()
                nuevo_token = data.get("access_token", "")
                if nuevo_token:
                    WHATSAPP_TOKEN = nuevo_token
                    print(f"[TOKEN] Renovado automaticamente OK", flush=True)
                else:
                    print(f"[TOKEN] Error al renovar: {data}", flush=True)
        except Exception as e:
            print(f"[TOKEN ERROR] {e}", flush=True)

async def limpiar_sesiones():
    """Limpia sesiones inactivas cada hora."""
    while True:
        await asyncio.sleep(3600)  # cada 1 hora
        ahora = time.time()
        numeros_limpiar = []

        # Limpiar sesiones inactivas por más de 24 horas
        for numero, ts in list(ultima_actividad.items()):
            horas_inactivo = (ahora - ts) / 3600
            if horas_inactivo > 24:
                numeros_limpiar.append(numero)

        for numero in numeros_limpiar:
            sesiones.pop(numero, None)
            historial_ia.pop(numero, None)
            ultima_actividad.pop(numero, None)
            calificacion_pendiente.discard(numero)

        # Limpiar historial de viajes mayor a 30 días
        for numero in list(historial_viajes.keys()):
            viajes = historial_viajes[numero]
            viajes_recientes = []
            for v in viajes:
                try:
                    from datetime import datetime
                    fecha = datetime.strptime(v["fecha"], "%d/%m/%Y %H:%M")
                    dias = (datetime.now() - fecha).days
                    if dias <= 30:
                        viajes_recientes.append(v)
                except:
                    viajes_recientes.append(v)
            historial_viajes[numero] = viajes_recientes

        if numeros_limpiar:
            print(f"[CLEAN] {len(numeros_limpiar)} sesiones limpiadas", flush=True)

@app.on_event("startup")
async def startup():
    asyncio.create_task(renovar_token())
    asyncio.create_task(limpiar_sesiones())
    print("[BOT] Renovador de token iniciado - renueva cada 23h", flush=True)
    print("[BOT] Limpiador de sesiones iniciado - cada 1h", flush=True)

# ── Navegación ───────────────────────────────────────────────────────────────
NAV = "\n\n_(✍️ *0* = paso anterior  ·  *menu* = inicio)_"

# ── Estados ───────────────────────────────────────────────────────────────────
S_MENU               = "MENU"
S_NOMBRE             = "NOMBRE"
S_RECOJO             = "RECOJO"
S_DESTINO            = "DESTINO"
S_PAGO               = "PAGO"
S_CONFIRMAR          = "CONFIRMAR"
S_ENCOMIENDA_DESC      = "ENCOMIENDA_DESC"
S_ENCOMIENDA_BULTOS    = "ENCOMIENDA_BULTOS"
S_ENCOMIENDA_TAMANO    = "ENCOMIENDA_TAMANO"
S_ENCOMIENDA_FOTO      = "ENCOMIENDA_FOTO"
S_ENCOMIENDA_URGENCIA  = "ENCOMIENDA_URGENCIA"
S_ENCOMIENDA_PROGRAMAR = "ENCOMIENDA_PROGRAMAR"
S_ENCOMIENDA_ORIGEN    = "ENCOMIENDA_ORIGEN"
S_ENCOMIENDA_DESTINO   = "ENCOMIENDA_DESTINO"
S_ENCOMIENDA_CONFIRM_DEST = "ENCOMIENDA_CONFIRM_DEST"
S_ENCOMIENDA_DESTINATARIO = "ENCOMIENDA_DESTINATARIO"
S_ENCOMIENDA_PAGO      = "ENCOMIENDA_PAGO"
S_ENCOMIENDA_CONFIRMAR = "ENCOMIENDA_CONFIRMAR"
S_TURISMO_DESTINO    = "TURISMO_DESTINO"
S_TURISMO_CARAL      = "TURISMO_CARAL"
S_TURISMO_MODALIDAD  = "TURISMO_MODALIDAD"
S_TURISMO_PERSONAS   = "TURISMO_PERSONAS"
S_TURISMO_TIPO_GRUPO = "TURISMO_TIPO_GRUPO"
S_TURISMO_CUANDO     = "TURISMO_CUANDO"
S_TURISMO_FECHA_PROG = "TURISMO_FECHA_PROG"
S_TURISMO_RECOJO     = "TURISMO_RECOJO"
S_TURISMO_PAGO       = "TURISMO_PAGO"
S_TURISMO_PASAJEROS  = "TURISMO_PASAJEROS"  # Datos DNI pasajeros
S_TURISMO_CONFIRMAR  = "TURISMO_CONFIRMAR"
S_CONSULTA_OPCION    = "CONSULTA_OPCION"
S_CALIFICAR          = "CALIFICAR"
S_CALIFICAR_COMMENT  = "CALIFICAR_COMMENT"
S_RECLAMO            = "RECLAMO"      # Reclamo/sugerencia del cliente
S_RECLAMO_TIPO       = "RECLAMO_TIPO" # Tipo de reclamo
S_CUANDO             = "CUANDO"            # ¿Cuándo necesitas el taxi?
S_COLECTIVO_RUTA     = "COLECTIVO_RUTA"     # Ruta del colectivo
S_COLECTIVO_HORARIO  = "COLECTIVO_HORARIO"  # Horario de salida
S_COLECTIVO_ASIENTOS = "COLECTIVO_ASIENTOS" # Cuántos asientos
S_COLECTIVO_RECOJO   = "COLECTIVO_RECOJO"   # Punto de recojo
S_COLECTIVO_PAGO     = "COLECTIVO_PAGO"     # Método de pago
S_COLECTIVO_CONFIRMAR= "COLECTIVO_CONFIRMAR"# Confirmación
S_CONFIRM_RECOJO     = "CONFIRM_RECOJO"    # Confirmar dirección de recojo
S_CONFIRM_DESTINO    = "CONFIRM_DESTINO"   # Confirmar dirección de destino
S_CONFIRM_COL_RECOJO = "CONFIRM_COL_RECOJO" # Confirmar recojo colectivo
S_PROGRAMAR          = "PROGRAMAR"         # Fecha y hora programada
S_RECURRENTE_DIAS    = "RECURRENTE_DIAS"   # Días de la semana
S_RECURRENTE_HORA    = "RECURRENTE_HORA"   # Hora del viaje recurrente

# ── Mapa estado → estado anterior ────────────────────────────────────────────
ESTADO_ANTERIOR = {
    S_NOMBRE:               S_MENU,
    S_RECOJO:               S_NOMBRE,
    S_CONFIRM_RECOJO:       S_RECOJO,
    S_DESTINO:              S_RECOJO,
    S_CONFIRM_DESTINO:      S_DESTINO,
    S_CUANDO:               S_DESTINO,
    S_PROGRAMAR:            S_CUANDO,
    S_RECURRENTE_DIAS:      S_CUANDO,
    S_RECURRENTE_HORA:      S_RECURRENTE_DIAS,
    S_PAGO:                 S_CUANDO,
    S_CONFIRMAR:            S_PAGO,
    S_COLECTIVO_RUTA:       S_MENU,
    S_COLECTIVO_HORARIO:    S_COLECTIVO_RUTA,
    "COLECTIVO_HORA_LIBRE": S_COLECTIVO_HORARIO,
    S_COLECTIVO_ASIENTOS:   S_COLECTIVO_HORARIO,
    S_COLECTIVO_RECOJO:     S_COLECTIVO_ASIENTOS,
    S_CONFIRM_COL_RECOJO:   S_COLECTIVO_RECOJO,
    S_COLECTIVO_PAGO:       S_COLECTIVO_RECOJO,
    S_COLECTIVO_CONFIRMAR:  S_COLECTIVO_PAGO,
    S_ENCOMIENDA_DESC:      S_MENU,
    S_ENCOMIENDA_BULTOS:    S_ENCOMIENDA_DESC,
    S_ENCOMIENDA_TAMANO:    S_ENCOMIENDA_BULTOS,
    S_ENCOMIENDA_FOTO:      S_ENCOMIENDA_TAMANO,
    S_ENCOMIENDA_URGENCIA:  S_ENCOMIENDA_FOTO,
    S_ENCOMIENDA_PROGRAMAR: S_ENCOMIENDA_URGENCIA,
    S_ENCOMIENDA_ORIGEN:    S_ENCOMIENDA_URGENCIA,
    S_ENCOMIENDA_DESTINO:   S_ENCOMIENDA_ORIGEN,
    S_ENCOMIENDA_CONFIRM_DEST: S_ENCOMIENDA_DESTINO,
    S_ENCOMIENDA_DESTINATARIO: S_ENCOMIENDA_DESTINO,
    S_ENCOMIENDA_PAGO:      S_ENCOMIENDA_DESTINATARIO,
    S_ENCOMIENDA_CONFIRMAR: S_ENCOMIENDA_PAGO,
    S_TURISMO_DESTINO:      S_MENU,
    S_TURISMO_CARAL:        S_TURISMO_DESTINO,
    S_TURISMO_MODALIDAD:    S_TURISMO_DESTINO,
    S_TURISMO_PERSONAS:     S_TURISMO_MODALIDAD,
    S_TURISMO_TIPO_GRUPO:   S_TURISMO_PERSONAS,
    S_TURISMO_CUANDO:       S_TURISMO_TIPO_GRUPO,
    S_TURISMO_FECHA_PROG:   S_TURISMO_CUANDO,
    S_TURISMO_RECOJO:       S_TURISMO_CUANDO,
    S_TURISMO_PAGO:         S_TURISMO_RECOJO,
    S_TURISMO_PASAJEROS:    S_TURISMO_PAGO,
    S_TURISMO_CONFIRMAR:    S_TURISMO_PASAJEROS,
}

# ── Prompt a reenviar cuando el usuario regresa ───────────────────────────────
PROMPT_VOLVER = {
    S_MENU:               None,  # se muestra MSG_BIENVENIDA
    S_NOMBRE:             "👤 *¿Cuál es tu nombre?*",
    S_RECOJO:             "📍 *¿Desde dónde te recogemos?*\n• Comparte tu ubicación 📌\n• O escribe tu dirección",
    S_DESTINO:            "🏁 *¿A dónde vas?*\n• Comparte la ubicación del destino 📌\n• O escribe el destino",
    S_CUANDO:             "🕐 *¿Cuándo necesitas el taxi?*\n1️⃣ Ahora mismo\n2️⃣ En menos de 1 hora\n3️⃣ Programar\n4️⃣ Recurrente",
    S_PAGO:               "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape",
    S_COLECTIVO_RUTA:     "🚌 *¿A qué destino?*\n1️⃣ Pativilca  2️⃣ Paramonga  3️⃣ Puerto Supe\n4️⃣ Supe Pueblo  5️⃣ San Nicolás  6️⃣ Huacho  7️⃣ Lima",
    S_COLECTIVO_HORARIO:  "🕐 *¿Cuándo necesitas el colectivo?*\n1️⃣ Ahora mismo\n2️⃣ Indicar hora",
    S_COLECTIVO_ASIENTOS: "👥 *¿Cuántos asientos necesitas?* (máx. 4)\n1️⃣  2️⃣  3️⃣  4️⃣",
    S_COLECTIVO_RECOJO:   "📍 *¿Desde dónde te recogemos?*\n• Comparte tu ubicación 📌\n• O escribe tu dirección",
    S_COLECTIVO_PAGO:     "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape",
    S_ENCOMIENDA_DESC:    "📦 *¿Qué vas a enviar?*\n_(Describe brevemente el contenido)_",
    S_ENCOMIENDA_BULTOS:  "🔢 *¿Cuántos paquetes son?*\n_(Escribe el número)_",
    S_ENCOMIENDA_TAMANO:  "📐 *¿Cuál es el tamaño del paquete más grande?*\n1️⃣ Sobre/Documento\n2️⃣ Paquete pequeño\n3️⃣ Paquete mediano\n4️⃣ Paquete grande\n5️⃣ Carga pesada",
    S_ENCOMIENDA_FOTO:    "📸 *Envía una foto de tu encomienda*\nO escribe *omitir*",
    S_ENCOMIENDA_URGENCIA:"⏰ *¿Cuándo necesitas que llegue?*\n1️⃣ Urgente 🚀\n2️⃣ Hoy en el día\n3️⃣ Programar",
    S_ENCOMIENDA_ORIGEN:  "📍 *¿Desde dónde recogemos la encomienda?*\n• Comparte tu ubicación 📌\n• O escribe la dirección",
    S_ENCOMIENDA_DESTINO: "🏁 *¿A qué dirección la enviamos?*\n• Comparte ubicación del destino 📌\n• O escribe la dirección",
    S_ENCOMIENDA_DESTINATARIO: "👤 *¿Nombre y teléfono de quien recibe?*\n_(Ej: María López / 987654321)_",
    S_ENCOMIENDA_PAGO:    "💳 *¿Quién paga?*\n1️⃣ Yo — Efectivo\n2️⃣ Yo — Yape\n3️⃣ Paga el destinatario al recibir",
    S_TURISMO_DESTINO:    "🗺️ *¿Qué destino turístico te interesa?*\n1️⃣ Fortaleza Paramonga\n2️⃣ Playas de Barranca\n3️⃣ Caral\n4️⃣ Tour Huacho\n5️⃣ Caral + Supe Pueblo\n6️⃣ Destino personalizado",
    S_TURISMO_MODALIDAD:  "🔄 *¿Cómo será el viaje?*\n1️⃣ Solo ida\n2️⃣ Ida y vuelta ✅",
    S_TURISMO_PERSONAS:   "👥 *¿Cuántas personas van?* (máx. 4)\n1️⃣  2️⃣  3️⃣  4️⃣",
    S_TURISMO_TIPO_GRUPO: "👨‍👩‍👧 *¿Tipo de grupo?*\n1️⃣ Familia con niños\n2️⃣ Pareja/adultos\n3️⃣ Adultos mayores\n4️⃣ Amigos/jóvenes",
    S_TURISMO_CUANDO:     "📅 *¿Para cuándo es el tour?*\n1️⃣ Hoy\n2️⃣ Mañana\n3️⃣ Otra fecha",
    S_TURISMO_RECOJO:     "📍 *¿Desde dónde los recogemos?*\n• Comparte tu ubicación 📌\n• O escribe la dirección",
    S_TURISMO_PAGO:       "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape",
    S_TURISMO_PASAJEROS:  "🔒 *Registro de pasajeros*\n¿Cuántos van? Escribe los datos o *omitir*",
}

sesiones: dict[str, dict] = {}
historial_ia: dict[str, list] = {}
calificaciones: list[dict] = []  # historial de ratings
tickets: list[dict] = []          # tickets de reclamos/sugerencias
_ticket_counter: int = 0          # contador de tickets
viajes_programados: list[dict] = []  # viajes agendados
viajes_recurrentes: dict[str, dict] = {}  # viajes recurrentes por número

# ── Conductores registrados ───────────────────────────────────────────────────
CONDUCTORES = {
    "51992995140": {"nombre": "Adriel Urpeque",    "placa": "AYH-643"},
    "51901258690": {"nombre": "Christian Chinchay", "placa": "APS-359"},
    "51900817214": {"nombre": "Carlos Álvarez",     "placa": "AXG-557"},
    "51936882776": {"nombre": "Fernando Urpeque",   "placa": "H3D-309"},
    "51940197110": {"nombre": "Marino Solorzano",    "placa": "BTE-605"},
}

# Servicios pendientes de aceptación {numero_cliente: datos_servicio}
servicios_pendientes: dict[str, dict] = {}
# Servicios ya tomados para evitar doble asignación
servicios_tomados: set[str] = set()
calificacion_pendiente: set[str] = set()  # números con calificación ya programada
historial_viajes: dict[str, list] = {}  # historial de viajes por número
ultima_actividad: dict[str, float] = {}  # timestamp última actividad por número
# Estado conductor: True=activo/disponible, False=pausado
conductores_estado: dict[str, bool] = {k: True for k in ["51992995140","51901258690","51900817214","51936882776","51940197110"]}
# Viajes activos por conductor {num_conductor: num_cliente}
viajes_activos: dict[str, str] = {}
# Tipo de servicio activo por conductor {num_conductor: tipo}
viajes_activos_tipo: dict[str, str] = {}

# ── Tarifas ───────────────────────────────────────────────────────────────────
TARIFAS_FIJAS = {
    "pativilca": 3.50, "paramonga": 5.00, "puerto supe": 3.00,
    "supe": 3.00, "san nicolas": 4.00, "huacho": 10.00,
    "vinto": 5.00, "potao": 5.00, "santa elena": 5.00,
}
TARIFA_BASE_KM = 3.0
TARIFA_POR_KM  = 1.20

# Tarifas colectivo (puerta a puerta, por pasajero)
COLECTIVO_RUTAS = {
    "1": {"nombre": "Pativilca",    "tarifa": 3.00,  "emoji": "🛣️"},
    "2": {"nombre": "Paramonga",    "tarifa": 5.00,  "emoji": "🏛️"},
    "3": {"nombre": "Puerto Supe",  "tarifa": 3.00,  "emoji": "⚓"},
    "4": {"nombre": "Supe Pueblo",  "tarifa": 4.00,  "emoji": "🌊"},
    "5": {"nombre": "San Nicolás",  "tarifa": 5.00,  "emoji": "🏘️"},
    "6": {"nombre": "Huacho",       "tarifa": 10.00, "emoji": "🏙️"},
    "7": {"nombre": "Lima",         "tarifa": 50.00, "emoji": "🏢"},
}
COLECTIVO_RECOJO_EXTRA = 1.00  # +S/1 por recojo a domicilio (puerta a puerta siempre)

# Turismo: margen de negociación permitido (±25% del precio referencial)
TURISMO_MARGEN_MIN = 0.75  # precio mínimo = 75% del referencial
TURISMO_MARGEN_MAX = 1.25  # precio máximo = 125% del referencial
COLECTIVO_HORARIOS = {
    "1": "5:00 am", "2": "6:00 am", "3": "7:00 am",
    "4": "1:00 pm", "5": "6:00 pm"
}
COLECTIVO_MAX_ASIENTOS = 4

SYSTEM_PROMPT_IA = """Eres el asistente de Barranca Móvil, servicio de taxis, encomiendas y turismo en Barranca, Perú.
Servicios: TAXI urbano (S/3+S/1.20/km), interdistrital fijo, ENCOMIENDA local, TURISMO (Paramonga S/35, Caral S/60, Playas S/25, Huacho S/50).
Pago: Efectivo o Yape. Responde en español, amigable, máximo 3 oraciones."""

MSG_BIENVENIDA = """👋 ¡Hola! Soy *Elizabeth*, tu asistente de *Barranca Móvil* 🚖🌊

Estoy aquí para ayudarte con lo que necesites.
¿En qué te puedo ayudar hoy?

1️⃣ Solicitar taxi
2️⃣ Colectivo puerta a puerta 🚌
3️⃣ Envío de encomienda 📦
4️⃣ Ruta turística 🗺️
5️⃣ Ver tarifas
6️⃣ Ayuda
7️⃣ Reclamos y sugerencias 📋
0️⃣ Salir

O escribe tu consulta libremente 💬"""

MSG_TARIFAS = """💰 *Tarifas Barranca Móvil*

🚖 *Taxi Urbano:* S/3.00 + S/1.20/km

🚌 *Colectivo Puerta a Puerta:*
• Pativilca: S/4 | Paramonga: S/6
• Puerto Supe: S/4 | Supe Pueblo: S/5
• San Nicolás: S/6 | Huacho: S/10
• Lima: S/50
✅ *Precio incluye recojo en tu domicilio*
_(2+ asientos: descuento en recojo S/0.50 c/u)_

🛣️ *Taxi Interdistrital:*
• Pativilca: S/3.50 | Paramonga: S/5.00
• Puerto Supe: S/3.00 | San Nicolás: S/4.00
• Huacho: S/10.00 | Vinto/Potao/S.Elena: S/5.00

🗺️ *Turismo (vehículo completo):*
• Fortaleza de Paramonga: S/35
• Playas de Barranca: S/25
• Ciudad de Caral: S/60
• Tour Huacho: S/50

📦 *Encomiendas:* precio según peso y distancia
💳 Pago: Efectivo o Yape

Escribe *menu* para volver."""

MSG_AYUDA = """❓ *Hola, soy Elizabeth — ¿en qué te ayudo?*

• Escribe *menu* para volver al inicio
• *1* Taxi | *2* Colectivo | *3* Encomienda | *4* Turismo
• Escribe *mis viajes* para ver tu historial
• Soporte directo: *+51 983 469 309*

_Estoy aquí para lo que necesites_ 🚖"""

MSG_TURISMO_OPCIONES = """🗺️ *Tours desde Barranca*
_(Precios referenciales, sujetos a negociación)_

1️⃣ 🏛️ Fortaleza de Paramonga
   ⏱️ 3-4h | hasta 4 personas | desde S/70 i+v

2️⃣ 🏖️ Playas de Barranca
   ⏱️ 2-3h | hasta 4 personas | desde S/50 i+v

3️⃣ 🏺 Ciudad Sagrada de Caral
   ⏱️ 5-6h | hasta 4 personas | desde S/120 i+v
   ⚠️ _Río cortado: traslado en moto S/40 extra_

4️⃣ 🏙️ Tour Huacho
   ⏱️ 4-5h | hasta 4 personas | desde S/100 i+v

5️⃣ ⭐ Tour Combinado Caral + Supe Pueblo
   ⏱️ Día completo | hasta 4 personas | desde S/180 i+v
   _(Almuerzo por cuenta del turista)_

6️⃣ 🗺️ Destino personalizado
   _(Precio a coordinar con conductor)_

¿Cuál te interesa?"""

ESTRELLAS = {"1": "⭐", "2": "⭐⭐", "3": "⭐⭐⭐", "4": "⭐⭐⭐⭐", "5": "⭐⭐⭐⭐⭐"}

# ── WhatsApp ──────────────────────────────────────────────────────────────────
async def enviar_mensaje(to: str, texto: str):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": texto}}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
        print(f"[WA] {r.status_code}", flush=True)

async def reenviar_imagen(to: str, media_id: str):
    """Reenvía una imagen recibida a otro número."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"id": media_id, "caption": "📸 Foto de la encomienda"}
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
        print(f"[IMG] {r.status_code}", flush=True)

async def registrar_turismo_sheets(datos_turismo: dict):
    """Registra servicio turismo en Google Sheets via Apps Script webhook."""
    webhook_url = os.getenv("SHEETS_WEBHOOK_URL", "")
    if not webhook_url:
        print("[SHEETS] No configurado SHEETS_WEBHOOK_URL", flush=True)
        return
    try:
        payload = {
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "pasajero_nombre": datos_turismo.get("nombre", ""),
            "pasajero_telefono": datos_turismo.get("telefono", ""),
            "conductor_nombre": datos_turismo.get("conductor_nombre", ""),
            "conductor_placa": datos_turismo.get("conductor_placa", ""),
            "conductor_telefono": datos_turismo.get("conductor_telefono", ""),
            "ruta": datos_turismo.get("ruta_nombre", ""),
            "modalidad": datos_turismo.get("modalidad", ""),
            "personas": datos_turismo.get("personas", ""),
            "tipo_grupo": datos_turismo.get("tipo_grupo", ""),
            "fecha_tour": datos_turismo.get("fecha", ""),
            "recojo": datos_turismo.get("recojo_texto", ""),
            "precio_ref": datos_turismo.get("ruta_precio_ref", ""),
            "precio_final": datos_turismo.get("precio_final", ""),
            "pago": datos_turismo.get("pago", ""),
            "pasajero_dni": datos_turismo.get("turismo_dni_principal", ""),
            "pasajeros_extra": datos_turismo.get("turismo_pasajeros_extra", ""),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(webhook_url, json=payload)
            print(f"[SHEETS] Registro turismo: {r.status_code}", flush=True)
    except Exception as e:
        print(f"[SHEETS ERROR] {e}", flush=True)

# ── Google Maps ───────────────────────────────────────────────────────────────
async def coords_a_direccion(lat, lng) -> str:
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_MAPS_KEY}&language=es"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            data = r.json()
            if data.get("results"):
                direccion = data["results"][0].get("formatted_address", "")
                if direccion:
                    partes = direccion.split(",")
                    return ", ".join(partes[:3]) if len(partes) > 3 else direccion
    except Exception as e:
        print(f"[GEOCODE ERROR] {e}", flush=True)
    return None  # None indica fallo, no devolver coordenadas

# Coordenadas centro de Barranca para bias de búsqueda
BARRANCA_LAT = -10.7511
BARRANCA_LNG = -77.7625
BARRANCA_RADIUS = 15000  # 15km radio

async def buscar_lugares_barranca(texto: str) -> list:
    """Places Autocomplete - busca lugares en Barranca como Waze.
    Retorna lista de {nombre, place_id} max 4 sugerencias."""
    # Agregar "Barranca" si no está en el texto para forzar zona
    query = texto if "barranca" in texto.lower() else f"{texto} Barranca"
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": query,
        "location": f"{BARRANCA_LAT},{BARRANCA_LNG}",
        "radius": 25000,
        "strictbounds": "true",
        "language": "es",
        "key": GOOGLE_MAPS_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
        predictions = data.get("predictions", [])
        resultados = []
        for p in predictions[:6]:  # revisar más para filtrar bien
            nombre = p.get("description", "")
            place_id = p.get("place_id", "")
            if not place_id:
                continue
            # Filtrar resultados que no sean de la zona Barranca
            nombre_lower = nombre.lower()
            # Para recojo: SOLO resultados de Barranca (no Paramonga ni otras ciudades)
            zona_valida = "barranca" in nombre_lower
            if zona_valida:
                resultados.append({"nombre": nombre, "place_id": place_id})
            if len(resultados) == 4:
                break
        print(f"[AUTOCOMPLETE] '{texto}' -> {len(resultados)} resultados", flush=True)
        return resultados
    except Exception as e:
        print(f"[AUTOCOMPLETE ERROR] {e}", flush=True)
        return []

async def coords_de_place_id(place_id: str, nombre_sugerido: str = "") -> tuple:
    """Obtiene coordenadas de un place_id. Usa nombre_sugerido como display (evita Plus Codes)."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "geometry",
        "language": "es",
        "key": GOOGLE_MAPS_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
        result = data.get("result", {})
        loc = result.get("geometry", {}).get("location", {})
        lat = loc.get("lat", BARRANCA_LAT)
        lng = loc.get("lng", BARRANCA_LNG)
        # Usar nombre de la sugerencia (ya es legible), no formatted_address que puede ser Plus Code
        if nombre_sugerido:
            partes = nombre_sugerido.split(",")
            direccion = ", ".join(partes[:2]) if len(partes) > 1 else nombre_sugerido
        else:
            direccion = "Dirección Barranca"
        return direccion, f"{lat},{lng}"
    except Exception as e:
        print(f"[PLACE DETAILS ERROR] {e}", flush=True)
        return nombre_sugerido or "Dirección", f"{BARRANCA_LAT},{BARRANCA_LNG}"

async def buscar_lugares_peru(texto: str) -> list:
    """Places Autocomplete sin restricción de zona - para destinos de encomienda."""
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": texto,
        "location": f"{BARRANCA_LAT},{BARRANCA_LNG}",
        "radius": 500000,  # 500km - todo Peru
        "language": "es",
        "components": "country:PE",
        "key": GOOGLE_MAPS_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
        predictions = data.get("predictions", [])
        resultados = []
        for p in predictions[:4]:
            nombre = p.get("description", "")
            place_id = p.get("place_id", "")
            if place_id:
                resultados.append({"nombre": nombre, "place_id": place_id})
        return resultados
    except Exception as e:
        print(f"[GEO PERU ERROR] {e}", flush=True)
        return []

MSG_NO_ENCONTRADO = ("No encontre esa direccion en Barranca.\n\n"
                     "Intenta con:\n"
                     "Nombre del barrio: _Las Gardenias_\n"
                     "Calle y numero: _Jr. Lima 234_\n"
                     "Lugar conocido: _Plaza de Armas_\n\n"
                     "O comparte tu ubicacion GPS.")

async def resolver_direccion(texto: str, sesion: dict, datos: dict, numero: str,
                              key_temp: str, key_coords: str, estado_confirmar: str,
                              label_confirm: str):
    """Helper: busca con autocomplete tipo Waze.
    1 resultado  → confirmar directo
    2-4 resultados → mostrar lista, usuario elige y va DIRECTO (sin confirmacion extra)
    0 resultados → error"""
    sugerencias = await buscar_lugares_barranca(texto)
    if not sugerencias:
        await enviar_mensaje(numero, MSG_NO_ENCONTRADO)
        return
    if len(sugerencias) == 1:
        # Una sola opcion - confirmar
        sug = sugerencias[0]
        direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
        datos[key_temp] = direccion
        datos[key_coords] = coords
        sesion["estado"] = estado_confirmar
        await enviar_mensaje(numero,
            f"📍 *{direccion}*\n\n"
            f"¿Es correcto?\n"
            f"1️⃣ Sí\n"
            f"2️⃣ No, escribir otra")
    else:
        # Varias opciones - mostrar lista numerada
        numeros = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        opciones_txt = "\n".join([f"{numeros[i]} {s['nombre'].split(',')[0]}" for i, s in enumerate(sugerencias)])
        datos["_sugerencias"] = sugerencias
        await enviar_mensaje(numero,
            f"📍 ¿Cuál de estas?\n\n"
            f"{opciones_txt}\n\n"
            f"_(O escribe otra dirección)_")

async def calcular_distancia_km(origen: str, destino: str) -> float:
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origen,
        "destinations": destino,
        "key": GOOGLE_MAPS_KEY,
        "language": "es",
        "region": "PE",
        "mode": "driving"
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        data = r.json()
        try:
            elemento = data["rows"][0]["elements"][0]
            if elemento.get("status") != "OK":
                return None
            metros = elemento["distance"]["value"]
            km = metros / 1000
            return max(km, 0.5) if km > 0 else None
        except:
            return None  # señal para coordinar con conductor

def calcular_tarifa_taxi(destino_texto: str, km: float) -> tuple[float, str]:
    d = destino_texto.lower()
    for lugar, precio in TARIFAS_FIJAS.items():
        if lugar in d:
            return precio, f"tarifa fija a {lugar.title()}"
    tarifa_exacta = max(TARIFA_BASE_KM + (km * TARIFA_POR_KM), 3.0)
    tarifa_redondeada = round(tarifa_exacta)  # >=0.5 sube (conductor), <0.5 baja (pasajero)
    return float(tarifa_redondeada), f"urbano {km:.1f} km"

# ── Groq IA ───────────────────────────────────────────────────────────────────
async def respuesta_ia(numero: str, texto: str) -> str:
    if numero not in historial_ia:
        historial_ia[numero] = []
    historial_ia[numero].append({"role": "user", "content": texto})
    historial = historial_ia[numero][-8:]
    def _groq():
        return groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT_IA}] + historial,
            max_tokens=250, temperature=0.7
        )
    completion = await asyncio.to_thread(_groq)
    resp = completion.choices[0].message.content
    historial_ia[numero].append({"role": "assistant", "content": resp})
    return resp

# ── Historial de viajes ──────────────────────────────────────────────────────
def guardar_viaje(numero: str, datos: dict, tipo: str):
    """Guarda un viaje en el historial del cliente."""
    if numero not in historial_viajes:
        historial_viajes[numero] = []
    
    from datetime import datetime
    viaje = {
        "tipo": tipo,
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "destino": datos.get("destino_texto") or datos.get("colectivo_ruta") or datos.get("ruta_nombre") or datos.get("destino_texto", "N/A"),
        "tarifa": datos.get("tarifa") or datos.get("colectivo_total", "N/A"),
        "pago": datos.get("pago") or datos.get("colectivo_pago", "N/A"),
    }
    historial_viajes[numero].insert(0, viaje)  # más reciente primero
    historial_viajes[numero] = historial_viajes[numero][:10]  # máx 10 viajes

def formato_historial(numero: str) -> str:
    """Genera el mensaje de historial para el cliente."""
    viajes = historial_viajes.get(numero, [])
    if not viajes:
        return "📋 *Mis viajes*\n\nAún no tienes viajes registrados.\n\nEscribe *menu* para solicitar uno."
    
    emojis = {"taxi": "🚖", "colectivo": "🚌", "encomienda": "📦", "turismo": "🗺️"}
    msg = "📋 *Mis últimos viajes:*\n\n"
    for i, v in enumerate(viajes[:5], 1):
        emoji = emojis.get(v.get("tipo", "taxi"), "🚖")
        tarifa_str = f"S/{v['tarifa']}" if v.get('tarifa') and v['tarifa'] != "N/A" else "A coordinar"
        tipo_str = v.get('tipo', 'taxi').title()
        destino_str = v.get('destino', 'N/A')
        fecha_str = v.get('fecha', 'N/A')
        msg += f"{i}. {emoji} *{tipo_str}*\n"
        msg += f"   📅 {fecha_str}\n"
        msg += f"   🏁 {destino_str}\n"
        msg += f"   💰 {tarifa_str}\n\n"

    msg += "_Escribe *menu* para solicitar otro servicio._"
    return msg

async def _turismo_pago(numero: str, datos: dict):
    """Helper: muestra opciones de pago para turismo."""
    await enviar_mensaje(numero,
        f"✅ Recojo: *{datos['recojo_texto']}*\n\n"
        "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)

# ── Notificaciones ────────────────────────────────────────────────────────────
async def notificar_operador_consulta(numero: str, consulta: str, respuesta: str):
    if not OPERADOR_WA:
        return
    msg = (f"💬 *CONSULTA DIRECTA*\n\n📱 +{numero}\n"
           f"❓ _{consulta}_\n🤖 _{respuesta[:100]}..._\n\nResponde directo a ese número.")
    await enviar_mensaje(OPERADOR_WA, msg)


# ── Videos turísticos por destino ────────────────────────────────────────────
VIDEOS_TURISMO = {
    "1": ("🏛️ *Fortaleza de Paramonga*", "https://youtu.be/u-qZL_JLbrg"),
    "2": ("🏖️ *Playas de Barranca*",     "https://youtu.be/ITQs3FS8eyk"),
    "3": ("🏺 *Ciudad Sagrada de Caral*", "https://youtu.be/x5FeHWC2E7M"),
    "4": ("🏙️ *Tour Huacho*",            "https://youtu.be/OLMzW0jU0_g"),
    "5": ("⭐ *Caral + Supe Pueblo*",     "https://youtu.be/fdE0wCsDOrc"),
    "6": None,  # destino personalizado, sin video
}
async def notificar_conductores(sesion: dict, numero_cliente: str, tipo: str = "TAXI"):
    """Envía solicitud a todos los conductores individualmente.
    El primero en responder ACEPTO se lleva el servicio."""
    d = sesion["datos"]

    if tipo == "TAXI":
        cuando = d.get("cuando", "ahora")
        if cuando == "programado":
            linea_t = f"📅 {d.get('fecha_programada', '')}\n"
        elif cuando == "recurrente":
            linea_t = f"🔄 {d.get('dias_recurrente','')} a las {d.get('hora_recurrente','')}\n"
        elif cuando == "menos de 1 hora":
            linea_t = "🕐 En menos de 1 hora\n"
        else:
            linea_t = "⚡ AHORA\n"
        tarifa_txt = f"S/{d.get('tarifa')}" if d.get('tarifa') != 'a coordinar' else "A coordinar"
        msg = (f"🚨 *NUEVO TAXI*\n\n"
               f"👤 {d.get('nombre')} | 📱 +{numero_cliente}\n"
               f"{linea_t}"
               f"📍 {d.get('recojo_texto')}\n"
               f"🏁 {d.get('destino_texto')}\n"
               f"💰 {tarifa_txt} | 💳 {d.get('pago')}\n\n"
               f"Responde: *ACEPTO {numero_cliente}*")
    elif tipo == "ENCOMIENDA":
        tarifa_txt = f"S/{d.get('enc_tarifa_final')}" if d.get("enc_tarifa_final") else "A coordinar"
        foto_txt = "✅ El cliente envió foto" if d.get("enc_foto") else "Sin foto"
        contra_entrega = " ⚠️ *COBRAR AL ENTREGAR*" if d.get("pago") == "Contra entrega 🚪" else ""
        msg = (f"📦 *NUEVA ENCOMIENDA*\n\n"
               f"👤 Remitente: {d.get('nombre')} | 📱 +{numero_cliente}\n"
               f"📦 {d.get('enc_descripcion')} — {d.get('enc_tamano')}\n"
               f"🔢 {d.get('enc_paquetes', 1)} paquete(s) | 📸 {foto_txt}\n"
               f"⏰ {d.get('enc_urgencia')}\n"
               f"📍 Recojo: {d.get('enc_origen')}\n"
               f"🏁 Destino: {d.get('enc_destino')}\n"
               f"👤 Destinatario: {d.get('enc_destinatario')}\n"
               f"💰 {tarifa_txt} | 💳 {d.get('pago')}{contra_entrega}\n\n"
               f"Responde: *ACEPTO {numero_cliente}*")
    elif tipo == "COLECTIVO":
        msg = (f"🚌 *NUEVO COLECTIVO*\n\n"
               f"👤 {d.get('nombre')} | 📱 +{numero_cliente}\n"
               f"{d.get('colectivo_emoji','')} {d.get('colectivo_ruta')}\n"
               f"🕐 {d.get('colectivo_horario')}\n"
               f"👥 {d.get('colectivo_asientos')} asiento(s) confirmados\n"
               f"📍 Recojo: {d.get('colectivo_recojo')}\n"
               f"💰 S/{d.get('colectivo_total')} | 💳 {d.get('colectivo_pago')}\n\n"
               f"💡 Puedes completar el cupo en el paradero\n\n"
               f"Responde: *ACEPTO {numero_cliente}*")
    elif tipo == "TURISMO":
        precio_ref = d.get("ruta_precio_ref", "a coordinar")
        precio_txt = f"S/{precio_ref} referencial" if precio_ref else "A coordinar"
        nota_caral = "\n⚠️ Río cortado — llevar por pueblo" if d.get("ruta_nota") == "caral" else ""
        msg = (f"🗺️ *NUEVO TOUR*\n\n"
               f"👤 {d.get('nombre')} | 📱 +{numero_cliente}\n"
               f"{d.get('ruta_emoji','')} {d.get('ruta_nombre')}\n"
               f"🔄 {d.get('modalidad','Ida y vuelta')} | ⏱️ {d.get('ruta_duracion','')}\n"
               f"👥 {d.get('personas')} persona(s) — {d.get('tipo_grupo','')}\n"
               f"🪪 DNI: {d.get('turismo_dni_principal','—')}"
               + (f" | Otros: {d.get('turismo_pasajeros_extra','')}\n" if d.get('turismo_pasajeros_extra') else "\n")
               + f"📅 {d.get('fecha')} | 📍 {d.get('recojo_texto','')}\n"
               f"💰 {precio_txt} | 💳 {d.get('pago')}{nota_caral}\n\n"
               f"💬 *Contacta al cliente para confirmar precio final*\n\n"
               f"Responde: *ACEPTO {numero_cliente}*")
    else:
        return

    # Guardar servicio como pendiente
    servicios_pendientes[numero_cliente] = {
        "tipo": tipo,
        "datos": d.copy(),
        "conductores_notificados": list(CONDUCTORES.keys())
    }

    # Enviar solo a conductores ACTIVOS (no pausados)
    conductores_disponibles = [n for n in CONDUCTORES.keys() if conductores_estado.get(n, True)]
    if not conductores_disponibles:
        await enviar_mensaje(numero_cliente,
            "😔 No hay conductores disponibles ahora.\n\nIntenta en unos minutos o escribe *menu*.")
        servicios_pendientes.pop(numero_cliente, None)
        return

    # Envío PARALELO a todos los conductores (asyncio.gather = mucho más rápido)
    tareas = [enviar_mensaje(num_conductor, msg) for num_conductor in conductores_disponibles]
    if GRUPO_CONDUCTORES:
        tareas.append(enviar_mensaje(GRUPO_CONDUCTORES, msg))
    await asyncio.gather(*tareas)

    # Timeout 90s: si nadie acepta, avisar al cliente
    async def timeout_sin_conductor():
        await asyncio.sleep(180)
        if numero_cliente in servicios_pendientes:
            servicios_pendientes.pop(numero_cliente, None)
            await enviar_mensaje(numero_cliente,
                "😔 *Sin conductores disponibles*\n\n"
                "Ningún conductor aceptó tu servicio en este momento.\n\n"
                "━━━━━━━━━━━━━━━━\n"
                "1️⃣ Intentar de nuevo\n"
                "0️⃣ Salir")
            sesiones[numero_cliente] = {"estado": S_MENU, "datos": {}}
    asyncio.create_task(timeout_sin_conductor())

# ── NUEVO: Calificación post-servicio ─────────────────────────────────────────
async def programar_calificacion(numero: str, datos_servicio: dict):
    """Espera X minutos y luego pide calificación al cliente."""
    # Si ya hay una calificación pendiente para este número, no programar otra
    if numero in calificacion_pendiente:
        return
    calificacion_pendiente.add(numero)
    await asyncio.sleep(MINUTOS_CALIFICAR * 60)
    calificacion_pendiente.discard(numero)

    # Solo preguntar si el cliente no está en medio de otro flujo
    sesion_actual = sesiones.get(numero, {})
    if sesion_actual.get("estado") not in [S_MENU, None]:
        return  # Está ocupado, no interrumpir

    sesiones[numero] = {
        "estado": S_CALIFICAR,
        "datos": {"servicio_calificado": datos_servicio}
    }

    tipo = datos_servicio.get("tipo", "servicio")
    destino = datos_servicio.get("destino", "tu destino")

    # Personalizar mensaje según tipo de servicio
    if tipo == "taxi":
        pregunta = f"¿Cómo estuvo tu viaje a *{destino}*? 🚖"
    elif tipo == "colectivo":
        pregunta = f"¿Cómo estuvo tu colectivo a *{destino}*? 🚌"
    elif tipo == "encomienda":
        pregunta = f"¿Llegó bien tu encomienda a *{destino}*? 📦"
    elif tipo == "turismo":
        pregunta = f"¿Cómo estuvo tu tour a *{destino}*? 🗺️"
    else:
        pregunta = f"¿Cómo estuvo tu servicio a *{destino}*?"

    await enviar_mensaje(numero,
        f"🌟 *{pregunta}*\n\n"
        f"Por favor califica tu experiencia:\n\n"
        f"1️⃣ ⭐ Malo\n"
        f"2️⃣ ⭐⭐ Regular\n"
        f"3️⃣ ⭐⭐⭐ Bueno\n"
        f"4️⃣ ⭐⭐⭐⭐ Muy bueno\n"
        f"5️⃣ ⭐⭐⭐⭐⭐ Excelente")

async def notificar_calificacion_operador(numero: str, datos: dict):
    """Notifica al operador cuando llega una calificación."""
    if not OPERADOR_WA:
        return
    estrellas = ESTRELLAS.get(str(datos.get("puntuacion")), "?")
    comentario = datos.get("comentario", "Sin comentario")
    servicio = datos.get("servicio_calificado", {})
    msg = (f"⭐ *NUEVA CALIFICACIÓN*\n\n"
           f"📱 Cliente: +{numero}\n"
           f"🚖 Servicio: {servicio.get('tipo', 'N/A')} → {servicio.get('destino', 'N/A')}\n"
           f"👤 Conductor: {servicio.get('conductor', 'No asignado')}\n"
           f"Puntuación: {estrellas} ({datos.get('puntuacion')}/5)\n"
           f"💬 _{comentario}_")
    await enviar_mensaje(OPERADOR_WA, msg)

def resumen_calificaciones() -> str:
    """Genera resumen de calificaciones para el operador."""
    if not calificaciones:
        return "📊 No hay calificaciones aún."
    total = len(calificaciones)
    promedio = sum(c["puntuacion"] for c in calificaciones) / total
    dist = {i: sum(1 for c in calificaciones if c["puntuacion"] == i) for i in range(1, 6)}
    texto = f"📊 *Resumen de calificaciones*\n\n"
    texto += f"Total: {total} | Promedio: {promedio:.1f} ⭐\n\n"
    for i in range(5, 0, -1):
        barra = "█" * dist[i] + "░" * (total - dist[i])
        texto += f"{ESTRELLAS[str(i)]}: {dist[i]} ({barra[:10]})\n"
    ultimas = calificaciones[-3:]
    if ultimas:
        texto += "\n*Últimas 3:*\n"
        for c in reversed(ultimas):
            texto += f"• {ESTRELLAS[str(c['puntuacion'])]} _{c.get('comentario', 'Sin comentario')[:40]}_\n"
    return texto

# ── Procesador principal ──────────────────────────────────────────────────────
async def procesar(numero: str, tipo: str, contenido: dict):
    if numero not in sesiones:
        sesiones[numero] = {"estado": S_MENU, "datos": {}}

    # Actualizar timestamp de actividad
    ultima_actividad[numero] = time.time()

    sesion = sesiones[numero]
    estado = sesion["estado"]
    datos  = sesion["datos"]

    texto = ""
    lat = lng = None
    if tipo == "text":
        texto = contenido.get("body", "").strip()
    elif tipo == "location":
        lat = contenido.get("latitude")
        lng = contenido.get("longitude")

    # Comando operador: ver calificaciones
    if texto.lower() in ["calificaciones", "/calificaciones", "ratings"]:
        await enviar_mensaje(numero, resumen_calificaciones())
        return

    # Comando cliente: ver historial
    if texto.lower() in ["mis viajes", "historial", "mis servicios", "/historial"]:
        await enviar_mensaje(numero, formato_historial(numero))
        return

    # ── Conductor responde ACEPTO (con sinónimos) ────────────────────────────
    SINONIMOS_ACEPTO = {"listo","si","sí","ok","dale","voy","ya","tomo","vamos"}
    txt_norm = texto.strip().lower()
    if numero in CONDUCTORES and txt_norm in SINONIMOS_ACEPTO:
        if numero in viajes_activos:
            texto = "CONFIRMO"
        else:
            texto = "ACEPTO"
    if texto.upper().startswith("ACEPTO") and numero in CONDUCTORES:
        partes = texto.strip().split()
        if len(partes) >= 2:
            numero_cliente = partes[1].replace("+", "").replace("51", "", 1) if partes[1].startswith("+51") else partes[1]
            numero_cliente_full = numero_cliente if numero_cliente.startswith("51") else f"51{numero_cliente}"

            # Verificar que el servicio existe y no fue tomado
            if numero_cliente_full not in servicios_pendientes:
                await enviar_mensaje(numero, "❌ Este servicio ya no está disponible.")
                return
            if numero_cliente_full in servicios_tomados:
                await enviar_mensaje(numero, "❌ Este servicio ya fue tomado por otro conductor.")
                return

            # Marcar como tomado
            servicios_tomados.add(numero_cliente_full)
            servicio = servicios_pendientes.pop(numero_cliente_full)
            conductor = CONDUCTORES[numero]
            tipo_servicio = servicio.get("tipo", "TAXI")

            # Avisar a los demás conductores
            for num_cond in CONDUCTORES.keys():
                if num_cond != numero:
                    await enviar_mensaje(num_cond,
                        f"❌ *Servicio tomado*\n"
                        f"El servicio para {servicio['datos'].get('nombre','N/A')} "
                        f"ya fue tomado por {conductor['nombre']}.")

            # Registrar viaje activo conductor→cliente
            viajes_activos[numero] = numero_cliente_full
            viajes_activos_tipo[numero] = tipo_servicio

            # ── TAXI: notificar pasajero inmediatamente + informar conductor ──
            if tipo_servicio == "TAXI":
                tarifa = servicio['datos'].get('tarifa', 'a coordinar')
                tarifa_txt = f"S/{tarifa}" if tarifa != 'a coordinar' else "a coordinar con el conductor"
                # Notificar al pasajero de inmediato
                await enviar_mensaje(numero_cliente_full,
                    f"🚖 *¡Conductor en camino!*\n\n"
                    f"👤 {conductor['nombre']}\n"
                    f"🚗 Placa: {conductor['placa']}\n"
                    f"📱 Contacto: +{numero}\n"
                    f"💰 Tarifa: {tarifa_txt}\n\n"
                    f"El conductor te contactará en breve.\n"
                    f"Escribe *menu* para otra solicitud.")
                # Informar al conductor con opción de ajustar
                await enviar_mensaje(numero,
                    f"✅ *¡Servicio tomado!*\n\n"
                    f"👤 {servicio['datos'].get('nombre', 'N/A')} | 📱 +{numero_cliente_full}\n"
                    f"📍 {servicio['datos'].get('recojo_texto', 'N/A')}\n"
                    f"🏁 {servicio['datos'].get('destino_texto', 'N/A')}\n"
                    f"📏 {servicio['datos'].get('km', 0):.1f} km\n"
                    f"💰 Tarifa: {tarifa_txt}\n\n"
                    f"Pasajero notificado con tus datos.\n"
                    f"Si deseas ajustar precio escribe: *AJUSTO [precio]*\n"
                    f"Cuando llegues escribe: *LLEGUE*\n"
                    f"Al terminar escribe: *FIN*")
            else:
                # ENCOMIENDA / COLECTIVO / TURISMO — notificar inmediatamente
                await enviar_mensaje(numero,
                    f"✅ *¡Servicio asignado!*\n\n"
                    f"📱 Cliente: +{numero_cliente_full}\n"
                    f"👤 {servicio['datos'].get('nombre', 'N/A')}\n"
                    f"📍 {servicio['datos'].get('recojo_texto') or servicio['datos'].get('colectivo_recojo') or servicio['datos'].get('enc_origen', 'N/A')}\n"
                    f"🏁 {servicio['datos'].get('destino_texto') or servicio['datos'].get('colectivo_ruta') or servicio['datos'].get('enc_destino', 'N/A')}\n\n"
                    f"Contáctalo directamente para coordinar.")
                if servicio['datos'].get('enc_foto_id'):
                    await reenviar_imagen(numero, servicio['datos']['enc_foto_id'])
                await enviar_mensaje(numero_cliente_full,
                    f"🚖 *¡Conductor en camino!*\n\n"
                    f"👤 {conductor['nombre']}\n"
                    f"🚗 Placa: {conductor['placa']}\n"
                    f"📱 Contacto: +{numero}\n\n"
                    f"El conductor te contactará en breve.\n"
                    f"Escribe *menu* para otra solicitud.")
                if tipo_servicio == "TURISMO":
                    datos_reg = servicio["datos"].copy()
                    datos_reg["telefono"] = numero_cliente_full
                    datos_reg["conductor_nombre"] = conductor["nombre"]
                    datos_reg["conductor_placa"] = conductor["placa"]
                    datos_reg["conductor_telefono"] = numero
                    asyncio.create_task(registrar_turismo_sheets(datos_reg))

            # Limpiar después de 5 minutos anti-doble
            async def limpiar_tomado():
                await asyncio.sleep(300)
                servicios_tomados.discard(numero_cliente_full)
            asyncio.create_task(limpiar_tomado())

        else:
            # Sin número — intentar tomar el único servicio pendiente automáticamente
            pendientes_disponibles = [
                nc for nc in servicios_pendientes
                if nc not in servicios_tomados
                and numero in servicios_pendientes[nc].get("conductores_notificados", [])
            ]
            if len(pendientes_disponibles) == 1:
                numero_cliente_full = pendientes_disponibles[0]
                servicios_tomados.add(numero_cliente_full)
                servicio = servicios_pendientes.pop(numero_cliente_full)
                conductor = CONDUCTORES[numero]
                tipo_servicio = servicio.get("tipo", "TAXI")

                for num_cond in CONDUCTORES.keys():
                    if num_cond != numero:
                        await enviar_mensaje(num_cond,
                            f"❌ *Servicio tomado*\n"
                            f"El servicio para {servicio['datos'].get('nombre','N/A')} "
                            f"ya fue tomado por {conductor['nombre']}.")

                viajes_activos[numero] = numero_cliente_full
                viajes_activos_tipo[numero] = tipo_servicio

                if tipo_servicio == "TAXI":
                    tarifa = servicio['datos'].get('tarifa', 'a coordinar')
                    tarifa_txt = f"S/{tarifa}" if tarifa != 'a coordinar' else "a coordinar con el conductor"
                    await enviar_mensaje(numero_cliente_full,
                        f"🚖 *¡Conductor en camino!*\n\n"
                        f"👤 {conductor['nombre']}\n"
                        f"🚗 Placa: {conductor['placa']}\n"
                        f"📱 Contacto: +{numero}\n"
                        f"💰 Tarifa: {tarifa_txt}\n\n"
                        f"El conductor te contactará en breve.\n"
                        f"Escribe *menu* para otra solicitud.")
                    await enviar_mensaje(numero,
                        f"✅ *¡Servicio tomado!*\n\n"
                        f"👤 {servicio['datos'].get('nombre', 'N/A')} | 📱 +{numero_cliente_full}\n"
                        f"📍 {servicio['datos'].get('recojo_texto', 'N/A')}\n"
                        f"🏁 {servicio['datos'].get('destino_texto', 'N/A')}\n"
                        f"📏 {servicio['datos'].get('km', 0):.1f} km\n"
                        f"💰 Tarifa: {tarifa_txt}\n\n"
                        f"Pasajero notificado con tus datos.\n"
                        f"Si deseas ajustar precio escribe: *AJUSTO [precio]*\n"
                        f"Cuando llegues escribe: *LLEGUE*\n"
                        f"Al terminar escribe: *FIN*")
                else:
                    await enviar_mensaje(numero,
                        f"✅ *¡Servicio asignado!*\n\n"
                        f"📱 Cliente: +{numero_cliente_full}\n"
                        f"👤 {servicio['datos'].get('nombre', 'N/A')}\n"
                        f"📍 {servicio['datos'].get('recojo_texto') or servicio['datos'].get('colectivo_recojo') or servicio['datos'].get('enc_origen', 'N/A')}\n"
                        f"🏁 {servicio['datos'].get('destino_texto') or servicio['datos'].get('colectivo_ruta') or servicio['datos'].get('enc_destino', 'N/A')}\n\n"
                        f"Contáctalo directamente para coordinar.")
                    if servicio['datos'].get('enc_foto_id'):
                        await reenviar_imagen(numero, servicio['datos']['enc_foto_id'])
                    await enviar_mensaje(numero_cliente_full,
                        f"🚖 *¡Conductor en camino!*\n\n"
                        f"👤 {conductor['nombre']}\n"
                        f"🚗 Placa: {conductor['placa']}\n"
                        f"📱 Contacto: +{numero}\n\n"
                        f"El conductor te contactará en breve.\n"
                        f"Escribe *menu* para otra solicitud.")
                    if tipo_servicio == "TURISMO":
                        datos_reg = servicio["datos"].copy()
                        datos_reg["telefono"] = numero_cliente_full
                        datos_reg["conductor_nombre"] = conductor["nombre"]
                        datos_reg["conductor_placa"] = conductor["placa"]
                        datos_reg["conductor_telefono"] = numero
                        asyncio.create_task(registrar_turismo_sheets(datos_reg))

                async def limpiar_tomado_auto():
                    await asyncio.sleep(300)
                    servicios_tomados.discard(numero_cliente_full)
                asyncio.create_task(limpiar_tomado_auto())

            elif len(pendientes_disponibles) > 1:
                # Hay varios — mostrar lista para que elija
                lista = "\n".join([
                    f"• *ACEPTO {nc}* — {servicios_pendientes[nc]['datos'].get('nombre','N/A')}"
                    for nc in pendientes_disponibles
                ])
                await enviar_mensaje(numero,
                    f"Hay {len(pendientes_disponibles)} servicios pendientes. ¿Cuál aceptas?\n\n{lista}")
            else:
                await enviar_mensaje(numero,
                    "No tienes servicios pendientes por aceptar.")
        return

    # ── Conductor confirma tarifa (TAXI y ENCOMIENDA) ─────────────────────
    if numero in CONDUCTORES and (texto.upper().startswith("CONFIRMO") or texto.upper().startswith("CONFIRMAR")):
        num_cliente = viajes_activos.get(numero)
        if num_cliente:
            tipo_activo = viajes_activos_tipo.get(numero, "TAXI")
            conductor_info = CONDUCTORES[numero]
            if tipo_activo == "TAXI":
                # Notificar al cliente con datos del conductor
                await enviar_mensaje(num_cliente,
                    f"🚖 *¡Conductor en camino!*\n\n"
                    f"👤 {conductor_info['nombre']}\n"
                    f"🚗 Placa: {conductor_info['placa']}\n"
                    f"📱 Contacto: +{numero}\n\n"
                    f"El conductor te contactará en breve.\n"
                    f"Escribe *menu* para otra solicitud.")
                await enviar_mensaje(numero, "✅ Tarifa confirmada. Cliente notificado con tus datos.")
            else:
                await enviar_mensaje(num_cliente,
                    "✅ *El conductor confirmó la tarifa.*\n\n"
                    "Tu encomienda está en camino. 📦🚖")
                await enviar_mensaje(numero, "✅ Tarifa confirmada. Cliente notificado.")
        else:
            await enviar_mensaje(numero, "No tienes un servicio activo.")
        return

    if numero in CONDUCTORES and texto.upper().startswith("AJUSTO"):
        num_cliente = viajes_activos.get(numero)
        if num_cliente:
            partes = texto.strip().split()
            if len(partes) >= 2 and partes[1].replace(".", "").isdigit():
                nuevo_precio = float(partes[1])
                tipo_activo = viajes_activos_tipo.get(numero, "TAXI")
                datos_cli = sesiones.get(num_cliente, {}).get("datos", {})
                precio_ref = datos_cli.get("ruta_precio_ref") or datos_cli.get("tarifa")
                # Validar rango solo para turismo
                if tipo_activo == "TURISMO" and precio_ref and isinstance(precio_ref, (int, float)):
                    precio_min = round(precio_ref * TURISMO_MARGEN_MIN)
                    precio_max = round(precio_ref * TURISMO_MARGEN_MAX)
                    if nuevo_precio < precio_min or nuevo_precio > precio_max:
                        await enviar_mensaje(numero,
                            f"❌ *Precio fuera del rango permitido*\n\n"
                            f"El precio referencial es S/{precio_ref}\n"
                            f"Rango permitido: S/{precio_min} — S/{precio_max}\n\n"
                            f"Propón un precio dentro de ese rango.")
                        return
                ref_txt = f"\n_(Precio referencial: S/{precio_ref})_" if precio_ref else ""
                await enviar_mensaje(num_cliente,
                    f"💰 *El conductor propone S/{nuevo_precio:.0f}*{ref_txt}\n\n"
                    "¿Aceptas?\n"
                    "1️⃣ Sí, acepto\n"
                    "2️⃣ No, cancelar")
                await enviar_mensaje(numero, f"✅ Propuesta S/{nuevo_precio:.0f} enviada al cliente.")
            else:
                await enviar_mensaje(numero, "Formato: *AJUSTO [precio]*\nEj: AJUSTO 8")
        else:
            await enviar_mensaje(numero, "No tienes un servicio activo.")
        return

    # "0" → regresar al paso anterior del flujo
    if texto == "0" and estado not in [S_MENU, None]:
        if numero in CONDUCTORES:
            pass  # conductores no usan este flujo
        else:
            prev_estado = ESTADO_ANTERIOR.get(estado, S_MENU)
            # Limpiar datos del paso actual según el estado
            _campos_por_estado = {
                S_RECOJO: ["recojo_texto","recojo_lat","recojo_lng","_recojo_coords"],
                S_DESTINO: ["destino_texto","destino_lat","destino_lng"],
                S_CUANDO: ["cuando","fecha_programada"],
                S_PAGO: ["pago"],
                S_COLECTIVO_HORARIO: ["colectivo_horario"],
                S_COLECTIVO_ASIENTOS: ["colectivo_asientos","colectivo_total"],
                S_COLECTIVO_RECOJO: ["colectivo_recojo"],
                S_COLECTIVO_PAGO: ["colectivo_pago"],
                S_ENCOMIENDA_BULTOS: ["enc_paquetes"],
                S_ENCOMIENDA_TAMANO: ["enc_tamano"],
                S_ENCOMIENDA_FOTO: ["enc_foto","enc_foto_id"],
                S_ENCOMIENDA_URGENCIA: ["enc_urgencia","enc_recargo"],
                S_ENCOMIENDA_ORIGEN: ["enc_origen"],
                S_ENCOMIENDA_DESTINO: ["enc_destino"],
                S_ENCOMIENDA_DESTINATARIO: ["enc_destinatario"],
                S_ENCOMIENDA_PAGO: ["pago"],
                S_TURISMO_MODALIDAD: ["modalidad"],
                S_TURISMO_PERSONAS: ["personas"],
                S_TURISMO_TIPO_GRUPO: ["tipo_grupo"],
                S_TURISMO_CUANDO: ["cuando_turismo","fecha"],
                S_TURISMO_RECOJO: ["recojo_texto"],
                S_TURISMO_PAGO: ["pago"],
                S_TURISMO_PASAJEROS: ["turismo_dni_principal","turismo_pasajeros_extra","turismo_pasajeros_lista"],
            }
            for campo in _campos_por_estado.get(estado, []):
                datos.pop(campo, None)
            datos.pop("_sugerencias", None)
            datos.pop("_esperando_confirm_recojo", None)

            sesiones[numero]["estado"] = prev_estado
            if prev_estado == S_MENU:
                sesiones[numero] = {"estado": S_MENU, "datos": {}}
                await enviar_mensaje(numero, "⬅️ " + MSG_BIENVENIDA)
            else:
                prompt = PROMPT_VOLVER.get(prev_estado, "Continuemos desde el paso anterior.")
                await enviar_mensaje(numero, f"⬅️ *Paso anterior*\n\n{prompt}{NAV}")
            return

    # "salir/chau" → despedirse
    if texto in ["salir", "chau", "bye", "adios", "adiós"]:
        if estado not in [S_MENU, None] and estado is not None:
            sesiones[numero]["datos"]["_confirmando_salida"] = True
            await enviar_mensaje(numero,
                "⚠️ *¿Seguro que quieres cancelar?*\n\n"
                "Perderás el servicio que estás solicitando.\n\n"
                "1️⃣ Sí, cancelar\n"
                "2️⃣ No, continuar")
            return
        sesiones.pop(numero, None)
        historial_ia.pop(numero, None)
        await enviar_mensaje(numero,
            "👋 *¡Hasta pronto!*\n\n"
            "Cuando necesites un servicio escribe *hola* o *1*.\n\n"
            "_Barranca Móvil — siempre a tu servicio_ 🚖")
        return

    # Confirmar cancelación
    if datos.get("_confirmando_salida"):
        if texto == "1":
            sesiones.pop(numero, None)
            historial_ia.pop(numero, None)
            await enviar_mensaje(numero,
                "👋 *¡Hasta pronto!*\n\n"
                "Cuando necesites un servicio escribe *hola* o *1*.\n\n"
                "_Barranca Móvil — siempre a tu servicio_ 🚖")
        else:
            datos.pop("_confirmando_salida", None)
            await enviar_mensaje(numero, "✅ Continuemos. ¿Por dónde íbamos?")
        return

    # ── Comandos exclusivos conductores ─────────────────────────────────────
    if numero in CONDUCTORES:
        conductor_info = CONDUCTORES[numero]
        txt_up = texto.upper().strip()

        if txt_up in ["PAUSAR", "PAUSA"]:
            conductores_estado[numero] = False
            await enviar_mensaje(numero,
                f"⏸️ *{conductor_info['nombre']}* — PAUSADO\n\n"
                "No recibirás nuevos servicios.\n"
                "Escribe *ACTIVAR* cuando estés disponible.")
            return

        if txt_up in ["ACTIVAR", "ACTIVO"]:
            conductores_estado[numero] = True
            await enviar_mensaje(numero,
                f"✅ *{conductor_info['nombre']}* — ACTIVO\n\n"
                "Ya recibirás nuevos servicios.\n"
                "Escribe *PAUSAR* cuando no estés disponible.")
            return

        if txt_up == "LLEGUE":
            num_cliente = viajes_activos.get(numero)
            if num_cliente:
                await enviar_mensaje(num_cliente,
                    f"📍 *¡Tu conductor llegó!*\n\n"
                    f"👤 {conductor_info['nombre']} — {conductor_info['placa']}\n"
                    "te está esperando en el punto de recojo. 🚗")
                await enviar_mensaje(numero, "✅ Cliente notificado que llegaste.")
            else:
                await enviar_mensaje(numero, "No tienes un viaje activo.")
            return

        if txt_up == "FIN":
            num_cliente = viajes_activos.get(numero)
            if num_cliente:
                datos_servicio = {"tipo": "taxi", "destino": "tu destino", "conductor": conductor_info["nombre"]}
                viajes_activos.pop(numero, None)
                await enviar_mensaje(numero,
                    f"🏁 *Viaje finalizado* — ¡Buen trabajo {conductor_info['nombre']}! 💪\n\n"
                    "Escribe *PAUSAR* si descansas o sigue recibiendo servicios.")
                asyncio.create_task(programar_calificacion(num_cliente, datos_servicio))
            else:
                await enviar_mensaje(numero, "No tienes un viaje activo.")
            return

        if texto.lower() in ["menu", "menú", "hola", "inicio", "start"]:
            estado_txt = "🟢 ACTIVO" if conductores_estado.get(numero, True) else "🔴 PAUSADO"
            viaje_txt = f"👤 Cliente activo: +{viajes_activos[numero]}" if numero in viajes_activos else "Sin viaje activo"
            await enviar_mensaje(numero,
                f"🚖 *Panel Conductor*\n"
                f"👤 {conductor_info['nombre']} | {conductor_info['placa']}\n"
                f"Estado: {estado_txt}\n"
                f"{viaje_txt}\n\n"
                f"Comandos disponibles:\n"
                f"• *ACEPTO [número]* — aceptar servicio\n"
                f"• *LLEGUE* — avisar que llegué al recojo\n"
                f"• *FIN* — marcar viaje terminado\n"
                f"• *PAUSAR* / *ACTIVAR* — cambiar disponibilidad")
            return

    # ── Cancelación cliente con servicio pendiente o asignado ────────────────
    if texto.upper() == "CANCELAR":
        if numero in servicios_pendientes:
            servicios_pendientes.pop(numero, None)
        for num_cond, num_cli in list(viajes_activos.items()):
            if num_cli == numero:
                viajes_activos.pop(num_cond, None)
                await enviar_mensaje(num_cond,
                    "❌ *El cliente canceló el servicio.*\n\n"
                    "Ya puedes tomar otro servicio.")
                break
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        await enviar_mensaje(numero,
            "❌ Servicio cancelado.\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "1️⃣ Nuevo servicio\n0️⃣ Salir")
        return

    palabras_menu = ["menu", "menú", "inicio", "hola", "hi", "buenas",
                     "buenos días", "buenas tardes", "buenas noches", "ola", "start"]
    if texto.lower() in palabras_menu:
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        historial_ia.pop(numero, None)
        await enviar_mensaje(numero, MSG_BIENVENIDA)
        return

    # Limpiar historial IA si tiene más de 20 mensajes
    if numero in historial_ia and len(historial_ia[numero]) > 20:
        historial_ia[numero] = historial_ia[numero][-10:]  # conservar últimos 10

    print(f"[{estado}] {numero}: {texto or f'gps({lat},{lng})'}", flush=True)

    # ══ CALIFICACIÓN ══════════════════════════════════════════════════════════
    if estado == S_CALIFICAR:
        if texto in ["1", "2", "3", "4", "5"]:
            datos["puntuacion"] = int(texto)
            estrellas = ESTRELLAS[texto]
            sesion["estado"] = S_CALIFICAR_COMMENT

            if int(texto) <= 2:
                await enviar_mensaje(numero,
                    f"😔 Lamentamos que tu experiencia haya sido {estrellas}\n\n"
                    "¿Puedes contarnos qué salió mal? Tu opinión nos ayuda a mejorar.\n"
                    "_(O escribe *omitir* para saltar)_")
            else:
                await enviar_mensaje(numero,
                    f"¡Gracias! {estrellas}\n\n"
                    "¿Quieres dejarnos algún comentario? 😊\n"
                    "_(O escribe *omitir* para terminar)_")
        else:
            await enviar_mensaje(numero, "Por favor responde del *1* al *5* para calificar.")

    elif estado == S_CALIFICAR_COMMENT:
        comentario = "" if texto.lower() == "omitir" else texto
        datos["comentario"] = comentario

        # Guardar calificación
        registro = {
            "numero": numero,
            "puntuacion": datos.get("puntuacion"),
            "comentario": comentario,
            "servicio_calificado": datos.get("servicio_calificado", {}),
            "timestamp": time.time()
        }
        calificaciones.append(registro)

        # Notificar operador
        await notificar_calificacion_operador(numero, datos)

        puntuacion = datos.get("puntuacion", 3)
        sesiones[numero] = {"estado": S_MENU, "datos": {}}

        OPCIONES_FINAL = "\n\n━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir"

        if puntuacion >= 4:
            respuesta_final = (f"🙏 *¡Gracias por tu calificación!*\n\n"
                               f"Nos alegra que hayas tenido una buena experiencia.\n"
                               f"Te esperamos pronto en *Barranca Móvil* 🚖"
                               f"{OPCIONES_FINAL}")
        else:
            respuesta_final = (f"🙏 *Gracias por tu opinión.*\n\n"
                               f"Tomaremos acción para mejorar el servicio.\n"
                               f"Disculpa los inconvenientes 🙏"
                               f"{OPCIONES_FINAL}")
        await enviar_mensaje(numero, respuesta_final)

    # ══ MENU ══════════════════════════════════════════════════════════════════
    elif estado == S_MENU:
        if texto == "1":
            sesion["estado"] = S_NOMBRE
            datos["servicio"] = "TAXI"
            await enviar_mensaje(numero, "🙋 ¿Cuál es tu nombre?")
        elif texto == "2":
            sesion["estado"] = S_NOMBRE
            datos["servicio"] = "COLECTIVO"
            await enviar_mensaje(numero, "🚌 ¡Genial! ¿Cuál es tu nombre?")
        elif texto == "3":
            sesion["estado"] = S_NOMBRE
            datos["servicio"] = "ENCOMIENDA"
            await enviar_mensaje(numero, "📦 ¡Perfecto! ¿Cuál es tu nombre?")
        elif texto == "4":
            sesion["estado"] = S_NOMBRE
            datos["servicio"] = "TURISMO"
            await enviar_mensaje(numero, "🗺️ ¡Genial! ¿Cuál es tu nombre?")
        elif texto == "5":
            await enviar_mensaje(numero, MSG_TARIFAS)
        elif texto == "6":
            await enviar_mensaje(numero, MSG_AYUDA)
        elif texto == "7":
            sesion["estado"] = S_RECLAMO_TIPO
            await enviar_mensaje(numero,
                "📋 *Reclamos y sugerencias*\n\n"
                "¿Qué deseas reportar?\n\n"
                "1️⃣ Reclamo — tuve un problema con el servicio\n"
                "2️⃣ Sugerencia — quiero proponer una mejora\n"
                "3️⃣ Consulta — tengo una pregunta\n\n"
                "_(O escribe *menu* para volver)_")
        else:
            resp = await respuesta_ia(numero, texto)
            datos["ultima_consulta"] = texto
            datos["ultima_respuesta"] = resp
            sesion["estado"] = S_CONSULTA_OPCION
            await enviar_mensaje(numero,
                f"{resp}\n\n━━━━━━━━━━━━━━━━━━\n"
                "¿Qué deseas hacer?\n\n"
                "1️⃣ Hacer una solicitud ahora\n"
                "2️⃣ Hablar con un operador 👤")

    # ══ CONSULTA OPCION ═══════════════════════════════════════════════════════
    elif estado == S_CONSULTA_OPCION:
        if texto == "1":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, MSG_BIENVENIDA)
        elif texto == "2":
            await notificar_operador_consulta(numero, datos.get("ultima_consulta",""), datos.get("ultima_respuesta",""))
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                "👤 *¡Listo!*\n\nUn operador te contactará en breve.\n\nEscribe *menu* si deseas algo más.")
        else:
            resp = await respuesta_ia(numero, texto)
            datos["ultima_consulta"] = texto
            datos["ultima_respuesta"] = resp
            await enviar_mensaje(numero,
                f"{resp}\n\n━━━━━━━━━━━━━━━━━━\n"
                "¿Qué deseas hacer?\n\n"
                "1️⃣ Hacer una solicitud ahora\n"
                "2️⃣ Hablar con un operador 👤")

    # ══ RECLAMOS ══════════════════════════════════════════════════════════════
    elif estado == S_RECLAMO_TIPO:
        tipos = {"1": "Reclamo", "2": "Sugerencia", "3": "Consulta"}
        if texto not in tipos:
            await enviar_mensaje(numero,
                "Responde *1* Reclamo, *2* Sugerencia o *3* Consulta.")
            return
        datos["reclamo_tipo"] = tipos[texto]
        sesion["estado"] = S_RECLAMO
        await enviar_mensaje(numero,
            f"📝 *{tipos[texto]}*\n\n"
            "Cuéntanos con detalle qué pasó o qué propones:\n"
            "_(Escribe tu mensaje)_")

    elif estado == S_RECLAMO:
        if len(texto.strip()) < 5:
            await enviar_mensaje(numero, "Por favor describe tu mensaje con más detalle.")
            return
        global _ticket_counter
        _ticket_counter += 1
        ticket_id = f"TK-{_ticket_counter:04d}"
        ticket = {
            "id": ticket_id,
            "numero": numero,
            "tipo": datos.get("reclamo_tipo", "Consulta"),
            "mensaje": texto.strip(),
            "estado": "nuevo",
            "timestamp": time.time(),
            "respuesta": ""
        }
        tickets.append(ticket)
        # Notificar operador
        if OPERADOR_WA:
            await enviar_mensaje(OPERADOR_WA,
                f"📋 *NUEVO TICKET {ticket_id}*\n\n"
                f"👤 Cliente: +{numero}\n"
                f"📌 Tipo: {ticket['tipo']}\n"
                f"💬 Mensaje: {texto.strip()}\n\n"
                f"Responde desde el dashboard.")
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        await enviar_mensaje(numero,
            f"✅ *¡Recibido! Ticket {ticket_id}*\n\n"
            f"Tu {ticket['tipo'].lower()} fue registrado.\n"
            f"Te contactaremos en menos de 2 horas.\n\n"
            f"Gracias por ayudarnos a mejorar 🙏\n"
            f"Escribe *menu* cuando necesites algo más.")

    # ══ NOMBRE ════════════════════════════════════════════════════════════════
    elif estado == S_NOMBRE:
        if len(texto) < 2:
            await enviar_mensaje(numero, "Por favor escribe tu nombre.")
            return
        datos["nombre"] = texto.title()
        servicio = datos.get("servicio")
        if servicio == "TAXI":
            sesion["estado"] = S_CUANDO
            await enviar_mensaje(numero,
                f"👍 Hola *{datos['nombre']}*!\n\n"
                "🕐 *¿Cuándo necesitas el taxi?*\n\n"
                "1️⃣ Ahora mismo\n"
                "2️⃣ En menos de 1 hora\n"
                "3️⃣ Programar fecha y hora 📅\n"
                "4️⃣ Viaje recurrente 🔄")
        elif servicio == "COLECTIVO":
            sesion["estado"] = S_COLECTIVO_RUTA
            rutas_txt = "\n".join([f"{k}️⃣ {v['emoji']} {v['nombre']} — S/{v['tarifa']:.2f}" 
                                    for k,v in COLECTIVO_RUTAS.items()])
            await enviar_mensaje(numero,
                f"👍 Hola *{datos['nombre']}*! 🚌\n\n"
                f"*¿A dónde vas?*\n\n"
                f"{rutas_txt}\n\n"
                f"_(Precios por pasajero, incluye recojo en tu domicilio)_")
        elif servicio == "ENCOMIENDA":
            sesion["estado"] = S_ENCOMIENDA_DESC
            await enviar_mensaje(numero,
                f"👍 Hola *{datos['nombre']}*!\n\n"
                "📦 ¿Qué vas a enviar?\n_(ej: ropa, documentos, paquete)_")
        elif servicio == "TURISMO":
            sesion["estado"] = S_TURISMO_DESTINO
            await enviar_mensaje(numero, f"👍 Hola *{datos['nombre']}*!\n\n" + MSG_TURISMO_OPCIONES)

    # ══ TAXI: ¿CUÁNDO? ═══════════════════════════════════════════════════════
    elif estado == S_CUANDO:
        if texto == "1":
            # Ahora mismo → flujo normal
            datos["cuando"] = "ahora"
            sesion["estado"] = S_RECOJO
            await enviar_mensaje(numero,
                "📍 *¿Desde dónde te recogemos?*\n\n"
                "• 📌 Comparte tu ubicación (clip → Ubicación)\n"
                "• ✍️ O escribe tu dirección / barrio")
        elif texto == "2":
            # En menos de 1 hora → flujo normal con nota
            datos["cuando"] = "menos de 1 hora"
            sesion["estado"] = S_RECOJO
            await enviar_mensaje(numero,
                "📍 *¿Desde dónde te recogemos?*\n\n"
                "• 📌 Comparte tu ubicación (clip → Ubicación)\n"
                "• ✍️ O escribe tu dirección / barrio")
        elif texto == "3":
            # Programar fecha y hora
            datos["cuando"] = "programado"
            sesion["estado"] = S_PROGRAMAR
            await enviar_mensaje(numero,
                "📅 *¿Para qué fecha y hora?*\n\n"
                "Escríbelo así:\n"
                "• _Mañana a las 6:00 am_\n"
                "• _Sábado 10 de mayo 8:30 am_\n"
                "• _Hoy a las 9pm_")
        elif texto == "4":
            # Viaje recurrente
            datos["cuando"] = "recurrente"
            sesion["estado"] = S_RECURRENTE_DIAS
            await enviar_mensaje(numero,
                "🔄 *Viaje recurrente*\n\n"
                "¿Qué días de la semana necesitas el taxi?\n\n"
                "Escribe los días separados por coma:\n"
                "_(ej: Lunes, Miércoles, Viernes)_\n"
                "_(ej: Lunes a Viernes)_\n"
                "_(ej: Todos los días)_")
        else:
            await enviar_mensaje(numero,
                "Por favor elige una opción:\n\n"
                "1️⃣ Ahora mismo\n"
                "2️⃣ En menos de 1 hora\n"
                "3️⃣ Programar fecha y hora 📅\n"
                "4️⃣ Viaje recurrente 🔄")

    # ══ TAXI: FECHA PROGRAMADA ════════════════════════════════════════════════
    elif estado == S_PROGRAMAR:
        if len(texto) < 5:
            await enviar_mensaje(numero, "Por favor indica la fecha y hora. Ej: _Mañana a las 7am_")
            return
        datos["fecha_programada"] = texto
        sesion["estado"] = S_RECOJO
        await enviar_mensaje(numero,
            f"✅ Reserva para: *{texto}*\n\n"
            "📍 *¿Desde dónde te recogeremos?*\n\n"
            "• 📌 Comparte tu ubicación\n"
            "• ✍️ O escribe tu dirección / barrio")

    # ══ TAXI: VIAJE RECURRENTE - DÍAS ═════════════════════════════════════════
    elif estado == S_RECURRENTE_DIAS:
        if len(texto) < 3:
            await enviar_mensaje(numero, "Por favor indica los días. Ej: _Lunes, Miércoles, Viernes_")
            return
        datos["dias_recurrente"] = texto
        sesion["estado"] = S_RECURRENTE_HORA
        await enviar_mensaje(numero,
            f"📅 Días: *{texto}*\n\n"
            "🕐 *¿A qué hora necesitas el taxi?*\n"
            "_(ej: 6:30 am | 7:00 am | 8pm)_")

    # ══ TAXI: VIAJE RECURRENTE - HORA ═════════════════════════════════════════
    elif estado == S_RECURRENTE_HORA:
        if len(texto) < 3:
            await enviar_mensaje(numero, "Por favor indica la hora. Ej: _6:30 am_")
            return
        datos["hora_recurrente"] = texto
        sesion["estado"] = S_RECOJO
        await enviar_mensaje(numero,
            f"🔄 Viaje recurrente configurado:\n"
            f"📅 *{datos['dias_recurrente']}* a las *{texto}*\n\n"
            "📍 *¿Desde dónde te recogeremos?*\n\n"
            "• 📌 Comparte tu ubicación\n"
            "• ✍️ O escribe tu dirección / barrio")

    # ══ CONFIRMACIÓN RECOJO ══════════════════════════════════════════════════
    elif estado == S_CONFIRM_RECOJO:
        if texto == "1":
            datos["recojo_texto"] = datos.pop("recojo_texto_temp")
            datos["recojo_coords"] = datos.pop("recojo_coords_temp")
            sesion["estado"] = S_DESTINO
            await enviar_mensaje(numero,
                f"✅ Recojo: *{datos['recojo_texto']}*\n\n"
                "🏁 *¿A dónde vas?*\n\n"
                "• 📌 Comparte ubicación del destino\n"
                "• ✍️ O escribe el destino")
        elif texto == "2":
            datos.pop("recojo_texto_temp", None)
            datos.pop("recojo_coords_temp", None)
            sesion["estado"] = S_RECOJO   # volver a S_RECOJO para nueva búsqueda
            await enviar_mensaje(numero,
                "📍 *Escribe tu dirección de recojo:*\n"
                "_(Ej: Parque Guadalupe, Jr. Lima 234, Barrio El Molino)_")
        else:
            # Usuario escribió directamente una nueva dirección sin presionar 2 → buscar
            datos.pop("recojo_texto_temp", None)
            datos.pop("recojo_coords_temp", None)
            sesion["estado"] = S_RECOJO
            await resolver_direccion(texto, sesion, datos, numero,
                                     "recojo_texto_temp", "recojo_coords_temp",
                                     S_CONFIRM_RECOJO, "recojo")

    # ══ CONFIRMACIÓN DESTINO ══════════════════════════════════════════════════
    elif estado == S_CONFIRM_DESTINO:
        if texto == "1":
            datos["destino_texto"] = datos.pop("destino_texto_temp")
            datos["destino_coords"] = datos.pop("destino_coords_temp")
            # Calcular tarifa
            km = await calcular_distancia_km(datos["recojo_coords"], datos["destino_coords"])
            if km is None:
                # No se pudo calcular → coordinar con conductor
                datos.update({"tarifa": "a coordinar", "tarifa_detalle": "coord. conductor", "km": 0})
                sesion["estado"] = S_PAGO
                await enviar_mensaje(numero,
                    f"📋 *Resumen:*\n\n"
                    f"👤 {datos['nombre']}\n📍 {datos['recojo_texto']}\n"
                    f"🏁 {datos['destino_texto']}\n"
                    f"💰 Tarifa: *a coordinar con el conductor*\n\n"
                    "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
            else:
                tarifa, detalle = calcular_tarifa_taxi(datos["destino_texto"], km)
                datos.update({"tarifa": tarifa, "tarifa_detalle": detalle, "km": km})
                sesion["estado"] = S_PAGO
                await enviar_mensaje(numero,
                    f"📋 *Resumen:*\n\n"
                    f"👤 {datos['nombre']}\n📍 {datos['recojo_texto']}\n"
                    f"🏁 {datos['destino_texto']}\n📏 {km:.1f} km\n"
                    f"💰 Tarifa estimada: *S/{tarifa}* ({detalle})\n\n"
                    "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
        elif texto == "2":
            datos.pop("destino_texto_temp", None)
            datos.pop("destino_coords_temp", None)
            sesion["estado"] = S_DESTINO   # volver a S_DESTINO
            await enviar_mensaje(numero,
                "🏁 *Escribe el destino:*\n"
                "_(Ej: Plaza de Armas, Mercado Central, Jr. Grau 123)_")
        else:
            # Escribió directamente nueva dirección → buscar
            datos.pop("destino_texto_temp", None)
            datos.pop("destino_coords_temp", None)
            sesion["estado"] = S_DESTINO
            await resolver_direccion(texto, sesion, datos, numero,
                                     "destino_texto_temp", "destino_coords_temp",
                                     S_CONFIRM_DESTINO, "destino")
            return
        if False: await enviar_mensaje(numero,
                "Responde *1* si es correcto o *2* para escribir otro destino.")

    # ══ TAXI ══════════════════════════════════════════════════════════════════
    elif estado == S_RECOJO:
        if lat and lng:
            direccion = await coords_a_direccion(lat, lng)
            datos["recojo_texto"] = direccion
            datos["recojo_coords"] = f"{lat},{lng}"
            # GPS es preciso, ir directo al destino
            sesion["estado"] = S_DESTINO
            await enviar_mensaje(numero,
                f"✅ Recojo: *{direccion}*\n\n"
                "🏁 *¿A dónde vas?*\n\n"
                "• 📌 Comparte ubicación del destino\n"
                "• ✍️ O escribe el destino")
        elif texto:
            # Sugerencia elegida de lista previa → DIRECTO sin confirmación extra
            if "_sugerencias" in datos and texto in ["1","2","3","4"]:
                idx = int(texto) - 1
                sugs = datos["_sugerencias"]
                if idx < len(sugs):
                    sug = sugs[idx]
                    direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
                    datos.pop("_sugerencias", None)
                    datos["recojo_texto"] = direccion
                    datos["recojo_coords"] = coords
                    sesion["estado"] = S_DESTINO
                    await enviar_mensaje(numero,
                        f"✅ Recojo: *{direccion}*\n\n"
                        "🏁 *¿A dónde vas?*\n\n"
                        "• 📌 Comparte ubicación\n"
                        "• ✍️ O escribe el destino")
                    return
                datos.pop("_sugerencias", None)
            # Buscar con Autocomplete
            await resolver_direccion(texto, sesion, datos, numero,
                                     "recojo_texto_temp", "recojo_coords_temp",
                                     S_CONFIRM_RECOJO, "recojo")
        else:
            await enviar_mensaje(numero, "Comparte tu ubicación o escribe tu dirección.")

    elif estado == S_DESTINO:
        if lat and lng:
            direccion = await coords_a_direccion(lat, lng)
            datos["destino_texto"] = direccion
            datos["destino_coords"] = f"{lat},{lng}"
            # GPS preciso, calcular directo
            km = await calcular_distancia_km(datos["recojo_coords"], datos["destino_coords"])
            if km is None:
                datos.update({"tarifa": "a coordinar", "tarifa_detalle": "coord. conductor", "km": 0})
                sesion["estado"] = S_PAGO
                await enviar_mensaje(numero,
                    f"📋 *Resumen:*\n\n"
                    f"👤 {datos['nombre']}\n📍 {datos['recojo_texto']}\n"
                    f"🏁 {datos['destino_texto']}\n"
                    f"💰 Tarifa: *a coordinar con el conductor*\n\n"
                    "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
            else:
                tarifa, detalle = calcular_tarifa_taxi(datos["destino_texto"], km)
                datos.update({"tarifa": tarifa, "tarifa_detalle": detalle, "km": km})
                sesion["estado"] = S_PAGO
                await enviar_mensaje(numero,
                    f"📋 *Resumen:*\n\n"
                    f"👤 {datos['nombre']}\n📍 {datos['recojo_texto']}\n"
                    f"🏁 {datos['destino_texto']}\n📏 {km:.1f} km\n"
                    f"💰 Tarifa estimada: *S/{tarifa}* ({detalle})\n\n"
                    "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
        elif texto:
            # Sugerencia elegida de lista previa → DIRECTO calcular tarifa
            if "_sugerencias" in datos and texto in ["1","2","3","4"]:
                idx = int(texto) - 1
                sugs = datos["_sugerencias"]
                if idx < len(sugs):
                    sug = sugs[idx]
                    direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
                    datos.pop("_sugerencias", None)
                    datos["destino_texto"] = direccion
                    datos["destino_coords"] = coords
                    km = await calcular_distancia_km(datos.get("recojo_coords",""), coords)
                    if km is None:
                        datos.update({"tarifa": "a coordinar", "tarifa_detalle": "coord. conductor", "km": 0})
                    else:
                        tarifa, detalle = calcular_tarifa_taxi(direccion, km)
                        datos.update({"tarifa": tarifa, "tarifa_detalle": detalle, "km": km})
                    sesion["estado"] = S_PAGO
                    km_txt = f"\n📏 {datos.get('km',0):.1f} km" if datos.get("km") else ""
                    tarifa_txt = f"S/{datos['tarifa']}" if datos["tarifa"] != "a coordinar" else "A coordinar con conductor"
                    await enviar_mensaje(numero,
                        f"✅ Destino: *{direccion}*{km_txt}\n"
                        f"💰 Tarifa: *{tarifa_txt}*\n\n"
                        "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
                    return
                datos.pop("_sugerencias", None)
            # Buscar con Autocomplete
            await resolver_direccion(texto, sesion, datos, numero,
                                     "destino_texto_temp", "destino_coords_temp",
                                     S_CONFIRM_DESTINO, "destino")
        else:
            await enviar_mensaje(numero, "Comparte ubicación o escribe el destino.")

    elif estado == S_PAGO:
        if texto == "1": datos["pago"] = "Efectivo 💵"
        elif texto == "2": datos["pago"] = "Yape 📱"
        else:
            await enviar_mensaje(numero, "Responde *1* Efectivo o *2* Yape.")
            return
        sesion["estado"] = S_CONFIRMAR
        # Armar línea de tiempo según tipo de reserva
        cuando = datos.get("cuando", "ahora")
        if cuando == "programado":
            linea_tiempo = f"📅 Programado: {datos.get('fecha_programada')}\n"
        elif cuando == "recurrente":
            linea_tiempo = f"🔄 Recurrente: {datos.get('dias_recurrente')} a las {datos.get('hora_recurrente')}\n"
        elif cuando == "menos de 1 hora":
            linea_tiempo = "🕐 En menos de 1 hora\n"
        else:
            linea_tiempo = "⚡ Ahora mismo\n"

        await enviar_mensaje(numero,
            f"✅ *Confirma tu pedido:*\n\n"
            f"👤 {datos['nombre']}\n"
            f"{linea_tiempo}"
            f"📍 {datos['recojo_texto']}\n"
            f"🏁 {datos['destino_texto']}\n💰 S/{datos['tarifa']}\n💳 {datos['pago']}\n\n"
            "1️⃣ *CONFIRMAR* ✅\n2️⃣ *CANCELAR* ❌" + NAV)

    elif estado == S_CONFIRMAR:
        if texto == "1":
            await notificar_conductores(sesion, numero, "TAXI")
            guardar_viaje(numero, datos, "taxi")
            datos_servicio = {
                "tipo": "taxi",
                "destino": datos.get("destino_texto", "tu destino"),
                "conductor": "Pendiente"
            }
            # Guardar viaje recurrente si aplica
            cuando = datos.get("cuando", "ahora")
            if cuando == "recurrente":
                viajes_recurrentes[numero] = {
                    "nombre": datos.get("nombre"),
                    "dias": datos.get("dias_recurrente"),
                    "hora": datos.get("hora_recurrente"),
                    "recojo": datos.get("recojo_texto"),
                    "destino": datos.get("destino_texto"),
                    "tarifa": datos.get("tarifa"),
                }
                msg_ok = ("🎉 *¡Viaje recurrente configurado!*\n\n"
                         f"🔄 {datos.get('dias_recurrente')} a las {datos.get('hora_recurrente')}\n"
                         f"📍 {datos.get('recojo_texto')}\n"
                         f"🏁 {datos.get('destino_texto')}\n\n"
                         "Recibirás confirmación cada día programado.\n"
                         "Escribe *menu* para otra solicitud.")
            elif cuando == "programado":
                msg_ok = ("🎉 *¡Reserva programada!*\n\n"
                         f"📅 {datos.get('fecha_programada')}\n"
                         f"📍 {datos.get('recojo_texto')}\n"
                         f"🏁 {datos.get('destino_texto')}\n\n"
                         "Un conductor te contactará antes de la hora acordada.\n"
                         "Escribe *menu* para otra solicitud.")
            else:
                msg_ok = "🎉 *¡Solicitud enviada!*\n\nEstamos buscando conductor.\nTe contactarán pronto.\n\n━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir"
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, msg_ok)
            asyncio.create_task(programar_calificacion(numero, datos_servicio))
        elif texto == "2":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, "❌ Cancelado.\n\nEscribe *1* cuando quieras solicitar otro servicio.\n0️⃣ Salir")
        else:
            await enviar_mensaje(numero, "Responde *1* confirmar o *2* cancelar.")

    # ══ COLECTIVO ═════════════════════════════════════════════════════════════
    elif estado == S_COLECTIVO_RUTA:
        if texto not in COLECTIVO_RUTAS:
            rutas_txt = "\n".join([f"{k}️⃣ {v['emoji']} {v['nombre']} — S/{v['tarifa']:.2f}"
                                    for k,v in COLECTIVO_RUTAS.items()])
            await enviar_mensaje(numero, f"Elige una ruta:\n\n{rutas_txt}")
            return
        ruta = COLECTIVO_RUTAS[texto]
        datos["colectivo_ruta"] = ruta["nombre"]
        datos["colectivo_tarifa"] = ruta["tarifa"]
        datos["colectivo_emoji"] = ruta["emoji"]
        sesion["estado"] = S_COLECTIVO_HORARIO
        await enviar_mensaje(numero,
            f"{ruta['emoji']} *{ruta['nombre']}* — S/{ruta['tarifa']:.2f} por pasajero\n\n"
            f"🕐 *¿Cuándo necesitas el colectivo?*\n\n"
            f"1️⃣ Ahora mismo 🚀\n"
            f"2️⃣ Indicar hora 🕐\n\n"
            f"_(El conductor puede completar el cupo en el paradero)_")

    elif estado == S_COLECTIVO_HORARIO:
        if texto == "1":
            datos["colectivo_horario"] = "Ahora mismo 🚀"
        elif texto == "2":
            # Pedir hora libre
            sesion["estado"] = "COLECTIVO_HORA_LIBRE"
            await enviar_mensaje(numero,
                "🕐 *¿A qué hora necesitas el colectivo?*\n\n"
                "Escríbelo como quieras:\n"
                "_(ej: 6:30 am / mañana 8am / hoy a las 3pm)_")
            return
        else:
            await enviar_mensaje(numero,
                "Elige cuándo necesitas el colectivo:\n\n"
                "1️⃣ Ahora mismo 🚀\n"
                "2️⃣ Indicar hora 🕐" + NAV)
            return
        sesion["estado"] = S_COLECTIVO_ASIENTOS
        await enviar_mensaje(numero,
            f"✅ Salida: *{datos['colectivo_horario']}*\n\n"
            f"👥 *¿Cuántos asientos necesitas?* (máx. {COLECTIVO_MAX_ASIENTOS})\n\n"
            f"1️⃣  2️⃣  3️⃣  4️⃣")

    elif estado == "COLECTIVO_HORA_LIBRE":
        if len(texto) < 3:
            await enviar_mensaje(numero, "Por favor indica la hora. Ej: _6:30 am_")
            return
        datos["colectivo_horario"] = texto
        sesion["estado"] = S_COLECTIVO_ASIENTOS
        await enviar_mensaje(numero,
            f"✅ Salida: *{texto}*\n\n"
            f"👥 *¿Cuántos asientos necesitas?* (máx. {COLECTIVO_MAX_ASIENTOS})\n\n"
            f"1️⃣  2️⃣  3️⃣  4️⃣")

    elif estado == S_COLECTIVO_ASIENTOS:
        if not texto.isdigit() or int(texto) < 1 or int(texto) > COLECTIVO_MAX_ASIENTOS:
            await enviar_mensaje(numero, f"Indica entre 1 y {COLECTIVO_MAX_ASIENTOS} asientos.")
            return
        asientos = int(texto)
        datos["colectivo_asientos"] = asientos
        # Huacho y Lima no tienen recargo por recojo
        ruta_nombre = datos.get("colectivo_ruta", "").lower()
        sin_recojo = any(x in ruta_nombre for x in ["huacho", "lima"])
        if sin_recojo:
            extra = 0.0
        elif asientos == 1:
            extra = 1.00   # 1 asiento → +S/1.00
        else:
            extra = 0.50   # 2+ asientos → +S/0.50 por persona
        tarifa_total = round((datos["colectivo_tarifa"] + extra) * asientos)
        datos["colectivo_total"] = tarifa_total
        sesion["estado"] = S_COLECTIVO_RECOJO
        if extra > 0:
            detalle = f"_(S/{datos['colectivo_tarifa']} + S/{extra:.2f} recojo × {asientos})_"
        else:
            detalle = f"_(S/{datos['colectivo_tarifa']} × {asientos} asiento(s))_"
        await enviar_mensaje(numero,
            f"✅ {asientos} asiento(s) — Total: *S/{tarifa_total}*\n"
            f"{detalle}\n\n"
            f"📍 *¿Desde dónde te recogemos?*\n\n"
            f"• 📌 Comparte tu ubicación (clip → Ubicación)\n"
            f"• ✍️ O escribe tu dirección / barrio" + NAV)

    elif estado == S_COLECTIVO_RECOJO:
        if lat and lng:
            direccion_gps = await coords_a_direccion(lat, lng)
            if not direccion_gps:
                await enviar_mensaje(numero,
                    "📌 Recibí tu ubicación pero no pude identificar la dirección.\n\n"
                    "✍️ *Escribe el nombre del lugar o dirección:*\n"
                    "_(Ej: Parque Guadalupe, Jr. Lima 234)_")
                return
            datos["colectivo_recojo"] = direccion_gps
            sesion["estado"] = S_COLECTIVO_PAGO
            await enviar_mensaje(numero,
                f"✅ Recojo: *{direccion_gps}*\n\n"
                "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
        elif texto:
            # Sugerencia elegida de lista previa → DIRECTO a pago
            if "_sugerencias" in datos and texto in ["1","2","3","4"]:
                idx = int(texto) - 1
                sugs = datos["_sugerencias"]
                if idx < len(sugs):
                    sug = sugs[idx]
                    direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
                    datos.pop("_sugerencias", None)
                    datos["colectivo_recojo"] = direccion
                    sesion["estado"] = S_COLECTIVO_PAGO
                    await enviar_mensaje(numero,
                        f"✅ Recojo: *{direccion}*\n\n"
                        "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
                    return
                datos.pop("_sugerencias", None)
            # Buscar con Autocomplete
            await resolver_direccion(texto, sesion, datos, numero,
                                     "col_recojo_temp", "_col_recojo_coords",
                                     S_CONFIRM_COL_RECOJO, "colectivo_recojo")
        else:
            await enviar_mensaje(numero, "Comparte tu ubicación o escribe tu dirección.")

    elif estado == S_CONFIRM_COL_RECOJO:
        if texto == "1":
            datos["colectivo_recojo"] = datos.pop("col_recojo_temp")
            sesion["estado"] = S_COLECTIVO_PAGO
            await enviar_mensaje(numero,
                f"✅ Recojo: *{datos['colectivo_recojo']}*\n\n"
                "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
        elif texto == "2":
            datos.pop("col_recojo_temp", None)
            sesion["estado"] = S_COLECTIVO_RECOJO  # volver
            await enviar_mensaje(numero,
                "📍 *Escribe tu dirección de recojo:*\n"
                "_(Ej: Parque Guadalupe, Jr. Lima 234, Barrio El Molino)_")
        else:
            # Escribió dirección directo → buscar
            datos.pop("col_recojo_temp", None)
            sesion["estado"] = S_COLECTIVO_RECOJO
            await resolver_direccion(texto, sesion, datos, numero,
                                     "col_recojo_temp", "_col_recojo_coords",
                                     S_CONFIRM_COL_RECOJO, "colectivo_recojo")

    elif estado == S_COLECTIVO_PAGO:
        if texto == "1": datos["colectivo_pago"] = "Efectivo 💵"
        elif texto == "2": datos["colectivo_pago"] = "Yape 📱"
        else:
            await enviar_mensaje(numero, "Responde *1* Efectivo o *2* Yape.")
            return
        sesion["estado"] = S_COLECTIVO_CONFIRMAR
        await enviar_mensaje(numero,
            f"🚌 *Confirma tu colectivo:*\n\n"
            f"👤 {datos['nombre']}\n"
            f"{datos['colectivo_emoji']} Ruta: {datos['colectivo_ruta']}\n"
            f"🕐 Horario: {datos['colectivo_horario']}\n"
            f"👥 Asientos: {datos['colectivo_asientos']}\n"
            f"📍 Recojo: {datos['colectivo_recojo']}\n"
            f"💰 Total: S/{datos['colectivo_total']:.2f}\n"
            f"💳 {datos['colectivo_pago']}\n\n"
            "1️⃣ *CONFIRMAR* ✅\n2️⃣ *CANCELAR* ❌" + NAV)

    elif estado == S_COLECTIVO_CONFIRMAR:
        if texto == "1":
            # Notificar conductores
            if GRUPO_CONDUCTORES:
                msg_cond = (
                    f"🚌 *COLECTIVO SOLICITADO*\n\n"
                    f"👤 {datos['nombre']} | 📱 +{numero}\n"
                    f"{datos['colectivo_emoji']} {datos['colectivo_ruta']}\n"
                    f"🕐 {datos['colectivo_horario']}\n"
                    f"👥 {datos['colectivo_asientos']} asiento(s)\n"
                    f"📍 {datos['colectivo_recojo']}\n"
                    f"💰 S/{datos['colectivo_total']:.2f} | 💳 {datos['colectivo_pago']}\n\n"
                    f"Responde *ACEPTO COLECTIVO* para tomar el servicio"
                )
                await enviar_mensaje(GRUPO_CONDUCTORES, msg_cond)
            guardar_viaje(numero, {
                "destino_texto": datos.get("colectivo_ruta"),
                "tarifa": datos.get("colectivo_total"),
                "pago": datos.get("colectivo_pago")
            }, "colectivo")
            datos_servicio = {
                "tipo": "colectivo",
                "destino": datos.get("colectivo_ruta"),
                "conductor": "Pendiente"
            }
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                f"🎉 *¡Colectivo reservado!*\n\n"
                f"Salida programada: *{datos.get('colectivo_horario')}*\n"
                f"El conductor te contactará para confirmar el recojo.\n\n"
                f"📌 *Recuerda:* el colectivo sale cuando se completan "
                f"los {COLECTIVO_MAX_ASIENTOS} asientos.\n\n"
                f"━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir")
            asyncio.create_task(programar_calificacion(numero, datos_servicio))
        elif texto == "2":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, "❌ Cancelado.\n\nEscribe *1* cuando quieras solicitar otro servicio.\n0️⃣ Salir")
        else:
            await enviar_mensaje(numero, "Responde *1* confirmar o *2* cancelar.")

    # ══ ENCOMIENDA ════════════════════════════════════════════════════════════
    elif estado == S_ENCOMIENDA_DESC:
        if len(texto) < 3:
            await enviar_mensaje(numero, "Por favor describe qué vas a enviar.")
            return
        datos["enc_descripcion"] = texto
        sesion["estado"] = S_ENCOMIENDA_BULTOS
        await enviar_mensaje(numero,
            f"📦 *{texto}*\n\n"
            "🔢 *¿Cuántos paquetes vas a enviar?*\n\n"
            "1️⃣ Solo 1 paquete\n"
            "2️⃣ 2 paquetes\n"
            "3️⃣ 3 paquetes\n"
            "4️⃣ 4 o más paquetes")

    elif estado == S_ENCOMIENDA_BULTOS:
        paquetes_map = {"1": 1, "2": 2, "3": 3, "4": 4}
        if texto not in paquetes_map:
            await enviar_mensaje(numero, "Responde del *1* al *4*.")
            return
        datos["enc_paquetes"] = paquetes_map[texto]
        sesion["estado"] = S_ENCOMIENDA_TAMANO
        await enviar_mensaje(numero,
            f"✅ *{datos['enc_paquetes']} paquete(s)*\n\n"
            "📐 *¿Cuál es el paquete más grande?*\n\n"
            "1️⃣ Sobre / Documento — S/3\n"
            "2️⃣ Paquete pequeño _(hasta 2kg)_ — S/5\n"
            "3️⃣ Paquete mediano _(2-10kg)_ — S/8\n"
            "4️⃣ Paquete grande _(10-30kg)_ — S/12\n"
            "5️⃣ Carga pesada _(+30kg)_ — A coordinar")

    elif estado == S_ENCOMIENDA_TAMANO:
        # Precio = equivalente a N pasajeros en colectivo
        # Conductor puede ajustar en mediano/grande/pesado
        tamanos = {
            "1": ("Sobre/Documento", 1, False),   # 1 pasajero, precio fijo
            "2": ("Paquete pequeño",  1, False),   # 1 pasajero, precio fijo
            "3": ("Paquete mediano",  2, True),    # 2 pasajeros, conductor confirma
            "4": ("Paquete grande",   3, True),    # 3 pasajeros, conductor confirma
            "5": ("Carga pesada",     4, True),    # vehículo completo, conductor confirma
        }
        if texto not in tamanos:
            await enviar_mensaje(numero, "Responde del *1* al *5*.")
            return
        nombre_tam, equiv_pasajeros, requiere_confirmacion = tamanos[texto]
        datos["enc_tamano"] = nombre_tam
        datos["enc_equiv_pasajeros"] = equiv_pasajeros
        datos["enc_requiere_confirmacion"] = requiere_confirmacion
        datos["enc_tarifa_base"] = None  # se calcula al conocer la ruta
        sesion["estado"] = S_ENCOMIENDA_FOTO
        await enviar_mensaje(numero,
            f"✅ *{nombre_tam}*\n\n"
            "📸 *Envía una foto de tu encomienda*\n"
            "_(Para que el conductor sepa qué va a transportar)_\n\n"
            "O escribe *omitir* si no tienes foto ahora.")

    elif estado == S_ENCOMIENDA_FOTO:
        # Recibir foto o saltar
        if tipo == "image":
            media_id = contenido.get("id", "")
            datos["enc_foto_id"] = media_id
            datos["enc_foto"] = True
        elif texto.lower() == "omitir" or texto:
            datos["enc_foto"] = False
        sesion["estado"] = S_ENCOMIENDA_URGENCIA
        await enviar_mensaje(numero,
            "⏰ *¿Cuándo necesitas que llegue?*\n\n"
            "1️⃣ Urgente — ahora mismo 🚀 _(+S/2)_\n"
            "2️⃣ Hoy en el día 📅\n"
            "3️⃣ Programar fecha y hora 🗓️")
        await enviar_mensaje(numero,
            f"✅ *{nombre_tam}*\n\n"
            "⏰ *¿Cuándo necesitas que llegue?*\n\n"
            "1️⃣ Urgente — ahora mismo 🚀 _(+S/2)_\n"
            "2️⃣ Hoy en el día 📅\n"
            "3️⃣ Programar fecha y hora 🗓️")

    elif estado == S_ENCOMIENDA_URGENCIA:
        if texto == "1":
            datos["enc_urgencia"] = "Urgente 🚀"
            datos["enc_recargo"] = 2.0
            sesion["estado"] = S_ENCOMIENDA_ORIGEN
            await enviar_mensaje(numero,
                "🚀 *Envío urgente*\n\n"
                "📍 *¿Desde dónde recogemos la encomienda?*\n\n"
                "• 📌 Comparte tu ubicación\n"
                "• ✍️ O escribe la dirección")
        elif texto == "2":
            datos["enc_urgencia"] = "Hoy en el día 📅"
            datos["enc_recargo"] = 0.0
            sesion["estado"] = S_ENCOMIENDA_ORIGEN
            await enviar_mensaje(numero,
                "📅 *Envío hoy en el día*\n\n"
                "📍 *¿Desde dónde recogemos la encomienda?*\n\n"
                "• 📌 Comparte tu ubicación\n"
                "• ✍️ O escribe la dirección")
        elif texto == "3":
            datos["enc_urgencia"] = "Programado 🗓️"
            datos["enc_recargo"] = 0.0
            sesion["estado"] = S_ENCOMIENDA_PROGRAMAR
            await enviar_mensaje(numero,
                "🗓️ *¿Para qué fecha y hora?*\n\n"
                "_(Ej: Mañana 3pm / Sábado 10:00)_")
        else:
            await enviar_mensaje(numero, "Responde *1*, *2* o *3*.")

    elif estado == S_ENCOMIENDA_PROGRAMAR:
        if len(texto) < 3:
            await enviar_mensaje(numero, "Indica la fecha y hora. Ej: Mañana 3pm")
            return
        datos["enc_urgencia"] = f"Programado: {texto} 🗓️"
        datos["enc_recargo"] = 0.0
        sesion["estado"] = S_ENCOMIENDA_ORIGEN
        await enviar_mensaje(numero,
            f"✅ *Programado: {texto}*\n\n"
            "📍 *¿Desde dónde recogemos la encomienda?*\n\n"
            "• 📌 Comparte tu ubicación\n"
            "• ✍️ O escribe la dirección")

    elif estado == S_ENCOMIENDA_ORIGEN:
        if lat and lng:
            direccion_gps = await coords_a_direccion(lat, lng)
            if not direccion_gps:
                await enviar_mensaje(numero,
                    "📌 Recibí tu ubicación GPS pero no pude identificar la dirección.\n\n"
                    "✍️ Escribe el nombre del lugar o dirección:")
            else:
                datos["enc_origen"] = direccion_gps
                sesion["estado"] = S_ENCOMIENDA_DESTINO
                await enviar_mensaje(numero,
                    f"✅ Recojo: *{direccion_gps}*\n\n"
                    "🏁 *¿A qué dirección lo enviamos?*\n\n"
                    "• 📌 Comparte ubicación del destino\n"
                    "• ✍️ O escribe la dirección")
        elif texto:
            if "_sugerencias" in datos and texto in ["1","2","3","4"]:
                idx = int(texto) - 1
                sugs = datos["_sugerencias"]
                if idx < len(sugs):
                    sug = sugs[idx]
                    direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
                    datos.pop("_sugerencias", None)
                    datos["enc_origen"] = direccion
                    sesion["estado"] = S_ENCOMIENDA_DESTINO
                    await enviar_mensaje(numero,
                        f"✅ Recojo: *{direccion}*\n\n"
                        "🏁 *¿A qué dirección lo enviamos?*\n\n"
                        "• 📌 Comparte ubicación del destino\n"
                        "• ✍️ O escribe la dirección")
                    return
                datos.pop("_sugerencias", None)
            sugerencias = await buscar_lugares_barranca(texto)
            if not sugerencias:
                await enviar_mensaje(numero, MSG_NO_ENCONTRADO)
            elif len(sugerencias) == 1:
                sug = sugerencias[0]
                direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
                datos["enc_origen"] = direccion
                sesion["estado"] = S_ENCOMIENDA_DESTINO
                await enviar_mensaje(numero,
                    f"✅ Recojo: *{direccion}*\n\n"
                    "🏁 *¿A qué dirección lo enviamos?*\n\n"
                    "• 📌 Comparte ubicación del destino\n"
                    "• ✍️ O escribe la dirección")
            else:
                numeros = ["1️⃣","2️⃣","3️⃣","4️⃣"]
                opciones = "\n".join([f"{numeros[i]} {s['nombre'].split(',')[0]}" for i,s in enumerate(sugerencias)])
                datos["_sugerencias"] = sugerencias
                await enviar_mensaje(numero, f"📍 ¿Cuál de estas?\n\n{opciones}\n\n_(O escribe otra)_")
        else:
            await enviar_mensaje(numero, "Comparte tu ubicación o escribe la dirección de recojo.")

    elif estado == S_ENCOMIENDA_DESTINO:
        if lat and lng:
            datos["enc_destino_temp"] = await coords_a_direccion(lat, lng)
            sesion["estado"] = S_ENCOMIENDA_CONFIRM_DEST
            await enviar_mensaje(numero,
                f"📍 Encontré: *{datos['enc_destino_temp']}*\n\n"
                "¿Es correcto?\n"
                "1️⃣ Sí\n"
                "2️⃣ No, escribir otra dirección")
        elif texto:
            if "_sugerencias" in datos and texto in ["1","2","3","4"]:
                idx = int(texto) - 1
                sugs = datos["_sugerencias"]
                if idx < len(sugs):
                    sug = sugs[idx]
                    direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
                    datos.pop("_sugerencias", None)
                    datos["enc_destino"] = direccion
                    sesion["estado"] = S_ENCOMIENDA_DESTINATARIO
                    await enviar_mensaje(numero,
                        f"✅ Destino: *{direccion}*\n\n"
                        "👤 *¿Nombre y teléfono de quien recibe?*\n"
                        "_(Ej: María López / 987654321)_")
                    return
                datos.pop("_sugerencias", None)
            sugerencias = await buscar_lugares_peru(texto)
            if not sugerencias:
                await enviar_mensaje(numero,
                    "❌ No encontré esa dirección.\n\n"
                    "Intenta con más detalle:\n"
                    "_(Ej: Panteón Chino Paramonga, Av. Lima Huacho)_")
            elif len(sugerencias) == 1:
                sug = sugerencias[0]
                direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
                datos["enc_destino_temp"] = direccion
                sesion["estado"] = S_ENCOMIENDA_CONFIRM_DEST
                await enviar_mensaje(numero,
                    f"📍 Encontré: *{direccion}*\n\n"
                    "¿Es correcto?\n"
                    "1️⃣ Sí\n"
                    "2️⃣ No, escribir otra dirección")
            else:
                numeros = ["1️⃣","2️⃣","3️⃣","4️⃣"]
                opciones = "\n".join([f"{numeros[i]} {s['nombre']}" for i,s in enumerate(sugerencias)])
                datos["_sugerencias"] = sugerencias
                await enviar_mensaje(numero, f"📍 ¿Cuál de estas?\n\n{opciones}\n\n_(O escribe otra dirección)_")
        else:
            await enviar_mensaje(numero, "Comparte ubicación o escribe la dirección de destino.")

    elif estado == S_ENCOMIENDA_CONFIRM_DEST:
        if texto == "1":
            datos["enc_destino"] = datos.pop("enc_destino_temp", "")
            sesion["estado"] = S_ENCOMIENDA_DESTINATARIO
            await enviar_mensaje(numero,
                f"✅ Destino: *{datos['enc_destino']}*\n\n"
                "👤 *¿Nombre y teléfono de quien recibe?*\n"
                "_(Ej: María López / 987654321)_")
        elif texto == "2":
            datos.pop("enc_destino_temp", None)
            sesion["estado"] = S_ENCOMIENDA_DESTINO
            await enviar_mensaje(numero,
                "🏁 *Escribe el destino nuevamente:*\n"
                "_(Sé más específico, ej: Panteón Chino Paramonga, Jr. Lima 234 Huacho)_")
        else:
            # Escribió dirección directo → buscar de nuevo
            datos.pop("enc_destino_temp", None)
            sesion["estado"] = S_ENCOMIENDA_DESTINO
            sugerencias = await buscar_lugares_peru(texto)
            if not sugerencias:
                await enviar_mensaje(numero,
                    "❌ No encontré esa dirección.\n\n"
                    "_(Ej: Panteón Chino Paramonga, Av. Lima Huacho)_")
            elif len(sugerencias) == 1:
                sug = sugerencias[0]
                direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
                datos["enc_destino_temp"] = direccion
                sesion["estado"] = S_ENCOMIENDA_CONFIRM_DEST
                await enviar_mensaje(numero,
                    f"📍 Encontré: *{direccion}*\n\n"
                    "¿Es correcto?\n1️⃣ Sí\n2️⃣ No, escribir otra")
            else:
                numeros = ["1️⃣","2️⃣","3️⃣","4️⃣"]
                opciones = "\n".join([f"{numeros[i]} {s['nombre']}" for i,s in enumerate(sugerencias)])
                datos["_sugerencias"] = sugerencias
                await enviar_mensaje(numero, f"📍 ¿Cuál de estas?\n\n{opciones}\n\n_(O escribe otra dirección)_")

    elif estado == S_ENCOMIENDA_DESTINATARIO:
        if len(texto) < 3:
            await enviar_mensaje(numero, "Indica nombre y teléfono del destinatario.")
            return
        datos["enc_destinatario"] = texto
        sesion["estado"] = S_ENCOMIENDA_PAGO
        recargo_urgencia = datos.get("enc_recargo", 0)
        # Tarifa siempre a coordinar — conductor la propone al ver el paquete
        datos["enc_tarifa_final"] = None
        if recargo_urgencia > 0:
            tarifa_txt = f"A coordinar + S/{recargo_urgencia:.0f} urgente"
        else:
            tarifa_txt = "A coordinar con conductor"
        detalle = "_(el conductor propone el precio al aceptar)_"
        await enviar_mensaje(numero,
            f"✅ Destinatario: *{texto}*\n"
            f"💰 Tarifa: *{tarifa_txt}*\n{detalle}\n\n"
            "💳 *¿Quién paga?*\n"
            "1️⃣ Yo pago ahora (Efectivo)\n"
            "2️⃣ Yo pago ahora (Yape)\n"
            "3️⃣ Paga el destinatario al recibir 🚪" + NAV)

    elif estado == S_ENCOMIENDA_PAGO:
        if texto == "1": datos["pago"] = "Efectivo 💵"
        elif texto == "2": datos["pago"] = "Yape 📱"
        elif texto == "3": datos["pago"] = "Contra entrega 🚪"
        else:
            await enviar_mensaje(numero, "Responde *1*, *2* o *3*.")
            return
        tarifa_txt = f"S/{datos['enc_tarifa_final']}" if datos.get("enc_tarifa_final") else "A coordinar"
        foto_txt = "✅ Con foto" if datos.get("enc_foto") else "Sin foto"
        paquetes = datos.get("enc_paquetes", 1)
        sesion["estado"] = S_ENCOMIENDA_CONFIRMAR
        await enviar_mensaje(numero,
            f"📦 *Confirma tu encomienda:*\n\n"
            f"👤 Remitente: {datos['nombre']}\n"
            f"📦 {datos['enc_descripcion']} — {datos['enc_tamano']}\n"
            f"🔢 {paquetes} paquete(s) | 📸 {foto_txt}\n"
            f"⏰ {datos['enc_urgencia']}\n"
            f"📍 Recojo: {datos['enc_origen']}\n"
            f"🏁 Destino: {datos['enc_destino']}\n"
            f"👤 Destinatario: {datos['enc_destinatario']}\n"
            f"💰 {tarifa_txt}\n"
            f"💳 {datos['pago']}\n\n"
            "1️⃣ *CONFIRMAR* ✅\n2️⃣ *CANCELAR* ❌" + NAV)

    elif estado == S_ENCOMIENDA_CONFIRMAR:
        if texto == "1":
            await notificar_conductores(sesion, numero, "ENCOMIENDA")
            guardar_viaje(numero, datos, "encomienda")
            datos_servicio = {"tipo": "encomienda", "destino": datos.get("enc_destino", "destino"), "conductor": "Pendiente"}
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                "🎉 *¡Encomienda registrada!*\n\nUn conductor te contactará pronto.\n\n━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir")
            asyncio.create_task(programar_calificacion(numero, datos_servicio))
        elif texto == "2":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, "❌ Cancelado.\n\n━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir")
        else:
            await enviar_mensaje(numero, "Responde *1* confirmar o *2* cancelar.")

    # ══ TURISMO ═══════════════════════════════════════════════════════════════
    elif estado == S_TURISMO_DESTINO:
        rutas = {
            "1": {"nombre": "Fortaleza de Paramonga", "emoji": "🏛️", "precio_ref": 70,  "duracion": "3-4h",    "nota": ""},
            "2": {"nombre": "Playas de Barranca",     "emoji": "🏖️", "precio_ref": 50,  "duracion": "2-3h",    "nota": ""},
            "3": {"nombre": "Ciudad Sagrada de Caral","emoji": "🏺", "precio_ref": 120, "duracion": "5-6h",    "nota": "caral"},
            "4": {"nombre": "Tour Huacho",             "emoji": "🏙️", "precio_ref": 100, "duracion": "4-5h",    "nota": ""},
            "5": {"nombre": "Tour Caral + Supe Pueblo","emoji": "⭐", "precio_ref": 180, "duracion": "día completo", "nota": "combinado"},
            "6": {"nombre": "Destino personalizado",   "emoji": "🗺️", "precio_ref": None,"duracion": "variable","nota": "custom"},
        }
        if texto not in rutas:
            await enviar_mensaje(numero, MSG_TURISMO_OPCIONES)
            return
        ruta = rutas[texto]
        datos.update({
            "ruta_nombre": ruta["nombre"],
            "ruta_emoji": ruta["emoji"],
            "ruta_precio_ref": ruta["precio_ref"],
            "ruta_duracion": ruta["duracion"],
            "ruta_nota": ruta["nota"],
        })
        # Enviar video turístico del destino
        video_info = VIDEOS_TURISMO.get(texto)
        if video_info:
            titulo, url = video_info
            await enviar_mensaje(numero,
                f"🎬 *Mira este video antes de tu tour:*\n\n"
                f"{titulo}\n"
                f"{url}\n\n"
                f"_¡Te va a encantar lo que te espera!_ ✨")

        # Caral tiene opción especial
        if ruta["nota"] == "caral":
            sesion["estado"] = S_TURISMO_CARAL
            await enviar_mensaje(numero,
                "🏺 *Ciudad Sagrada de Caral*\n\n"
                "⚠️ *Aviso importante:* el río está cortado actualmente.\n\n"
                "¿Qué opción prefieres?\n\n"
                "1️⃣ Hasta el pueblo — *S/120 referencial*\n"
                "   _(Moto a ruinas: S/40 extra, se paga allá)_\n\n"
                "2️⃣ Hasta la boletería — *S/140 referencial*\n"
                "   _(Conductor te lleva más cerca)_")
        elif ruta["nota"] == "custom":
            sesion["estado"] = S_TURISMO_PERSONAS
            await enviar_mensaje(numero,
                "🗺️ *Destino personalizado*\n\n"
                "¿A dónde quieren ir?\n"
                "_(Escribe el destino)_")
        else:
            sesion["estado"] = S_TURISMO_MODALIDAD
            precio_txt = f"desde S/{ruta['precio_ref']}" if ruta["precio_ref"] else "a coordinar"
            await enviar_mensaje(numero,
                f"{ruta['emoji']} *{ruta['nombre']}*\n"
                f"⏱️ {ruta['duracion']} | 💰 {precio_txt}\n\n"
                "🔄 *¿Cómo será el viaje?*\n\n"
                "1️⃣ Solo ida\n"
                "2️⃣ Ida y vuelta ✅ _(recomendado)_")

    elif estado == S_TURISMO_CARAL:
        if texto == "1":
            datos["ruta_opcion"] = "Hasta el pueblo"
            datos["ruta_precio_ref"] = 120
        elif texto == "2":
            datos["ruta_opcion"] = "Hasta la boletería"
            datos["ruta_precio_ref"] = 140
        else:
            await enviar_mensaje(numero, "Responde *1* o *2*.")
            return
        sesion["estado"] = S_TURISMO_MODALIDAD
        await enviar_mensaje(numero,
            f"✅ *{datos['ruta_opcion']}* — S/{datos['ruta_precio_ref']} referencial\n\n"
            "🔄 *¿Cómo será el viaje?*\n\n"
            "1️⃣ Solo ida\n"
            "2️⃣ Ida y vuelta ✅ _(recomendado)_")

    elif estado == S_TURISMO_MODALIDAD:
        if texto == "1":
            datos["modalidad"] = "Solo ida 🚗"
            datos["precio_final_ref"] = round((datos.get("ruta_precio_ref") or 0) * 0.6)
        elif texto == "2":
            datos["modalidad"] = "Ida y vuelta 🔄"
            datos["precio_final_ref"] = datos.get("ruta_precio_ref") or 0
        else:
            await enviar_mensaje(numero, "Responde *1* o *2*.")
            return
        sesion["estado"] = S_TURISMO_PERSONAS
        await enviar_mensaje(numero,
            f"✅ *{datos['modalidad']}*\n\n"
            "👥 *¿Cuántas personas van?*\n"
            "_(hasta 4 en auto — más de 4 consultar van)_")

    elif estado == S_TURISMO_PERSONAS:
        # Destino personalizado puede llegar aquí con texto del destino
        if datos.get("ruta_nota") == "custom" and not texto.isdigit():
            datos["ruta_nombre"] = texto.title()
            await enviar_mensaje(numero,
                f"🗺️ *{datos['ruta_nombre']}*\n\n"
                "🔄 *¿Cómo será el viaje?*\n\n"
                "1️⃣ Solo ida\n"
                "2️⃣ Ida y vuelta ✅")
            sesion["estado"] = S_TURISMO_MODALIDAD
            return
        if not texto.isdigit() or int(texto) < 1:
            await enviar_mensaje(numero, "Indica el número de personas (ej: 3)")
            return
        personas = int(texto)
        datos["personas"] = personas
        if personas > 4:
            await enviar_mensaje(numero,
                f"👥 *{personas} personas*\n\n"
                "⚠️ Para grupos de 5+ personas se requiere van o minibús.\n"
                "El conductor confirmará disponibilidad y precio.\n\n"
                "¿Deseas continuar?\n1️⃣ Sí, continuar\n2️⃣ No, cancelar")
        sesion["estado"] = S_TURISMO_TIPO_GRUPO
        if personas <= 4:
            await enviar_mensaje(numero,
                f"✅ *{personas} persona(s)*\n\n"
                "👨‍👩‍👧 *¿Tipo de grupo?*\n\n"
                "1️⃣ Familia con niños 👨‍👩‍👧\n"
                "2️⃣ Pareja / adultos 👫\n"
                "3️⃣ Adultos mayores 👴\n"
                "4️⃣ Amigos / jóvenes 🧑‍🤝‍🧑")

    elif estado == S_TURISMO_TIPO_GRUPO:
        if texto == "1": datos["tipo_grupo"] = "Familia con niños 👨‍👩‍👧"
        elif texto == "2": datos["tipo_grupo"] = "Pareja/adultos 👫"
        elif texto == "3": datos["tipo_grupo"] = "Adultos mayores 👴"
        elif texto == "4": datos["tipo_grupo"] = "Amigos/jóvenes 🧑‍🤝‍🧑"
        else:
            await enviar_mensaje(numero, "Responde del *1* al *4*.")
            return
        sesion["estado"] = S_TURISMO_CUANDO
        await enviar_mensaje(numero,
            f"✅ *{datos['tipo_grupo']}*\n\n"
            "📅 *¿Cuándo quieren ir?*\n\n"
            "1️⃣ Hoy mismo 🚀 _(+S/20 urgente)_\n"
            "2️⃣ Mañana 📅\n"
            "3️⃣ Elegir fecha 🗓️")

    elif estado == S_TURISMO_CUANDO:
        if texto == "1":
            datos["fecha_base"] = "Hoy mismo"
            datos["recargo_urgencia"] = 20
            sesion["estado"] = S_TURISMO_FECHA_PROG
            await enviar_mensaje(numero,
                "🚀 *Tour hoy mismo* _(+S/20)_\n\n"
                "🕐 *¿A qué hora los recogemos?*\n"
                "_(Ej: 9:00 am, 2:30 pm)_")
        elif texto == "2":
            datos["fecha_base"] = "Mañana"
            datos["recargo_urgencia"] = 0
            sesion["estado"] = S_TURISMO_FECHA_PROG
            await enviar_mensaje(numero,
                "📅 *Tour mañana*\n\n"
                "🕐 *¿A qué hora los recogemos?*\n"
                "_(Ej: 8:00 am, 9:30 am)_")
        elif texto == "3":
            datos["recargo_urgencia"] = 0
            sesion["estado"] = S_TURISMO_FECHA_PROG
            await enviar_mensaje(numero,
                "🗓️ *¿Para qué fecha y hora?*\n"
                "_(Ej: Sábado 14 de mayo, 8:00 am)_")
        else:
            await enviar_mensaje(numero, "Responde *1*, *2* o *3*.")

    elif estado == S_TURISMO_FECHA_PROG:
        import re
        tiene_hora = bool(re.search(r'(\d{1,2}:\d{2}|\d{1,2}\s*(am|pm|a\.m|p\.m))', texto.lower()))
        fecha_base = datos.get("fecha_base", "")

        if fecha_base:
            # Hoy/Mañana — solo necesitan la hora
            if not tiene_hora:
                await enviar_mensaje(numero,
                    "🕐 Indica la hora. _(Ej: 8:00 am, 2:30 pm)_")
                return
            datos["fecha"] = f"{fecha_base}, {texto}"
            datos.pop("fecha_base", None)
        else:
            # Elegir fecha libre
            if len(texto) < 3:
                await enviar_mensaje(numero,
                    "Indica fecha y hora.\n_(Ej: Viernes 15 mayo, 8:00 am)_")
                return
            if not tiene_hora:
                await enviar_mensaje(numero,
                    f"✅ Fecha: *{texto}*\n\n"
                    "🕐 *¿A qué hora?*\n_(Ej: 8:00 am, 9:30 am, 2:00 pm)_")
                datos["fecha_sin_hora"] = texto
                return
            if datos.get("fecha_sin_hora"):
                datos["fecha"] = f"{datos.pop('fecha_sin_hora')}, {texto}"
            else:
                datos["fecha"] = texto

        sesion["estado"] = S_TURISMO_RECOJO
        await enviar_mensaje(numero,
            f"✅ *{datos['fecha']}*\n\n"
            "📍 *¿Desde dónde los recogemos?*\n\n"
            "• 📌 Comparte tu ubicación\n"
            "• ✍️ O escribe la dirección" + NAV)

    elif estado == S_TURISMO_RECOJO:
        # Confirmación de resultado único
        if datos.get("_esperando_confirm_recojo"):
            if texto == "1":
                datos["recojo_texto"] = datos.pop("recojo_temp")
                datos.pop("_esperando_confirm_recojo", None)
                sesion["estado"] = S_TURISMO_PAGO
                await _turismo_pago(numero, datos)
            elif texto == "2":
                datos.pop("recojo_temp", None)
                datos.pop("_esperando_confirm_recojo", None)
                await enviar_mensaje(numero,
                    "📍 *Escribe el punto de recojo:*\n"
                    "_(Ej: Urb. Los Jardines Barranca, Jr. Lima 234)_")
            else:
                await enviar_mensaje(numero, "Responde *1* Sí o *2* No.")
            return
        if lat and lng:
            dir_gps = await coords_a_direccion(lat, lng)
            if not dir_gps:
                await enviar_mensaje(numero,
                    "📌 No pude identificar tu dirección GPS.\n✍️ Escribe el nombre del lugar:")
                return
            datos["recojo_texto"] = dir_gps
        elif texto:
            if "_sugerencias" in datos and texto in ["1","2","3","4"]:
                idx = int(texto) - 1
                sugs = datos["_sugerencias"]
                if idx < len(sugs):
                    sug = sugs[idx]
                    direccion, _ = await coords_de_place_id(sug["place_id"], sug["nombre"])
                    datos.pop("_sugerencias", None)
                    datos["recojo_temp"] = direccion
                    datos["_esperando_confirm_recojo"] = True
                    await enviar_mensaje(numero,
                        f"📍 *{direccion}*\n\n"
                        "¿Es correcto?\n1️⃣ Sí\n2️⃣ No, escribir otra")
                    return
                datos.pop("_sugerencias", None)
            sugerencias = await buscar_lugares_barranca(texto)
            if not sugerencias:
                await enviar_mensaje(numero, MSG_NO_ENCONTRADO)
                return
            elif len(sugerencias) == 1:
                sug = sugerencias[0]
                direccion, _ = await coords_de_place_id(sug["place_id"], sug["nombre"])
                datos["recojo_temp"] = direccion
                await enviar_mensaje(numero,
                    f"📍 Encontré: *{direccion}*\n\n"
                    "¿Es correcto?\n1️⃣ Sí\n2️⃣ No, escribir otra")
                datos["_esperando_confirm_recojo"] = True
                return
            else:
                numeros = ["1️⃣","2️⃣","3️⃣","4️⃣"]
                opciones = "\n".join([f"{numeros[i]} {s['nombre'].split(',')[0]}" for i,s in enumerate(sugerencias)])
                datos["_sugerencias"] = sugerencias
                await enviar_mensaje(numero, f"📍 ¿Cuál de estas?\n\n{opciones}\n\n_(O escribe otra)_")
                return
        else:
            await enviar_mensaje(numero, "Comparte ubicación o escribe el punto de recojo.")
            return
        sesion["estado"] = S_TURISMO_PAGO
        await _turismo_pago(numero, datos)

    elif estado == S_TURISMO_PAGO:
        if texto == "1": datos["pago"] = "Efectivo 💵"
        elif texto == "2": datos["pago"] = "Yape 📱"
        else:
            await enviar_mensaje(numero, "Responde *1* Efectivo o *2* Yape.")
            return
        # Registro paso a paso
        personas = int(datos.get("personas", 1))
        datos["_turismo_pasajero_idx"] = 0
        datos["_turismo_paso"] = "dni"
        datos["turismo_pasajeros_lista"] = []
        datos["_turismo_nombre_temp"] = datos.get("nombre", "")
        sesion["estado"] = S_TURISMO_PASAJEROS
        await enviar_mensaje(numero,
            f"🔒 *Registro de pasajeros* ({personas} persona(s))\n\n"
            f"👤 Pasajero 1: *{datos.get('nombre','')}*\n"
            "🪪 *¿Cuál es tu número de DNI?*\n_(8 dígitos)_")
        return

    elif estado == S_TURISMO_PASAJEROS:
        txt_norm = texto.strip()
        personas = int(datos.get("personas", 1))
        idx = datos.get("_turismo_pasajero_idx", 0)
        paso = datos.get("_turismo_paso", "dni")
        lista = datos.get("turismo_pasajeros_lista", [])

        if txt_norm.lower() == "omitir":
            datos["turismo_dni_principal"] = lista[0]["dni"] if lista else "—"
            datos["turismo_pasajeros_extra"] = " | ".join(
                [f"{p['nombre']} / {p['dni']}" for p in lista[1:]]) if len(lista) > 1 else ""
        elif paso == "nombre":
            if len(txt_norm) < 3:
                await enviar_mensaje(numero, "✍️ Escribe el nombre completo del pasajero:")
                return
            datos["_turismo_nombre_temp"] = txt_norm
            datos["_turismo_paso"] = "dni"
            await enviar_mensaje(numero,
                f"👤 *{txt_norm}*\n"
                f"🪪 *DNI del pasajero {idx+1}:*\n_(8 dígitos)_")
            return
        elif paso == "dni":
            dni = txt_norm.replace(" ", "")
            if not dni.isdigit() or len(dni) < 6:
                await enviar_mensaje(numero, "❌ DNI inválido. Ingresa solo números _(mínimo 6 dígitos)_:")
                return
            nombre_temp = datos.get("_turismo_nombre_temp", "")
            lista.append({"nombre": nombre_temp, "dni": dni})
            datos["turismo_pasajeros_lista"] = lista
            siguiente = idx + 1
            if siguiente < personas:
                datos["_turismo_pasajero_idx"] = siguiente
                datos["_turismo_paso"] = "nombre"
                await enviar_mensaje(numero,
                    f"✅ Pasajero {idx+1} registrado.\n\n"
                    f"👤 *Nombre del pasajero {siguiente+1}:*")
                return
            else:
                datos["turismo_dni_principal"] = lista[0]["dni"] if lista else "—"
                datos["turismo_pasajeros_extra"] = " | ".join(
                    [f"{p['nombre']} / {p['dni']}" for p in lista[1:]]) if len(lista) > 1 else ""
        else:
            return

        # Ir a confirmar
        precio_ref = datos.get("ruta_precio_ref", 0)
        recargo = datos.get("recargo_urgencia", 0)
        precio_total = (datos.get("precio_final_ref") or precio_ref) + recargo
        nota_caral = ""
        if datos.get("ruta_nota") == "caral":
            nota_caral = "\n⚠️ _Moto a ruinas: S/40 extra (se paga allá)_"
        nota_negociacion = "\n\n💬 _Precio referencial — el conductor confirmará el precio final al contactarte_"
        sesion["estado"] = S_TURISMO_CONFIRMAR
        await enviar_mensaje(numero,
            f"🗺️ *Confirma tu tour:*\n\n"
            f"👤 {datos['nombre']} | DNI: {datos.get('turismo_dni_principal','—')}\n"
            f"{datos['ruta_emoji']} {datos['ruta_nombre']}\n"
            f"{datos.get('ruta_opcion', '')}\n"
            f"🔄 {datos.get('modalidad', 'Ida y vuelta')}\n"
            f"👥 {datos['personas']} persona(s) — {datos['tipo_grupo']}\n"
            + (f"👥 Otros: {datos['turismo_pasajeros_extra']}\n" if datos.get('turismo_pasajeros_extra') else "")
            + f"📅 {datos['fecha']}\n"
            f"📍 Recojo: {datos['recojo_texto']}\n"
            f"⏱️ Duración aprox: {datos['ruta_duracion']}\n"
            f"💰 Precio referencial: S/{precio_total}{nota_caral}\n"
            f"💳 {datos['pago']}"
            f"{nota_negociacion}\n\n"
            "1️⃣ *CONFIRMAR* ✅\n2️⃣ *CANCELAR* ❌" + NAV)

    elif estado == S_TURISMO_CONFIRMAR:
        if texto == "1":
            await notificar_conductores(sesion, numero, "TURISMO")
            guardar_viaje(numero, {
                "destino_texto": datos.get("ruta_nombre"),
                "tarifa": datos.get("ruta_precio_ref"),
                "pago": datos.get("pago")
            }, "turismo")
            datos_servicio = {"tipo": "turismo", "destino": datos.get("ruta_nombre", "destino"), "conductor": "Pendiente"}
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                "🎉 *¡Tour reservado!*\n\n"
                "Un conductor te contactará pronto para confirmar el precio final y los detalles.\n\n"
                "━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir")
            asyncio.create_task(programar_calificacion(numero, datos_servicio))
        elif texto == "2":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, "❌ Cancelado.\n\n━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir")
        else:
            await enviar_mensaje(numero, "Responde *1* confirmar o *2* cancelar.")

# ── Webhook ───────────────────────────────────────────────────────────────────
@app.get("/webhook")
async def verificar(request: Request):
    p = dict(request.query_params)
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(p.get("hub.challenge"))
    raise HTTPException(status_code=403)

@app.post("/webhook")
async def recibir(request: Request):
    try:
        body = await request.json()
        messages = body.get("entry",[{}])[0].get("changes",[{}])[0].get("value",{}).get("messages",[])
        if not messages:
            return {"status": "ok"}
        msg    = messages[0]
        numero = msg["from"]
        tipo   = msg.get("type")

        msg_age = time.time() - int(msg.get("timestamp", 0))
        if msg_age > 300:
            print(f"[SKIP] mensaje viejo {int(msg_age)}s - ignorando", flush=True)
            return {"status": "ok"}

        if tipo == "text":
            await procesar(numero, "text", msg.get("text", {}))
        elif tipo == "location":
            await procesar(numero, "location", msg.get("location", {}))
        elif tipo == "image":
            await procesar(numero, "image", msg.get("image", {}))
        else:
            await enviar_mensaje(numero, "Solo entiendo texto, ubicaciones e imágenes 😊\n\nEscribe *menu* para comenzar.")

        return {"status": "ok"}
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        return {"status": "error"}

@app.get("/tickets")
async def get_tickets():
    return {
        "tickets": sorted(tickets, key=lambda x: x["timestamp"], reverse=True),
        "total": len(tickets),
        "nuevos": sum(1 for t in tickets if t["estado"] == "nuevo"),
        "en_proceso": sum(1 for t in tickets if t["estado"] == "en_proceso"),
        "resueltos": sum(1 for t in tickets if t["estado"] == "resuelto"),
    }

@app.post("/tickets/{ticket_id}/estado")
async def update_ticket_estado(ticket_id: str, body: dict):
    from fastapi import Body
    for t in tickets:
        if t["id"] == ticket_id:
            t["estado"] = body.get("estado", t["estado"])
            t["respuesta"] = body.get("respuesta", t["respuesta"])
            if body.get("respuesta") and body.get("notificar", True):
                await enviar_mensaje(t["numero"],
                    f"📋 *Respuesta a tu ticket {ticket_id}*\n\n"
                    f"_{body['respuesta']}_\n\n"
                    f"— Equipo Barranca Móvil 🚖")
            return {"ok": True, "ticket": t}
    raise HTTPException(status_code=404, detail="Ticket no encontrado")

@app.get("/")
async def root():
    return {"status": "Barranca Movil Bot v5 activo 🚖"}
