import os
import json
import time
from datetime import datetime
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
ADMIN_KEY         = os.getenv("ADMIN_KEY", "cuervo2025")

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
    # Renovador desactivado: WHATSAPP_TOKEN debe venir desde Render Environment.
    # asyncio.create_task(renovar_token())
    asyncio.create_task(limpiar_sesiones())
    print("[BOT] Renovador de token DESACTIVADO - usando WHATSAPP_TOKEN de Render Environment", flush=True)
    print("[BOT] Limpiador de sesiones iniciado - cada 1h", flush=True)
    asyncio.create_task(programador_inicio_turno_conductores())
    print("[BOT] Programador inicio turno activo - 07:00 Lima / alerta 08:00 Lima", flush=True)

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
S_ENCOMIENDA_CONFIRM_AUTO = "ENCOMIENDA_CONFIRM_AUTO"
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

# ── Estados El Cuervo ─────────────────────────────────────────────────────────
S_TRANSPORTE_MENU    = "TRANSPORTE_MENU"   # Submenú Barranca Móvil

# Gastronomía
S_GASTRO_LISTA       = "GASTRO_LISTA"      # Lista de restaurantes

# Seguridad & Saneamiento
S_SEG_SUBCATEGORIA   = "SEG_SUBCATEGORIA"  # Elige servicio
S_SEG_DESCRIPCION    = "SEG_DESCRIPCION"   # Describe la necesidad
S_SEG_UBICACION      = "SEG_UBICACION"     # Dirección
S_SEG_URGENCIA       = "SEG_URGENCIA"      # Urgente o programado
S_SEG_PROGRAMAR      = "SEG_PROGRAMAR"     # Fecha y hora si programado
S_SEG_ESPERA_COT     = "SEG_ESPERA_COT"    # Esperando cotización de Marcos
S_SEG_CONFIRMAR_COT  = "SEG_CONFIRMAR_COT" # Cliente acepta o rechaza cotización
S_SEG_CALIFICAR      = "SEG_CALIFICAR"     # Calificación post servicio

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
    S_ENCOMIENDA_CONFIRM_AUTO: S_ENCOMIENDA_DESC,
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
    # El Cuervo
    S_TRANSPORTE_MENU:      S_MENU,
    S_GASTRO_LISTA:         S_MENU,
    S_SEG_SUBCATEGORIA:     S_MENU,
    S_SEG_DESCRIPCION:      S_SEG_SUBCATEGORIA,
    S_SEG_UBICACION:        S_SEG_DESCRIPCION,
    S_SEG_URGENCIA:         S_SEG_UBICACION,
    S_SEG_PROGRAMAR:        S_SEG_URGENCIA,
    S_SEG_ESPERA_COT:       S_SEG_URGENCIA,
    S_SEG_CONFIRMAR_COT:    S_SEG_ESPERA_COT,
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
    S_ENCOMIENDA_CONFIRM_AUTO: "📦 *Confirma la encomienda detectada*\n1️⃣ Sí, continuar\n2️⃣ Cambiar cantidad o tamaño",
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
    S_TURISMO_PASAJEROS:  "🔒 *Registro de pasajeros*\n\n¿Cuál es tu número de DNI? _(7-8 dígitos)_\nO escribe *omitir* para saltarlo.",
    # El Cuervo
    S_TRANSPORTE_MENU:    "🚖 *Elige tu servicio de transporte:*\n1️⃣ Taxi\n2️⃣ Colectivo compartido\n3️⃣ Envío de encomienda 📦\n4️⃣ Ruta turística 🗺️\n0️⃣ Volver",
    S_SEG_SUBCATEGORIA:   "🛡️ *¿Qué servicio necesitas?*\n1️⃣ Extintores (venta/recarga)\n2️⃣ Señalización de seguridad\n3️⃣ Fumigación / Control de plagas\n4️⃣ Capacitación y Defensa Civil\n5️⃣ Otro\n0️⃣ Volver",
    S_SEG_DESCRIPCION:    "📝 *Describe tu necesidad:*\n_(Escribe los detalles del servicio que requieres)_",
    S_SEG_UBICACION:      "📍 *¿Cuál es la dirección del servicio?*\n• Comparte tu ubicación 📌\n• O escribe la dirección",
    S_SEG_URGENCIA:       "⏰ *¿Con qué urgencia necesitas el servicio?*\n1️⃣ Urgente — lo antes posible\n2️⃣ Programar — elegir fecha y hora\n0️⃣ Volver",
}

sesiones: dict[str, dict] = {}
historial_ia: dict[str, list] = {}
calificaciones: list[dict] = []  # historial de ratings
tickets: list[dict] = []          # tickets de reclamos/sugerencias
_ticket_counter: int = 0          # contador de tickets
mensajes_procesados: set[str] = set()  # idempotencia básica de webhooks WhatsApp
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
conductores_estado: dict[str, bool] = {k: False for k in ["51992995140","51901258690","51900817214","51936882776","51940197110"]}

def telefono_sin_51(numero: str) -> str:
    n = str(numero or "").strip()
    return n[2:] if n.startswith("51") and len(n) == 11 else n


async def actualizar_estado_conductor_sheets(numero: str, estado: str):
    """
    Sincroniza el estado real del conductor con Google Sheets.
    """
    try:
        info = CONDUCTORES.get(numero, {})
        await sheets_evento("update_conductor", {
            "TELEFONO": telefono_sin_51(numero),
            "CONDUCTOR": info.get("nombre", ""),
            "PLACA": info.get("placa", ""),
            "ESTADO": estado
        })
    except Exception as e:
        print(f"[CONDUCTOR SHEETS ERROR] {numero} {estado}: {e}", flush=True)

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

TARIFA_MINIMA_TAXI_PROGRAMADO = 6.00


def aplicar_tarifa_minima_programada(datos: dict):
    """
    Para taxis programados, evita tarifas demasiado bajas.
    Regla: taxi programado urbano mínimo S/6.
    No aplica a colectivo, encomienda ni turismo.
    """
    if not isinstance(datos, dict):
        return

    servicio = str(datos.get("servicio", "") or datos.get("tipo_servicio", "")).upper()
    if servicio and servicio != "TAXI":
        return

    # Detectar si el servicio no es "ahora mismo"
    valores_programacion = [
        datos.get("horario"),
        datos.get("hora_programada"),
        datos.get("fecha_programada"),
        datos.get("programado"),
        datos.get("tipo_tiempo"),
        datos.get("reserva_tipo"),
    ]

    combinado = " ".join(str(x or "") for x in valores_programacion).lower()

    es_programado = False
    if datos.get("programado") is True:
        es_programado = True
    if datos.get("hora_programada") or datos.get("fecha_programada"):
        es_programado = True
    if "program" in combinado or "reserva" in combinado or "indicar hora" in combinado:
        es_programado = True
    if combinado and "ahora" not in combinado and "inmediato" not in combinado:
        # Si existe horario y no es "ahora", lo tratamos como programado.
        if datos.get("horario") or datos.get("tipo_tiempo"):
            es_programado = True

    if not es_programado:
        return

    try:
        tarifa = float(datos.get("tarifa") or 0)
    except Exception:
        return

    if 0 < tarifa < TARIFA_MINIMA_TAXI_PROGRAMADO:
        datos["tarifa_original"] = tarifa
        datos["tarifa"] = TARIFA_MINIMA_TAXI_PROGRAMADO
        aplicar_tarifa_minima_programada(datos)
        datos["tarifa_aviso"] = (
            f"📌 Tarifa mínima por servicio programado: S/{TARIFA_MINIMA_TAXI_PROGRAMADO:.2f}\n"
        )
        datos["observacion_tarifa"] = "Tarifa mínima por servicio programado"



PROMO_TOPE = 7.00
PROMO_CODIGO = "PROMO_PRIMER_SERVICIO_URBANO"


def texto_es_promo(texto: str) -> bool:
    t = (texto or "").lower().strip()
    claves = [
        "promo", "promocion", "promoción",
        "gratis", "servicio gratis", "viaje gratis",
        "primer servicio", "primer viaje",
        "facebook", "anuncio", "descuento"
    ]
    return any(c in t for c in claves)


def aplicar_promo_monto(datos: dict, monto: float, servicio: str) -> tuple[float, float, str]:
    """
    Aplica promo hasta S/7 si la sesión viene marcada con promo.
    Retorna: descuento, total_final, texto_promo
    """
    try:
        monto = float(monto or 0)
    except Exception:
        monto = 0.0

    if not datos.get("promo_activa"):
        return 0.0, monto, ""

    servicio = (servicio or "").upper()

    # Promo solo para servicios urbanos permitidos.
    if servicio not in ["TAXI", "COLECTIVO", "ENCOMIENDA"]:
        return 0.0, monto, ""

    descuento = min(PROMO_TOPE, monto)
    total_final = max(0.0, monto - descuento)

    datos["promo_codigo"] = PROMO_CODIGO
    datos["promo_descuento"] = descuento
    datos["promo_total_final"] = total_final

    if total_final <= 0:
        texto_promo = (
            f"\n🎁 *Promo aplicada:* -S/{descuento:.2f}\n"
            f"✅ *Total a pagar: S/0.00*\n"
        )
    else:
        texto_promo = (
            f"\n🎁 *Promo aplicada:* -S/{descuento:.2f}\n"
            f"💰 *Total con promo: S/{total_final:.2f}*\n"
        )

    return descuento, total_final, texto_promo



# ── Proveedores Seguridad & Saneamiento ──────────────────────────────────────
PROVEEDORES_SEG = {
    "51960459741": {
        "nombre":    "Marcos Espinoza",
        "negocio":   "SASI SAC",
        "servicios": ["extintores", "señalización", "fumigación", "capacitación", "defensa civil"],
        "horario":   {"inicio": 8, "fin": 18},   # 8am–6pm, flexible con clientes
        "cobertura": "Barranca y distritos, Huacho y distritos",
    },
}

# Solicitudes de seguridad pendientes de cotización {num_cliente: datos_solicitud}
solicitudes_seg_pendientes: dict[str, dict] = {}
# Cotizaciones enviadas por proveedor pendientes de respuesta cliente {num_cliente: datos_cotizacion}
cotizaciones_seg_pendientes: dict[str, dict] = {}

HORARIO_LIMA = "America/Lima"

def dentro_horario_seg() -> bool:
    """Verifica si estamos dentro del horario de Seguridad & Saneamiento (8am–6pm Lima)."""
    try:
        from datetime import datetime
        import zoneinfo
        ahora = datetime.now(zoneinfo.ZoneInfo(HORARIO_LIMA))
        return 8 <= ahora.hour < 18
    except Exception:
        return True  # Si falla, dejamos pasar

SEG_SUBCATEGORIAS = {
    "1": "Extintores (venta/recarga)",
    "2": "Señalización de seguridad",
    "3": "Fumigación / Control de plagas",
    "4": "Capacitación y Defensa Civil",
    "5": "Otro",
}

SYSTEM_PROMPT_IA = """Eres Elizabeth, asistente de *El Cuervo* 🦅 — red inteligente de servicios locales en Barranca, Perú.
Servicios: TRANSPORTE (taxi, colectivo, encomiendas, turismo), GASTRONOMÍA (restaurantes, cevicherías), SEGURIDAD & SANEAMIENTO (extintores, fumigación, señalización, defensa civil).
Responde en español amigable y natural, máximo 3 oraciones."""

MSG_BIENVENIDA = """👋 ¡Hola! Soy *Elizabeth*, tu asistente de *El Cuervo* 🦅
_Red inteligente de servicios locales en Barranca_

¿En qué te puedo ayudar hoy?

1️⃣ 🚖 Transporte
2️⃣ 🍽️ Gastronomía
3️⃣ 🛡️ Seguridad & Saneamiento
0️⃣ Salir

O escribe tu consulta libremente 💬"""

MSG_TRANSPORTE_MENU = """🚖 *Transporte — Barranca Móvil*

¿Qué servicio necesitas?

1️⃣ Taxi
2️⃣ Colectivo compartido con recojo a domicilio 🚌
3️⃣ Envío de encomienda 📦
4️⃣ Ruta turística 🗺️
0️⃣ Volver al menú principal

🎁 Promo de lanzamiento: *primer servicio puede salirte GRATIS*.
Escribe *promo* para consultar condiciones."""

MSG_GASTRO_PROXIMAMENTE = """🍽️ *Gastronomía — Próximamente*

Estamos registrando los mejores restaurantes, cevicherías, chifas y más de Barranca.

Muy pronto podrás pedir tu comida favorita sin salir de WhatsApp. 🙌

Escribe *menu* para volver al inicio."""

MSG_TARIFAS = """💰 *Tarifas Barranca Móvil*

🚖 *Taxi Urbano:* S/3.00 + S/1.20/km

🚌 *Colectivo compartido con recojo a domicilio:*
• Pativilca: S/4 | Paramonga: S/6
• Puerto Supe: S/4 | Supe Pueblo: S/5
• San Nicolás: S/6 | Huacho: S/10
• Lima: S/50
✅ *Incluye solicitud de recojo a domicilio*
_Salida sujeta a cupos disponibles o confirmación del conductor._

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
    """
    Envía mensaje por WhatsApp Cloud API.
    Además registra errores críticos para no dejar al bot fallando en silencio.
    """
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": texto}
    }

    destino_tipo = "CONDUCTOR" if "CONDUCTORES" in globals() and to in CONDUCTORES else "CLIENTE"
    if "OPERADOR_WA" in globals() and OPERADOR_WA and to == OPERADOR_WA:
        destino_tipo = "OPERADOR"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=payload)

        if r.status_code >= 400:
            error_txt = r.text[:500]
            print(
                f"[WA ERROR] status={r.status_code} destino={destino_tipo} to={to} error={error_txt}",
                flush=True
            )

            # Registrar alerta operativa en Google Sheets.
            # No usamos WhatsApp para avisar porque justamente WhatsApp puede estar fallando.
            try:
                prioridad = "CRITICA" if r.status_code in (401, 403) else "ALTA"
                descripcion = (
                    f"Error WhatsApp API al enviar mensaje. "
                    f"Status={r.status_code}. Destino={destino_tipo}. To={to}. "
                    f"Respuesta={error_txt}"
                )

                if "sheets_evento" in globals():
                    asyncio.create_task(sheets_evento("add_alerta", {
                        "id_servicio": f"WA-ERROR-{int(time.time())}",
                        "tipo_alerta": "WHATSAPP_API_ERROR",
                        "prioridad": prioridad,
                        "descripcion": descripcion,
                        "requiere_accion": "SI",
                        "estado_alerta": "ABIERTA",
                        "responsable": "Operador"
                    }))
            except Exception as e:
                print(f"[WA ALERT ERROR] No se pudo registrar alerta: {e}", flush=True)

            return False

        print(f"[WA] {r.status_code} destino={destino_tipo} to={to}", flush=True)
        return True

    except Exception as e:
        print(f"[WA EXCEPTION] destino={destino_tipo} to={to} error={e}", flush=True)

        try:
            if "sheets_evento" in globals():
                asyncio.create_task(sheets_evento("add_alerta", {
                    "id_servicio": f"WA-EXCEPTION-{int(time.time())}",
                    "tipo_alerta": "WHATSAPP_SEND_EXCEPTION",
                    "prioridad": "CRITICA",
                    "descripcion": f"Excepción enviando WhatsApp. Destino={destino_tipo}. To={to}. Error={e}",
                    "requiere_accion": "SI",
                    "estado_alerta": "ABIERTA",
                    "responsable": "Operador"
                }))
        except Exception as e2:
            print(f"[WA ALERT ERROR] No se pudo registrar excepción en Sheets: {e2}", flush=True)

        return False




async def enviar_template_inicio_turno(to: str):
    """
    Envía plantilla aprobada de WhatsApp para recordatorio de inicio de turno.
    Plantilla Meta: inicio_turno_conductor
    Idioma: Spanish (PER) => es_PE
    """
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": "inicio_turno_conductor",
            "language": {"code": "es_PE"}
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=payload)

        if r.status_code >= 400:
            print(f"[TEMPLATE ERROR] inicio_turno_conductor to={to} status={r.status_code} {r.text}", flush=True)
            return False

        print(f"[TEMPLATE] inicio_turno_conductor enviado to={to} status={r.status_code}", flush=True)
        return True

    except Exception as e:
        print(f"[TEMPLATE EXCEPTION] inicio_turno_conductor to={to} error={e}", flush=True)
        return False


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
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            print(f"[IMG ERROR] {r.status_code} {r.text}", flush=True)
        else:
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
            r = await client.post(webhook_url, json=payload, follow_redirects=True)
            print(f"[SHEETS] Registro turismo: {r.status_code}", flush=True)
    except Exception as e:
        print(f"[SHEETS ERROR] {e}", flush=True)



def generar_id_servicio(numero_cliente: str, tipo: str) -> str:
    sufijo = str(numero_cliente)[-4:]
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    prefijo = (tipo or "SRV")[:3].upper()
    return f"BM-{prefijo}-{sufijo}-{ts}"


async def _notificar_proveedor_seg(numero_cliente: str, datos: dict):
    """Notifica a Marcos Espinoza con los detalles de la solicitud de seg & saneamiento."""
    num_marcos = list(PROVEEDORES_SEG.keys())[0]
    nombre = datos.get("nombre", "Cliente")
    tel    = telefono_sin_51(numero_cliente)
    subcat = datos.get("seg_subcategoria", "")
    desc   = datos.get("seg_descripcion", "")
    ubic   = datos.get("seg_ubicacion", "")
    urgenc = datos.get("seg_urgencia", "URGENTE")
    fecha  = datos.get("seg_fecha_programada", "")

    solicitudes_seg_pendientes[numero_cliente] = datos.copy()

    msg = (
        f"🦅 *El Cuervo — Nueva Solicitud*\n\n"
        f"🛡️ *Seguridad & Saneamiento*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📋 Servicio: *{subcat}*\n"
        f"👤 Cliente: {nombre}\n"
        f"📱 Teléfono: +{tel}\n"
        f"📝 Descripción: {desc}\n"
        f"📍 Dirección: {ubic}\n"
        f"⏰ Urgencia: *{urgenc}*\n"
        f"{'📅 Fecha programada: ' + fecha + chr(10) if fecha else ''}"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"Para cotizar responde:\n"
        f"*COTIZO {tel} [monto] [descripción breve]*\n\n"
        f"Ejemplo: COTIZO {tel} 150 recarga 3 extintores PQS 6kg"
    )
    await enviar_mensaje(num_marcos, msg)
    # Notificar al cliente que se envió
    await enviar_mensaje(numero_cliente,
        f"✅ *¡Solicitud enviada!*\n\n"
        f"🛡️ *{subcat}*\n"
        f"📍 {ubic}\n\n"
        f"Nuestro especialista *Marcos Espinoza / SASI SAC* revisará tu solicitud "
        f"y te enviará una cotización en breve.\n\n"
        f"⏳ Tiempo estimado de respuesta: *15–30 minutos*\n\n"
        f"Escribe *menu* si necesitas otra cosa 🦅")




def armar_sheets_servicio(numero_cliente: str, tipo: str, d: dict, estado: str, conductor: dict | None = None) -> dict:
    """Arma una fila estándar para la pestaña SERVICIOS."""
    if not d.get("id_servicio"):
        d["id_servicio"] = generar_id_servicio(numero_cliente, tipo)

    origen = (
        d.get("recojo_texto")
        or d.get("colectivo_recojo")
        or d.get("enc_origen")
        or d.get("recojo")
        or ""
    )

    destino = (
        d.get("destino_texto")
        or d.get("colectivo_ruta")
        or d.get("enc_destino")
        or d.get("ruta_nombre")
        or ""
    )

    pago = (
        d.get("pago")
        or d.get("colectivo_pago")
        or ""
    )

    tarifa = (
        d.get("tarifa")
        or d.get("colectivo_total")
        or d.get("enc_tarifa_final")
        or d.get("ruta_precio_ref")
        or "A coordinar"
    )

    if tarifa is None:
        tarifa = "A coordinar"

    alerta = ""
    prioridad = "BAJA"

    cuidado = (d.get("enc_cuidado_extra") or "").lower()
    tamano = (d.get("enc_tamano") or "").lower()

    if "gas" in cuidado or "riesgosa" in cuidado or "carga especial" in tamano:
        alerta = "CARGA_RIESGOSA"
        prioridad = "CRITICA"
    elif "bebida" in cuidado or "liquido" in cuidado or "líquido" in cuidado:
        alerta = "BEBIDAS_LIQUIDO"
        prioridad = "MEDIA"
    elif tipo == "TURISMO":
        alerta = "VALIDAR_IDENTIDADES"
        prioridad = "ALTA"

    conductor = conductor or {}

    return {
        "ID_SERVICIO": d.get("id_servicio"),
        "estado": estado,
        "tipo_servicio": tipo,
        "canal": d.get("canal_origen", "WHATSAPP"),
        "cliente": d.get("nombre", ""),
        "telefono": str(numero_cliente).replace("51", "", 1) if str(numero_cliente).startswith("51") else str(numero_cliente),
        "dni_cliente": d.get("turismo_dni_principal", ""),
        "origen": origen,
        "destino": destino,
        "ruta": d.get("colectivo_ruta") or d.get("ruta_nombre") or "",
        "conductor": conductor.get("nombre", ""),
        "placa": conductor.get("placa", ""),
        "telefono_conductor": conductor.get("telefono", ""),
        "pago": pago,
        "tarifa": str(tarifa),
        "prioridad": prioridad,
        "alerta": alerta,
        "observacion": d.get("observacion_sheets", ""),
        "hora_confirmacion": d.get("hora_confirmacion", ""),
        "hora_asignacion": datetime.now().strftime("%H:%M") if estado == "ASIGNADO" else "",
    }


async def sheets_evento(action: str, data: dict):
    """Envía eventos operativos a Google Sheets. No debe romper el bot si falla."""
    webhook_url = os.getenv("SHEETS_WEBHOOK_URL", "")
    if not webhook_url:
        print("[SHEETS] No configurado SHEETS_WEBHOOK_URL", flush=True)
        return

    try:
        payload = {
            "action": action,
            "data": data,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(webhook_url, json=payload, follow_redirects=True)
            print(f"[SHEETS] {action}: {r.status_code} {r.text[:120]}", flush=True)
    except Exception as e:
        print(f"[SHEETS ERROR] {action}: {e}", flush=True)


# ── Google Maps ───────────────────────────────────────────────────────────────
async def coords_a_direccion(lat, lng) -> str:
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_MAPS_KEY}&language=es"
    try:
        async with httpx.AsyncClient(timeout=4) as client:
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


def _normalizar_geo(txt: str) -> str:
    import unicodedata
    txt = (txt or "").lower().strip()
    txt = "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")
    return " ".join(txt.replace(".", " ").replace(",", " ").split())

def _distancia_km_simple(lat1, lon1, lat2, lon2) -> float:
    from math import radians, sin, cos, asin, sqrt
    r = 6371.0
    dlat = radians(float(lat2) - float(lat1))
    dlon = radians(float(lon2) - float(lon1))
    a = sin(dlat / 2) ** 2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))

def _alias_barranca(texto: str) -> str:
    n = _normalizar_geo(texto)
    aliases = {
        "calle lino": "El Lino Barranca Peru",
        "calle nino": "El Lino Barranca Peru",
        "el lino": "El Lino Barranca Peru",
        "lino": "El Lino Barranca Peru",
        "parque guadalupe": "Parque Virgen de Guadalupe Barranca Peru",
        "parque virgen guadalupe": "Parque Virgen de Guadalupe Barranca Peru",
        "parque virgen de guadalupe": "Parque Virgen de Guadalupe Barranca Peru",
        "virgen de guadalupe": "Parque Virgen de Guadalupe Barranca Peru",
    }
    return aliases.get(n, texto)

def _palabras_importantes_geo(texto: str) -> list[str]:
    n = _normalizar_geo(texto)
    stop = {
        "calle", "jr", "jiron", "av", "avenida", "pasaje", "psje", "prolongacion",
        "parque", "plaza", "mercado", "barranca", "peru", "el", "la", "los", "las",
        "de", "del", "en", "por", "a", "una", "un"
    }
    return [w for w in n.split() if len(w) >= 3 and w not in stop]

def _coincide_con_busqueda(texto_usuario: str, nombre_lugar: str) -> bool:
    importantes = _palabras_importantes_geo(texto_usuario)
    if not importantes:
        return True
    lugar_norm = _normalizar_geo(nombre_lugar)
    return any(w in lugar_norm for w in importantes)


def _referencia_local_barranca(nombre: str) -> str:
    n = _normalizar_geo(nombre)

    # Referencias locales conocidas de Barranca
    if "lino" in n:
        return "El Lino, referencia Calle Primavera, Barranca"

    if "pasaje espana" in n or "pje espana" in n or "psje espana" in n:
        return "Pasaje España, zona Pampa de Lara, Barranca"

    if "parque guadalupe" in n or "virgen de guadalupe" in n or "guadalupe" in n:
        return "Parque Virgen de Guadalupe, Barranca"

    if "pasaje pelota" in n or "pje pelota" in n or "psje pelota" in n:
        return "Pasaje Pelota, Barranca"

    return ""

def _limpiar_display_barranca(nombre: str) -> str:
    import re

    s = (nombre or "").strip()
    if not s:
        return "Barranca"

    ref_local = _referencia_local_barranca(s)
    if ref_local:
        return ref_local

    # Quitar Plus Codes: 762X+C99, 4X5P+22, etc.
    s = re.sub(r"\b[23456789CFGHJMPQRVWX]{3,}\+[23456789CFGHJMPQRVWX0-9]{2,}\b", "", s, flags=re.I)

    # Quitar codigos postales tipo 15169
    s = re.sub(r"\b15\d{3}\b", "", s)

    # Quitar pais
    s = re.sub(r"\bPer[uú]\b", "", s, flags=re.I)

    partes = [p.strip(" -") for p in s.split(",") if p.strip(" -")]
    partes_limpias = []

    for p in partes:
        pn = _normalizar_geo(p)
        if not pn:
            continue
        if pn in {"peru", "barranca province", "provincia de barranca"}:
            continue
        if "+" in p:
            continue
        partes_limpias.append(p)

    if not partes_limpias:
        return "Barranca"

    primero = partes_limpias[0]
    unido_norm = _normalizar_geo(", ".join(partes_limpias))

    if "barranca" not in unido_norm:
        return f"{primero}, Barranca"

    if _normalizar_geo(primero) == "barranca":
        return "Barranca"

    return f"{primero}, Barranca"


async def _place_details_minimal(place_id: str) -> dict | None:
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,geometry",
        "language": "es",
        "key": GOOGLE_MAPS_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
        result = data.get("result") or {}
        loc = result.get("geometry", {}).get("location", {})
        if not loc.get("lat") or not loc.get("lng"):
            return None
        nombre = result.get("name") or ""
        direccion = result.get("formatted_address") or nombre
        display = direccion if nombre.lower() in direccion.lower() else f"{nombre}, {direccion}"
        display = _limpiar_display_barranca(display)
        return {
            "nombre": display,
            "place_id": place_id,
            "lat": float(loc["lat"]),
            "lng": float(loc["lng"]),
        }
    except Exception as e:
        print(f"[PLACE DETAILS MIN ERROR] {e}", flush=True)
        return None


def _normalizar_geo(txt: str) -> str:
    import unicodedata
    txt = (txt or "").lower().strip()
    txt = "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")
    return " ".join(txt.replace(".", " ").replace(",", " ").split())

def _distancia_km_simple(lat1, lon1, lat2, lon2) -> float:
    from math import radians, sin, cos, asin, sqrt
    r = 6371.0
    dlat = radians(float(lat2) - float(lat1))
    dlon = radians(float(lon2) - float(lon1))
    a = sin(dlat / 2) ** 2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))

def _alias_barranca(texto: str) -> str:
    n = _normalizar_geo(texto)
    aliases = {
        "calle lino": "El Lino Barranca Peru",
        "calle nino": "El Lino Barranca Peru",
        "el lino": "El Lino Barranca Peru",
        "lino": "El Lino Barranca Peru",
        "parque guadalupe": "Parque Virgen de Guadalupe Barranca Peru",
        "parque virgen guadalupe": "Parque Virgen de Guadalupe Barranca Peru",
        "parque virgen de guadalupe": "Parque Virgen de Guadalupe Barranca Peru",
        "virgen de guadalupe": "Parque Virgen de Guadalupe Barranca Peru",
    }
    return aliases.get(n, texto)

def _palabras_importantes_geo(texto: str) -> list[str]:
    n = _normalizar_geo(texto)
    stop = {
        "calle", "jr", "jiron", "av", "avenida", "pasaje", "psje", "prolongacion",
        "parque", "plaza", "mercado", "barranca", "peru", "el", "la", "los", "las",
        "de", "del", "en", "por", "a", "una", "un"
    }
    return [w for w in n.split() if len(w) >= 3 and w not in stop]

def _coincide_con_busqueda(texto_usuario: str, nombre_lugar: str) -> bool:
    importantes = _palabras_importantes_geo(texto_usuario)
    if not importantes:
        return True
    lugar_norm = _normalizar_geo(nombre_lugar)
    return any(w in lugar_norm for w in importantes)

async def _place_details_minimal(place_id: str) -> dict | None:
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,geometry",
        "language": "es",
        "key": GOOGLE_MAPS_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
        result = data.get("result") or {}
        loc = result.get("geometry", {}).get("location", {})
        if not loc.get("lat") or not loc.get("lng"):
            return None
        nombre = result.get("name") or ""
        direccion = result.get("formatted_address") or nombre
        display = direccion if nombre.lower() in direccion.lower() else f"{nombre}, {direccion}"
        return {
            "nombre": display,
            "place_id": place_id,
            "lat": float(loc["lat"]),
            "lng": float(loc["lng"]),
        }
    except Exception as e:
        print(f"[PLACE DETAILS MIN ERROR] {e}", flush=True)
        return None

async def buscar_lugares_barranca(texto: str) -> list:
    texto_original = texto or ""
    texto_alias = _alias_barranca(texto_original)
    query = texto_alias if "barranca" in _normalizar_geo(texto_alias) else f"{texto_alias} Barranca Peru"

    candidatos: list[dict] = []
    vistos: set[str] = set()

    async def agregar_place_id(place_id: str):
        if not place_id or place_id in vistos:
            return
        vistos.add(place_id)
        det = await _place_details_minimal(place_id)
        if not det:
            return
        distancia = _distancia_km_simple(BARRANCA_LAT, BARRANCA_LNG, det["lat"], det["lng"])
        if distancia > (BARRANCA_RADIUS / 1000):
            print(f"[GEO FILTRO] fuera de Barranca: {det['nombre']} ({distancia:.1f} km)", flush=True)
            return
        if not _coincide_con_busqueda(texto_original, det["nombre"]):
            print(f"[GEO FILTRO] no coincide con busqueda '{texto_original}': {det['nombre']}", flush=True)
            return
        det["distancia_barranca"] = distancia
        candidatos.append(det)

    try:
        url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        params = {
            "input": query,
            "location": f"{BARRANCA_LAT},{BARRANCA_LNG}",
            "radius": BARRANCA_RADIUS,
            "strictbounds": "true",
            "language": "es",
            "components": "country:PE",
            "key": GOOGLE_MAPS_KEY,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
        for p in data.get("predictions", [])[:8]:
            await agregar_place_id(p.get("place_id", ""))
    except Exception as e:
        print(f"[AUTOCOMPLETE ERROR] {e}", flush=True)

    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "location": f"{BARRANCA_LAT},{BARRANCA_LNG}",
            "radius": BARRANCA_RADIUS,
            "language": "es",
            "key": GOOGLE_MAPS_KEY,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
        for p in data.get("results", [])[:8]:
            place_id = p.get("place_id", "")
            if place_id and place_id not in vistos:
                await agregar_place_id(place_id)
    except Exception as e:
        print(f"[TEXT SEARCH ERROR] {e}", flush=True)

    candidatos.sort(key=lambda x: x.get("distancia_barranca", 999))

    resultados = []
    claves_nombre = set()

    for c in candidatos:
        nombre_limpio = _limpiar_display_barranca(c.get("nombre", ""))
        clave = _normalizar_geo(nombre_limpio)

        if not clave or clave in claves_nombre:
            continue

        claves_nombre.add(clave)
        resultados.append({
            "nombre": nombre_limpio,
            "place_id": c["place_id"],
        })

        if len(resultados) >= 4:
            break

    print(f"[GEO BARRANCA] '{texto_original}' -> {len(resultados)} resultado(s)", flush=True)
    return resultados

async def coords_de_place_id(place_id: str, nombre_sugerido: str = "") -> tuple:
    # Obtiene coordenadas de un place_id y devuelve nombre legible sin codigos raros.
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,geometry",
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

        nombre = result.get("name") or ""
        direccion_api = result.get("formatted_address") or ""
        base = nombre_sugerido or (f"{nombre}, {direccion_api}" if nombre else direccion_api)
        direccion = _limpiar_display_barranca(base)

        return direccion, f"{lat},{lng}"
    except Exception as e:
        print(f"[PLACE DETAILS ERROR] {e}", flush=True)
        direccion = _limpiar_display_barranca(nombre_sugerido or "Barranca")
        return direccion, f"{BARRANCA_LAT},{BARRANCA_LNG}"



# ── Programador diario de inicio de turno ─────────────────────────────────────
async def obtener_conductores_para_recordatorio_turno():
    """
    Devuelve conductores registrados para enviar recordatorio de inicio de turno.
    Por ahora usa la lista CONDUCTORES del bot.
    Más adelante puede migrarse a Google Sheets como fuente total.
    """
    conductores = []

    try:
        if "CONDUCTORES" in globals() and isinstance(CONDUCTORES, dict):
            for telefono, info in CONDUCTORES.items():
                tel = str(telefono).strip()
                if not tel:
                    continue

                conductores.append({
                    "telefono": tel,
                    "nombre": info.get("nombre", "") if isinstance(info, dict) else "",
                    "placa": info.get("placa", "") if isinstance(info, dict) else ""
                })
    except Exception as e:
        print(f"[TURNO ERROR] No se pudo obtener lista CONDUCTORES: {e}", flush=True)

    return conductores


async def enviar_recordatorio_inicio_turno_masivo():
    """
    Envía la plantilla aprobada inicio_turno_conductor a todos los conductores registrados.
    """
    conductores = await obtener_conductores_para_recordatorio_turno()

    if not conductores:
        print("[TURNO] No hay conductores registrados para enviar recordatorio", flush=True)
        return

    enviados = 0
    fallidos = 0

    print(f"[TURNO] Enviando recordatorio inicio_turno_conductor a {len(conductores)} conductor(es)", flush=True)

    for c in conductores:
        tel = c.get("telefono", "")
        if not tel:
            continue

        ok = await enviar_template_inicio_turno(tel)

        if ok:
            enviados += 1
        else:
            fallidos += 1

        await asyncio.sleep(0.5)

    print(f"[TURNO] Recordatorio finalizado. Enviados={enviados} Fallidos={fallidos}", flush=True)


async def verificar_activos_y_alertar_operador():
    """
    A las 08:00 valida si existe al menos un conductor ACTIVO.
    Si hay 0 activos, alerta al operador.
    """
    try:
        activos = []

        if "obtener_conductores_activos_desde_sheets" in globals():
            activos = await obtener_conductores_activos_desde_sheets()

        total = len(activos or [])

        print(f"[TURNO] Validacion 08:00 conductores activos={total}", flush=True)

        if total > 0:
            return

        mensaje = (
            "🚨 *ALERTA OPERATIVA*\\n\\n"
            "Aún no hay conductores *ACTIVO* en Barranca Móvil.\\n\\n"
            "Hora de validación: 08:00 a. m.\\n\\n"
            "Revisa el panel CONDUCTORES o coordina manualmente con el grupo."
        )

        if "OPERADOR_WA" in globals() and OPERADOR_WA:
            await enviar_mensaje(OPERADOR_WA, mensaje)
        else:
            print("[TURNO ALERTA] OPERADOR_WA no configurado", flush=True)

        try:
            if "sheets_evento" in globals():
                asyncio.create_task(sheets_evento("add_alerta", {
                    "id_servicio": f"TURNO-SIN-ACTIVOS-{int(time.time())}",
                    "tipo_alerta": "SIN_CONDUCTORES_ACTIVOS",
                    "prioridad": "ALTA",
                    "descripcion": "A las 08:00 no hay conductores activos registrados en el panel.",
                    "requiere_accion": "SI",
                    "estado_alerta": "ABIERTA",
                    "responsable": "Operador"
                }))
        except Exception as e:
            print(f"[TURNO ALERTA ERROR] No se pudo registrar alerta en Sheets: {e}", flush=True)

    except Exception as e:
        print(f"[TURNO ERROR] verificar_activos_y_alertar_operador: {e}", flush=True)


async def programador_inicio_turno_conductores():
    """
    Programador diario (robusto ante reinicios de Render):
    - Recordatorio: se envía la PRIMERA vez que el bot esté vivo dentro de la
      ventana 07:00–10:59 Lima y aún no se haya enviado hoy.
      Antes era una ventana rígida 07:00–07:10; si Render reiniciaba después
      de las 07:10 el recordatorio se perdía el día completo (bug confirmado).
    - Alerta: si a partir de las 08:00 Lima no hay conductores activos, avisa.
    Cada acción se ejecuta una sola vez por día.
    """
    try:
        from zoneinfo import ZoneInfo
        tz_lima = ZoneInfo("America/Lima")
    except Exception:
        tz_lima = None

    # Ventana de recuperación (catch-up). Si el bot arranca tarde dentro de
    # este rango, igual manda el recordatorio. Ajustable por env si lo deseas.
    HORA_RECORDATORIO_INICIO = int(os.getenv("TURNO_HORA_INICIO", "7"))   # 07:00 Lima
    HORA_RECORDATORIO_FIN    = int(os.getenv("TURNO_HORA_FIN", "11"))     # hasta 10:59 Lima
    HORA_ALERTA              = int(os.getenv("TURNO_HORA_ALERTA", "8"))   # alerta desde 08:00 Lima

    enviados_recordatorio = set()
    alertas_0800 = set()

    print(
        f"[BOT] Programador inicio turno iniciado - recordatorio "
        f"{HORA_RECORDATORIO_INICIO:02d}:00–{HORA_RECORDATORIO_FIN-1:02d}:59 Lima "
        f"(catch-up) / alerta {HORA_ALERTA:02d}:00 Lima",
        flush=True
    )

    while True:
        try:
            ahora = datetime.now(tz_lima) if tz_lima else datetime.now()
            dia = ahora.strftime("%Y-%m-%d")

            # Recordatorio: cualquier momento dentro de la ventana, una vez al día.
            en_ventana_recordatorio = (
                HORA_RECORDATORIO_INICIO <= ahora.hour < HORA_RECORDATORIO_FIN
            )
            if en_ventana_recordatorio and dia not in enviados_recordatorio:
                enviados_recordatorio.add(dia)
                print(
                    f"[TURNO] Disparando recordatorio (hora Lima {ahora.strftime('%H:%M')})",
                    flush=True
                )
                await enviar_recordatorio_inicio_turno_masivo()

            # Alerta: desde la hora de alerta en adelante, una vez al día.
            if ahora.hour >= HORA_ALERTA and dia not in alertas_0800:
                alertas_0800.add(dia)
                await verificar_activos_y_alertar_operador()

        except Exception as e:
            print(f"[BOT ERROR] programador_inicio_turno_conductores: {e}", flush=True)

        await asyncio.sleep(60)


async def buscar_lugares_peru(texto: str) -> list:
    texto_norm = _normalizar_geo(texto)
    ciudades_externas = [
        "lima", "miraflores", "san isidro", "surco", "callao", "huacho", "huaral",
        "paramonga", "pativilca", "supe", "puerto supe", "chimbote", "trujillo"
    ]
    menciona_externa = any(c in texto_norm for c in ciudades_externas)

    if not menciona_externa:
        locales = await buscar_lugares_barranca(texto)
        if locales:
            return locales

    query = texto if "peru" in texto_norm else f"{texto} Peru"
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": query,
        "location": f"{BARRANCA_LAT},{BARRANCA_LNG}",
        "radius": 500000,
        "language": "es",
        "components": "country:PE",
        "key": GOOGLE_MAPS_KEY,
    }

    resultados = []
    vistos = set()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
        for p in data.get("predictions", [])[:8]:
            place_id = p.get("place_id", "")
            if not place_id or place_id in vistos:
                continue
            vistos.add(place_id)
            det = await _place_details_minimal(place_id)
            if not det:
                continue
            if not _coincide_con_busqueda(texto, det["nombre"]):
                continue
            resultados.append({"nombre": det["nombre"], "place_id": place_id})
            if len(resultados) == 4:
                break
        print(f"[GEO PERU] '{texto}' -> {len(resultados)} resultado(s)", flush=True)
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

def _dedup_sugerencias(sugerencias: list) -> list:
    """Elimina sugerencias con nombres casi identicos (ej: Limoncillo vs Calle Limoncillo)."""
    def clave(nombre: str) -> str:
        n = nombre.lower().split(",")[0].strip()
        for p in ["calle ", "jr. ", "jr ", "av. ", "av ", "avenida ", "pasaje ", "psje ", "prolongacion ", "prol. "]:
            if n.startswith(p):
                n = n[len(p):]
        return n
    vistas, unicas = set(), []
    for s in sugerencias:
        k = clave(s["nombre"])
        if k not in vistas:
            vistas.add(k)
            unicas.append(s)
    return unicas

async def resolver_direccion(texto: str, sesion: dict, datos: dict, numero: str,
                              key_temp: str, key_coords: str, estado_confirmar: str,
                              label_confirm: str):
    """Helper: busca con autocomplete tipo Waze.
    1 resultado unico  → auto-confirma y avanza directo (sin preguntar)
    2-4 resultados     → lista, usuario elige y va DIRECTO
    0 resultados       → error"""
    sugerencias = await buscar_lugares_barranca(texto)
    if not sugerencias:
        await enviar_mensaje(numero, MSG_NO_ENCONTRADO)
        return

    unicas = _dedup_sugerencias(sugerencias)

    if len(unicas) == 1:
        # Un solo lugar → auto-confirmar sin preguntar
        sug = unicas[0]
        direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
        if label_confirm == "recojo":
            datos["recojo_texto"] = direccion
            datos["recojo_coords"] = coords
            sesion["estado"] = S_DESTINO
            await enviar_mensaje(numero,
                f"✅ Recojo: *{direccion}*\n\n"
                "🏁 *¿A dónde vas?*\n\n"
                "• 📌 Comparte ubicación del destino\n"
                "• ✍️ O escribe el destino" + NAV)
        elif label_confirm == "destino":
            datos["destino_texto"] = direccion
            datos["destino_coords"] = coords
            km = await calcular_distancia_km(datos.get("recojo_coords", ""), coords)
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
        elif label_confirm == "colectivo_recojo":
            datos["colectivo_recojo"] = direccion
            sesion["estado"] = S_COLECTIVO_PAGO
            await enviar_mensaje(numero,
                f"✅ Recojo: *{direccion}*\n\n"
                "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
        else:
            # fallback generico
            datos[key_temp] = direccion
            datos[key_coords] = coords
            sesion["estado"] = estado_confirmar
            await enviar_mensaje(numero,
                f"📍 *{direccion}*\n\n¿Es correcto?\n1️⃣ Sí\n2️⃣ No, escribir otra")
    else:
        # Varias opciones distintas → mostrar lista
        numeros = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        opciones_txt = "\n".join([f"{numeros[i]} {s['nombre'].split(',')[0]}" for i, s in enumerate(unicas)])
        datos["_sugerencias"] = unicas
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
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": SYSTEM_PROMPT_IA}] + historial,
            max_tokens=150, temperature=0.5
        )
    try:
        completion = await asyncio.wait_for(asyncio.to_thread(_groq), timeout=4.0)
        resp = completion.choices[0].message.content
    except (asyncio.TimeoutError, Exception):
        resp = ("Lo siento, no entendí tu consulta. ¿Necesitas taxi, colectivo, encomienda o turismo?\n\n"
                "Escribe *menu* para ver las opciones.")
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


async def obtener_conductores_activos_desde_sheets():
    """
    Lee la hoja CONDUCTORES desde Apps Script.
    Solo devuelve conductores con ESTADO = ACTIVO.
    Google Sheets es la fuente de verdad.
    """
    webhook_url = os.getenv("SHEETS_WEBHOOK_URL", "")
    if not webhook_url:
        print("[CONDUCTORES] SHEETS_WEBHOOK_URL no configurado", flush=True)
        return []

    payload = {
        "action": "get_conductores_activos"
    }

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.post(webhook_url, json=payload)

        if r.status_code >= 400:
            print(f"[CONDUCTORES ERROR] HTTP {r.status_code}: {r.text[:300]}", flush=True)
            return []

        resp = r.json()

        if not resp.get("ok"):
            print(f"[CONDUCTORES ERROR] Respuesta inválida: {resp}", flush=True)
            return []

        conductores = resp.get("conductores", []) or []
        print(f"[CONDUCTORES] activos desde Sheets: {len(conductores)}", flush=True)

        activos = []
        for c in conductores:
            telefono = str(c.get("telefono", "")).strip()
            if not telefono:
                continue

            activos.append({
                "telefono": telefono,
                "nombre": c.get("nombre", ""),
                "placa": c.get("placa", ""),
                "estado": c.get("estado", "ACTIVO")
            })

        return activos

    except Exception as e:
        print(f"[CONDUCTORES ERROR] No se pudo consultar Sheets: {e}", flush=True)
        return []


async def notificar_conductores(sesion: dict, numero_cliente: str, tipo: str = "TAXI"):
    """Envía solicitud a todos los conductores individualmente.
    El primero en responder ACEPTO se lleva el servicio."""
    d = sesion["datos"]
    if not d.get("id_servicio"):
        d["id_servicio"] = generar_id_servicio(numero_cliente, tipo)
    d["hora_confirmacion"] = datetime.now().strftime("%H:%M")

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
               f"📍 Recojo solicitado: {d.get('enc_origen')}\n"
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
               f"📍 Recojo solicitado: {d.get('colectivo_recojo')}\n"
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

    # Enviar solo a conductores ACTIVOS (no pausados)
    conductores_activos_sheets = await obtener_conductores_activos_desde_sheets()
    conductores_disponibles = [c["telefono"] for c in conductores_activos_sheets if c.get("telefono")]
    conductores_por_numero_sheets = {
        c["telefono"]: c for c in conductores_activos_sheets if c.get("telefono")
    }
    if not conductores_disponibles:
        await enviar_mensaje(numero_cliente,
            "😔 No hay conductores activos disponibles ahora.\n\nIntenta en unos minutos o escribe *menu*.")
        servicios_pendientes.pop(numero_cliente, None)
        return

    # Guardar servicio como pendiente operativo
    servicios_pendientes[numero_cliente] = {
        "tipo": tipo,
        "estado": "PENDIENTE_CONDUCTOR",
        "datos": d.copy(),
        "creado_en": time.time(),
        "conductores_notificados": list(conductores_disponibles)
    }

    # Envío PARALELO a todos los conductores (asyncio.gather = mucho más rápido)
    tareas = [enviar_mensaje(num_conductor, msg) for num_conductor in conductores_disponibles]
    if GRUPO_CONDUCTORES:
        tareas.append(enviar_mensaje(GRUPO_CONDUCTORES, msg))
    await asyncio.gather(*tareas)

    asyncio.create_task(sheets_evento(
        "upsert_servicio",
        armar_sheets_servicio(numero_cliente, tipo, d, "PENDIENTE_CONDUCTOR")
    ))

    # Timeout 90s: si nadie acepta, avisar al cliente
    async def timeout_sin_conductor():
        await asyncio.sleep(180)
        if numero_cliente in servicios_pendientes:
            servicio_timeout = servicios_pendientes.get(numero_cliente, {})
            datos_timeout = servicio_timeout.get("datos", {})
            tipo_timeout = servicio_timeout.get("tipo", tipo)

            await sheets_evento(
                "upsert_servicio",
                armar_sheets_servicio(numero_cliente, tipo_timeout, datos_timeout, "SIN_CONDUCTOR")
            )

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

async def cancelar_solicitud_actual(numero: str):
    sesiones.pop(numero, None)
    await enviar_mensaje(numero,
        "Solicitud cancelada.\n\n"
        "Cuando necesites otro servicio, escribe *menu*.")

def es_comando_cancelar(texto: str) -> bool:
    t = (texto or "").strip().lower()
    return t in {
        "salir", "cancelar", "cancela", "anular", "anula",
        "ya no", "no deseo", "no quiero", "terminar", "finalizar",
        "cancelar solicitud", "salir del servicio"
    }

def es_primer_paso_servicio(estado: str) -> bool:
    primeros = {
        globals().get("S_NOMBRE"),
        globals().get("S_TAXI_NOMBRE"),
        globals().get("S_COLECTIVO_RUTA"),
        globals().get("S_ENCOMIENDA_DESC"),
        globals().get("S_TURISMO_TIPO"),
        globals().get("S_TURISMO_DESTINO"),
    }
    return estado in {x for x in primeros if x}



async def descargar_media_whatsapp(media_id: str) -> tuple[str, str]:
    import tempfile

    if not media_id:
        raise ValueError("media_id vacio")

    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    meta_url = f"https://graph.facebook.com/v19.0/{media_id}"

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(meta_url, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"Meta media URL error {r.status_code}: {r.text}")
        info = r.json()

    download_url = info.get("url")
    mime_type = info.get("mime_type", "audio/ogg")

    if not download_url:
        raise RuntimeError("Meta no devolvio URL de descarga")

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(download_url, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"Meta media download error {r.status_code}: {r.text}")
        data = r.content

    suffix = ".ogg"
    if "mpeg" in mime_type or "mp3" in mime_type:
        suffix = ".mp3"
    elif "mp4" in mime_type or "m4a" in mime_type:
        suffix = ".m4a"
    elif "wav" in mime_type:
        suffix = ".wav"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(data)
    tmp.close()

    return tmp.name, mime_type


async def transcribir_audio_groq(ruta_audio: str) -> str:
    from pathlib import Path as _Path

    if not GROQ_API_KEY:
        raise RuntimeError("Falta GROQ_API_KEY")

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    audio_path = _Path(ruta_audio)
    if not audio_path.exists():
        raise RuntimeError(f"No existe el audio descargado: {ruta_audio}")

    data = {
        "model": "whisper-large-v3-turbo",
        "language": "es",
        "response_format": "json",
        "temperature": "0",
    }

    with audio_path.open("rb") as f:
        files = {"file": (audio_path.name, f, "application/octet-stream")}
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(url, headers=headers, data=data, files=files)

    if r.status_code >= 400:
        raise RuntimeError(f"Groq transcription error {r.status_code}: {r.text}")

    resp = r.json()
    return (resp.get("text") or "").strip()


async def procesar_audio(numero: str, audio_payload: dict):
    import os

    media_id = (audio_payload or {}).get("id", "")
    if not media_id:
        await enviar_mensaje(numero, "No pude leer el audio. Intenta enviarlo nuevamente.")
        return

    ruta_audio = ""
    try:
        await enviar_mensaje(numero, "Audio recibido. Lo estoy escuchando...")
        ruta_audio, _mime_type = await descargar_media_whatsapp(media_id)
        texto_audio = await transcribir_audio_groq(ruta_audio)

        if not texto_audio or len(texto_audio.strip()) < 2:
            await enviar_mensaje(numero, "No logre entender el audio. Por favor envialo otra vez o escribe tu solicitud.")
            return

        await enviar_mensaje(numero, f"Entendi:\n_{texto_audio}_")
        await procesar(numero, "text", {"body": texto_audio})

    except Exception as e:
        print(f"[AUDIO ERROR] {e}", flush=True)
        await enviar_mensaje(numero, "No pude procesar el audio. Por favor escribe tu solicitud o intenta enviar otro audio.")
    finally:
        if ruta_audio:
            try:
                os.remove(ruta_audio)
            except Exception:
                pass




def normalizar_nombre_persona(nombre: str) -> str:
    nombre = " ".join((nombre or "").strip().split())
    if not nombre:
        return ""

    minusculas = {"de", "del", "la", "las", "los", "y"}
    partes = []

    for i, p in enumerate(nombre.lower().split()):
        if i > 0 and p in minusculas:
            partes.append(p)
        else:
            partes.append(p.capitalize())

    return " ".join(partes)

def extraer_nombre_dni(texto: str):
    """Separa nombre y DNI si el usuario escribe ambos juntos. Ej: 'Zoila Tello, 15862130'."""
    import re
    raw = (texto or "").strip()
    m = re.search(r"\b(\d{7,9})\b", raw)
    if not m:
        return normalizar_nombre_persona(raw.strip(" ,.-")), ""

    dni = m.group(1)
    nombre = (raw[:m.start()] + " " + raw[m.end():]).strip(" ,.-")
    nombre = " ".join(nombre.split())

    return normalizar_nombre_persona(nombre), dni

async def procesar(numero: str, tipo: str, contenido: dict):
    if numero not in sesiones:
        sesiones[numero] = {"estado": S_MENU, "datos": {}}

    # Actualizar timestamp de actividad
    ultima_actividad[numero] = time.time()

    sesion = sesiones[numero]
    estado = sesion["estado"]
    texto = (contenido.get("body", "") if isinstance(contenido, dict) else "").strip()

    if es_comando_cancelar(texto):
        await cancelar_solicitud_actual(numero)
        return

    if texto == "0" and es_primer_paso_servicio(estado):
        await cancelar_solicitud_actual(numero)
        return

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

    # ── Proveedor Seguridad responde COTIZO ──────────────────────────────────
    if numero in PROVEEDORES_SEG and texto.upper().startswith("COTIZO"):
        partes = texto.strip().split(maxsplit=3)
        # Formato: COTIZO [tel_cliente] [monto] [descripcion]
        if len(partes) >= 3:
            tel_raw    = partes[1].replace("+51","").replace("51","",1) if partes[1].startswith("+51") or (partes[1].startswith("51") and len(partes[1])==11) else partes[1]
            num_cliente = tel_raw if tel_raw.startswith("51") else f"51{tel_raw}"
            monto_str  = partes[2]
            descripcion = partes[3] if len(partes) >= 4 else ""
            proveedor  = PROVEEDORES_SEG[numero]

            if num_cliente not in solicitudes_seg_pendientes:
                await enviar_mensaje(numero,
                    f"❌ No encontré solicitud activa para el número {tel_raw}.\n"
                    f"Verifica el número e intenta de nuevo.")
                return

            cotizaciones_seg_pendientes[num_cliente] = {
                "monto":       monto_str,
                "descripcion": descripcion,
                "proveedor":   proveedor["nombre"],
            }
            sesiones[num_cliente] = {
                "estado": S_SEG_CONFIRMAR_COT,
                "datos":  sesiones.get(num_cliente, {}).get("datos", solicitudes_seg_pendientes.get(num_cliente, {}))
            }
            await enviar_mensaje(numero,
                f"✅ Cotización enviada al cliente. Esperando respuesta.")
            await enviar_mensaje(num_cliente,
                f"💰 *Cotización recibida — {proveedor['negocio']}*\n\n"
                f"🛡️ Servicio: {sesiones[num_cliente]['datos'].get('seg_subcategoria','')}\n"
                f"💵 Monto: *S/{monto_str}*\n"
                f"{'📝 ' + descripcion + chr(10) if descripcion else ''}\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"¿Deseas aceptar esta cotización?\n\n"
                f"1️⃣ ✅ Aceptar\n"
                f"2️⃣ ❌ Rechazar")
        else:
            await enviar_mensaje(numero,
                "⚠️ Formato incorrecto. Usa:\n"
                "*COTIZO [teléfono_cliente] [monto] [descripción breve]*\n\n"
                "Ejemplo: COTIZO 987654321 150 recarga 3 extintores 6kg")
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

            if numero not in servicios_pendientes[numero_cliente_full].get("conductores_notificados", []):
                await enviar_mensaje(numero, "❌ No puedes tomar este servicio porque no estás en la lista de conductores disponibles para esta solicitud.")
                return

            # Marcar como tomado
            servicios_tomados.add(numero_cliente_full)
            servicio = servicios_pendientes.pop(numero_cliente_full)
            conductor = CONDUCTORES[numero]
            tipo_servicio = servicio.get("tipo", "TAXI")

            asyncio.create_task(sheets_evento(
                "upsert_servicio",
                armar_sheets_servicio(numero_cliente_full, tipo_servicio, servicio["datos"], "ASIGNADO", conductor)
            ))

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
                    f"✅ *Servicio asignado para ti*\n\n"
                    f"🧾 Tipo: *{tipo_servicio}*\n"
                    f"👤 Cliente: {servicio['datos'].get('nombre', 'N/A')}\n"
                    f"📱 Teléfono: +{numero_cliente_full}\n"
                    f"📍 Recojo solicitado: {servicio['datos'].get('recojo_texto') or servicio['datos'].get('colectivo_recojo') or servicio['datos'].get('enc_origen', 'N/A')}\n"
                    f"🏁 Destino/Ruta: {servicio['datos'].get('destino_texto') or servicio['datos'].get('colectivo_ruta') or servicio['datos'].get('enc_destino', 'N/A')}\n"
                    f"💳 Pago: {servicio['datos'].get('pago') or servicio['datos'].get('colectivo_pago') or 'A coordinar'}\n\n"
                    f"Coordina directamente con el cliente.\n"
                    f"Cuando termines escribe: *FIN*")
                if servicio['datos'].get('enc_foto_id'):
                    await reenviar_imagen(numero, servicio['datos']['enc_foto_id'])
                await enviar_mensaje(numero_cliente_full,
                    f"✅ *Conductor asignado*\n\n"
                    f"👤 Conductor: *{conductor['nombre']}*\n"
                    f"🚗 Placa: *{conductor['placa']}*\n"
                    f"📱 Contacto: +{numero}\n\n"
                    f"🧾 Servicio: *{tipo_servicio}*\n"
                    f"📍 Recojo solicitado: {servicio['datos'].get('recojo_texto') or servicio['datos'].get('colectivo_recojo') or servicio['datos'].get('enc_origen', 'N/A')}\n"
                    f"🏁 Destino/Ruta: {servicio['datos'].get('destino_texto') or servicio['datos'].get('colectivo_ruta') or servicio['datos'].get('enc_destino', 'N/A')}\n\n"
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

                asyncio.create_task(sheets_evento(
                    "upsert_servicio",
                    armar_sheets_servicio(numero_cliente_full, tipo_servicio, servicio["datos"], "ASIGNADO", conductor)
                ))

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
            await actualizar_estado_conductor_sheets(numero, "PAUSADO")
            await enviar_mensaje(numero,
                f"⏸️ *{conductor_info['nombre']}* — PAUSADO\n\n"
                "No recibirás nuevos servicios.\n"
                "Escribe *ACTIVAR* cuando estés disponible.")
            return

        if txt_up in ["ACTIVAR", "ACTIVO"]:
            conductores_estado[numero] = True
            await actualizar_estado_conductor_sheets(numero, "ACTIVO")
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
                               f"Te esperamos pronto en *El Cuervo* 🦅"
                               f"{OPCIONES_FINAL}")
        else:
            respuesta_final = (f"🙏 *Gracias por tu opinión.*\n\n"
                               f"Tomaremos acción para mejorar el servicio.\n"
                               f"Disculpa los inconvenientes 🙏"
                               f"{OPCIONES_FINAL}")
        await enviar_mensaje(numero, respuesta_final)

    # ══ MENU CENTRAL EL CUERVO ════════════════════════════════════════════════
    elif estado == S_MENU:
        if texto == "1":
            sesion["estado"] = S_TRANSPORTE_MENU
            await enviar_mensaje(numero, MSG_TRANSPORTE_MENU)
        elif texto == "2":
            sesion["estado"] = S_GASTRO_LISTA
            await enviar_mensaje(numero, MSG_GASTRO_PROXIMAMENTE)
        elif texto == "3":
            if not dentro_horario_seg():
                await enviar_mensaje(numero,
                    "🛡️ *Seguridad & Saneamiento*\n\n"
                    "⏰ Nuestro proveedor atiende de *8:00 am a 6:00 pm*.\n\n"
                    "Escríbenos mañana en ese horario y con gusto te ayudamos 🙌\n\n"
                    "Escribe *menu* para volver al inicio.")
                return
            sesion["estado"] = S_SEG_SUBCATEGORIA
            await enviar_mensaje(numero,
                "🛡️ *Seguridad & Saneamiento*\n\n"
                "¿Qué servicio necesitas?\n\n"
                "1️⃣ Extintores (venta / recarga)\n"
                "2️⃣ Señalización de seguridad\n"
                "3️⃣ Fumigación / Control de plagas\n"
                "4️⃣ Capacitación y Defensa Civil\n"
                "5️⃣ Otro servicio\n"
                "0️⃣ Volver al menú principal" + NAV)
        elif texto == "0":
            sesiones.pop(numero, None)
            historial_ia.pop(numero, None)
            await enviar_mensaje(numero,
                "👋 *¡Hasta pronto!*\n\n"
                "Cuando necesites algo escribe *hola* o *menu*.\n\n"
                "_El Cuervo — servicios locales siempre a tu disposición_ 🦅")
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

    # ══ TRANSPORTE (Barranca Móvil) ═══════════════════════════════════════════
    elif estado == S_TRANSPORTE_MENU:
        if texto_es_promo(texto):
            datos["promo_activa"] = True
            datos["promo_codigo"] = PROMO_CODIGO
            await enviar_mensaje(numero,
                "🎉 *Promo de lanzamiento Barranca Móvil*\n\n"
                "🎁 *Tu primer servicio de movilidad puede salirte GRATIS*\n"
                "💰 Valor máximo promocional: *S/7*\n"
                "🎟️ Solo para los *10 primeros usuarios nuevos*\n\n📌 *¿Cómo funciona?*\nSi tu viaje cuesta *S/7 o menos*, te sale *GRATIS*.\nSi cuesta más de *S/7*, solo pagas la diferencia.\n\n"
                "✅ Aplica para:\n"
                "1️⃣ Taxi urbano dentro de Barranca\n"
                "2️⃣ Primer cupo en colectivo compartido\n"
                "3️⃣ No aplica para encomiendas\n\n"
                "⚠️ No aplica para Lima, Huacho, turismo, viajes largos, anexos lejanos, cargas pesadas o riesgosas.\n\n"
                "Elige el servicio que deseas solicitar:\n"
                "1️⃣ Taxi urbano\n"
                "2️⃣ Colectivo compartido\n"
                "3️⃣ Envío de encomienda\n"
                "0️⃣ Volver")
            return

        if texto == "1":
            sesion["estado"] = S_NOMBRE
            datos["servicio"] = "TAXI"
            if datos.get("promo_codigo") == PROMO_CODIGO:
                datos["promo_activa"] = True
            await enviar_mensaje(numero, "🙋 Escribe tu nombre y primer apellido.\nEjemplo: Ana Torres\n\nTambién puedes enviar un audio breve si prefieres.")
        elif texto == "2":
            sesion["estado"] = S_NOMBRE
            datos["servicio"] = "COLECTIVO"
            if datos.get("promo_codigo") == PROMO_CODIGO:
                datos["promo_activa"] = True
            await enviar_mensaje(numero, "🚌 ¡Genial! Escribe tu nombre y primer apellido.\nEjemplo: Ana Torres\n\nTambién puedes enviar un audio breve si prefieres.")
        elif texto == "3":
            sesion["estado"] = S_NOMBRE
            datos["servicio"] = "ENCOMIENDA"
            if datos.get("promo_codigo") == PROMO_CODIGO:
                datos["promo_activa"] = True
            await enviar_mensaje(numero, "📦 ¡Perfecto! Escribe tu nombre y primer apellido.\nEjemplo: Ana Torres\n\nTambién puedes enviar un audio breve si prefieres.")
        elif texto == "4":
            sesion["estado"] = S_NOMBRE
            datos["servicio"] = "TURISMO"
            await enviar_mensaje(numero, "🗺️ ¡Genial! Escribe tu nombre y primer apellido.\nEjemplo: Ana Torres\n\nTambién puedes enviar un audio breve si prefieres.")
        elif texto == "0":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, MSG_BIENVENIDA)
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

    # ══ GASTRONOMÍA (placeholder) ═════════════════════════════════════════════
    elif estado == S_GASTRO_LISTA:
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        await enviar_mensaje(numero, MSG_GASTRO_PROXIMAMENTE)

    # ══ SEGURIDAD & SANEAMIENTO ════════════════════════════════════════════════
    elif estado == S_SEG_SUBCATEGORIA:
        if texto not in SEG_SUBCATEGORIAS and texto != "0":
            await enviar_mensaje(numero,
                "Por favor elige una opción del *1* al *5*, o *0* para volver." + NAV)
            return
        if texto == "0":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, MSG_BIENVENIDA)
            return
        datos["seg_subcategoria"] = SEG_SUBCATEGORIAS[texto]
        sesion["estado"] = S_SEG_DESCRIPCION
        await enviar_mensaje(numero,
            f"📋 *{SEG_SUBCATEGORIAS[texto]}*\n\n"
            "Describe brevemente tu necesidad.\n"
            "_(Ej: necesito recargar 3 extintores de 6kg para mi negocio)_" + NAV)

    elif estado == S_SEG_DESCRIPCION:
        if not texto or len(texto) < 5:
            await enviar_mensaje(numero, "Por favor escribe una descripción más detallada 📝" + NAV)
            return
        datos["seg_descripcion"] = texto
        sesion["estado"] = S_SEG_UBICACION
        await enviar_mensaje(numero,
            "📍 *¿Cuál es la dirección donde se realizará el servicio?*\n"
            "• Comparte tu ubicación 📌\n"
            "• O escribe la dirección completa" + NAV)

    elif estado == S_SEG_UBICACION:
        if lat and lng:
            direccion = await coords_a_direccion(lat, lng)
            datos["seg_ubicacion"] = direccion if direccion else f"📌 Coordenadas: {lat},{lng}"
            datos["seg_lat"] = lat
            datos["seg_lng"] = lng
        elif texto and len(texto) >= 5:
            datos["seg_ubicacion"] = texto
        else:
            await enviar_mensaje(numero,
                "Por favor comparte tu ubicación o escribe la dirección." + NAV)
            return
        sesion["estado"] = S_SEG_URGENCIA
        await enviar_mensaje(numero,
            "⏰ *¿Con qué urgencia necesitas el servicio?*\n\n"
            "1️⃣ Urgente — lo antes posible\n"
            "2️⃣ Programar — elegir fecha y hora\n"
            "0️⃣ Volver" + NAV)

    elif estado == S_SEG_URGENCIA:
        if texto == "0":
            sesion["estado"] = S_SEG_UBICACION
            await enviar_mensaje(numero, PROMPT_VOLVER[S_SEG_UBICACION] + NAV)
            return
        if texto not in ["1", "2"]:
            await enviar_mensaje(numero, "Responde *1* Urgente o *2* Programar, o *0* para volver." + NAV)
            return
        datos["seg_urgencia"] = "URGENTE" if texto == "1" else "PROGRAMADO"
        if texto == "2":
            sesion["estado"] = S_SEG_PROGRAMAR
            await enviar_mensaje(numero,
                "📅 *¿Para cuándo necesitas el servicio?*\n"
                "_(Ej: mañana a las 10am / 30 de mayo a las 3pm)_" + NAV)
        else:
            # Urgente: notificar a Marcos y esperar cotización
            await _notificar_proveedor_seg(numero, datos)
            sesion["estado"] = S_SEG_ESPERA_COT

    elif estado == S_SEG_PROGRAMAR:
        if not texto or len(texto) < 3:
            await enviar_mensaje(numero, "Por favor escribe la fecha y hora del servicio." + NAV)
            return
        datos["seg_fecha_programada"] = texto
        await _notificar_proveedor_seg(numero, datos)
        sesion["estado"] = S_SEG_ESPERA_COT

    elif estado == S_SEG_ESPERA_COT:
        # El cliente puede preguntar el estado o esperar
        await enviar_mensaje(numero,
            "⏳ *Aún estamos esperando la cotización de nuestro especialista.*\n\n"
            "Te notificaremos en cuanto tengamos una respuesta.\n\n"
            "Escribe *menu* si deseas hacer otra consulta." + NAV)

    elif estado == S_SEG_CONFIRMAR_COT:
        if texto == "1":
            # Cliente acepta cotización
            cot = cotizaciones_seg_pendientes.pop(numero, {})
            datos["seg_cotizacion_aceptada"] = cot.get("monto", "")
            datos["seg_estado"] = "CONFIRMADO"
            # Notificar a Marcos que fue aceptado
            num_marcos = list(PROVEEDORES_SEG.keys())[0]
            nombre_cliente = datos.get("nombre", "Cliente")
            tel_cliente = telefono_sin_51(numero)
            await enviar_mensaje(num_marcos,
                f"✅ *¡Cotización ACEPTADA!*\n\n"
                f"👤 Cliente: {nombre_cliente}\n"
                f"📱 Teléfono: +{tel_cliente}\n"
                f"🛡️ Servicio: {datos.get('seg_subcategoria','')}\n"
                f"📍 Dirección: {datos.get('seg_ubicacion','')}\n"
                f"💰 Monto aceptado: S/{cot.get('monto','')}\n"
                f"⏰ Urgencia: {datos.get('seg_urgencia','')}\n"
                f"{'📅 Fecha: ' + datos.get('seg_fecha_programada','') if datos.get('seg_fecha_programada') else ''}\n\n"
                f"Coordina con el cliente para confirmar horario exacto.")
            asyncio.create_task(sheets_evento("upsert_servicio", {
                "FECHA":       datetime.now().strftime("%d/%m/%Y %H:%M"),
                "ID_SERVICIO": generar_id_servicio(numero, "SEG"),
                "CATEGORIA":   "SEGURIDAD",
                "SUBCATEGORIA": datos.get("seg_subcategoria",""),
                "CLIENTE":     datos.get("nombre",""),
                "TELEFONO":    telefono_sin_51(numero),
                "DESCRIPCION": datos.get("seg_descripcion",""),
                "UBICACION":   datos.get("seg_ubicacion",""),
                "URGENCIA":    datos.get("seg_urgencia",""),
                "PROVEEDOR":   "Marcos Espinoza / SASI SAC",
                "MONTO":       cot.get("monto",""),
                "ESTADO":      "CONFIRMADO",
            }))
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                f"✅ *¡Servicio confirmado!*\n\n"
                f"🛡️ *{datos.get('seg_subcategoria','')}*\n"
                f"👷 Especialista: *Marcos Espinoza / SASI SAC*\n"
                f"💰 Monto: *S/{cot.get('monto','')}*\n\n"
                f"Marcos coordinará contigo los detalles finales.\n\n"
                f"Escribe *menu* para volver al inicio 🦅")
        elif texto == "2":
            # Cliente rechaza cotización
            cot = cotizaciones_seg_pendientes.pop(numero, {})
            num_marcos = list(PROVEEDORES_SEG.keys())[0]
            await enviar_mensaje(num_marcos,
                f"❌ *Cotización rechazada*\n"
                f"El cliente {datos.get('nombre','N/A')} no aceptó la cotización de S/{cot.get('monto','')}.")
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                "Entendido. Hemos notificado al especialista.\n\n"
                "Si cambias de opinión o necesitas otro servicio, escribe *menu* 🦅")
        else:
            cot = cotizaciones_seg_pendientes.get(numero, {})
            await enviar_mensaje(numero,
                f"Por favor responde:\n\n"
                f"1️⃣ Aceptar cotización (S/{cot.get('monto','')})\n"
                f"2️⃣ Rechazar cotización")

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
        nombre_normalizado = normalizar_nombre_persona(texto)
        partes_nombre = [p for p in nombre_normalizado.split() if p]

        if len(partes_nombre) < 2:
            await enviar_mensaje(numero,
                "Por favor escribe tu nombre y primer apellido.\n"
                "Ejemplo: Ana Torres")
            return

        datos["nombre"] = nombre_normalizado
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
                f"_(Precio por pasajero. Recojo a domicilio sujeto a cupos disponibles o confirmación del conductor)_" + NAV)
        elif servicio == "ENCOMIENDA":
            sesion["estado"] = S_ENCOMIENDA_DESC
            await enviar_mensaje(numero,
                f"👍 Hola *{datos['nombre']}*!\n\n"
                "📦 ¿Qué vas a enviar?\n"
                "Puedes escribirlo o enviar un audio breve.\n"
                "_Ejemplo: una silla de oficina de 20 kilos_")
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
            f"🏁 {datos['destino_texto']}\n💰 S/{datos['tarifa']}\n"f"{datos.get('tarifa_aviso','')}"f"💳 {datos['pago']}\n\n"
            "1️⃣ *REGISTRAR CUPO* ✅\n2️⃣ *CANCELAR* ❌" + NAV)

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
            "📌 *Importante:* este servicio es compartido.\n"
            "La salida depende de cupos disponibles o confirmación del conductor.\n\n"
            f"🕐 *¿Cuándo necesitas el colectivo?*\n\n"
            f"1️⃣ Ahora mismo 🚀\n"
            f"2️⃣ Indicar hora 🕐" + NAV)

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
        _, total_final_promo, texto_promo = aplicar_promo_monto(datos, datos['colectivo_total'], "COLECTIVO")
        datos["colectivo_total_final"] = total_final_promo

        await enviar_mensaje(numero,
            f"🚌 *Confirma tu cupo de colectivo compartido:*\n\n"
            f"👤 {datos['nombre']}\n"
            f"{datos['colectivo_emoji']} Ruta: {datos['colectivo_ruta']}\n"
            f"🕐 Horario: {datos['colectivo_horario']}\n"
            f"👥 Cupos solicitados: {datos['colectivo_asientos']}\n"
            f"📍 Recojo solicitado: {datos['colectivo_recojo']}\n"
            f"💰 Precio referencial: S/{datos['colectivo_total']:.2f}\n"
            f"{texto_promo}"
            f"💳 {datos['colectivo_pago']}\n\n"
            "📌 La salida se confirmará cuando se completen cupos o cuando un conductor acepte la ruta.\n\n"
            "1️⃣ *REGISTRAR CUPO* ✅\n2️⃣ *CANCELAR* ❌" + NAV)

    elif estado == S_COLECTIVO_CONFIRMAR:
        if texto == "1":
            await notificar_conductores(sesion, numero, "COLECTIVO")
            guardar_viaje(numero, {
                "destino_texto": datos.get("colectivo_ruta"),
                "tarifa": datos.get("colectivo_total"),
                "pago": datos.get("colectivo_pago")
            }, "colectivo")
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            promo_final = ""
            if datos.get("promo_descuento"):
                promo_final = f"\n🎁 Promo aplicada: -S/{datos.get('promo_descuento', 0):.2f}\nTotal final: S/{datos.get('promo_total_final', 0):.2f}\n"

            await enviar_mensaje(numero,
                f"✅ *Cupo registrado* 🚌\n\n"
                f"Ruta: *{datos.get('colectivo_ruta')}*\n"
                f"Horario solicitado: *{datos.get('colectivo_horario')}*\n"
                f"{promo_final}\n"
                f"Estamos agrupando pasajeros para esta ruta. Te avisaremos cuando un conductor confirme la salida.\n\n"
                f"📌 *Recuerda:* el colectivo compartido sale cuando se completan "
                f"los {COLECTIVO_MAX_ASIENTOS} asientos o cuando un conductor confirma disponibilidad.\n\n"
                f"━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir")

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

        # Auto-detectar cantidad, tamaño, peso y cuidado desde la descripcion
        import re as _re
        desc_l = texto.lower()

        auto_paquetes = None
        auto_tamano = None
        peso_kg = None
        peso_unitario_kg = None
        peso_total_kg = None
        productos_detectados = []

        def _paquetes_txt(n):
            return "1 paquete" if int(n) == 1 else f"{int(n)} paquetes"

        # Detectar productos especiales / conocidos
        es_gas = any(w in desc_l for w in [
            "balon de gas", "balón de gas", "balon gas", "balón gas",
            "gas lleno", "balon lleno", "balón lleno"
        ])

        es_bebida = any(w in desc_l for w in [
            "cerveza", "cervezas", "botella", "botellas",
            "bebida", "bebidas", "liquido", "líquido"
        ])

        if es_gas:
            productos_detectados.append("Balón de gas lleno" if "lleno" in desc_l else "Balón de gas")

        if any(w in desc_l for w in ["canasta", "canastas", "viveres", "víveres"]):
            productos_detectados.append("Canasta de víveres")

        if es_bebida:
            if "caja" in desc_l or "cajas" in desc_l:
                productos_detectados.append("Caja de cervezas/bebidas")
            else:
                productos_detectados.append("Bebidas / líquidos")

        # Cantidad explicita: "2 cajas", "3 bolsas", etc.
        m_n = _re.search(
            r'\b(\d+)\s*(balon|balones|balón|balones|canasta|canastas|costal|costales|paquete|paquetes|caja|cajas|bolsa|bolsas|bolson|bolsones|bulto|bultos|maleta|maletas|saco|sacos|silla|sillas|mesa|mesas|mueble|muebles)\b',
            desc_l
        )
        if m_n:
            n = int(m_n.group(1))
            auto_paquetes = min(n, 4) if n <= 3 else 4

        # Cantidad por objetos singulares: "un balón ... y una caja ..."
        objetos_singulares = _re.findall(
            r'\b(?:un|una|1)\s+(balon|balón|canasta|caja|bolsa|paquete|bulto|maleta|saco|silla|mesa|mueble|costal)\b',
            desc_l
        )
        if auto_paquetes is None and len(objetos_singulares) >= 2:
            auto_paquetes = min(len(objetos_singulares), 4)
        elif auto_paquetes is None and len(objetos_singulares) == 1:
            auto_paquetes = 1

        # Singular generico: "una silla", "un televisor", etc.
        if auto_paquetes is None and _re.search(r'\b(un|una)\s+\w+', desc_l):
            auto_paquetes = 1

        # Si no hay cantidad pero la descripcion parece un objeto unico, asumir 1 y confirmar
        if auto_paquetes is None and any(w in desc_l for w in [
            "silla", "mesa", "televisor", "tv", "monitor", "cpu", "impresora",
            "mueble", "colchon", "bicicleta", "caja", "maleta", "mochila",
            "costal", "bolsa", "paquete", "canasta", "canastas", "viveres", "víveres", "balon", "balón"
        ]):
            auto_paquetes = 1

        # Peso: 20 kg, 20 kilos, 20 kilogramos
        m_kg = _re.search(r'(\d+(?:[\.,]\d+)?)\s*(kg|kilo|kilos|kilogramo|kilogramos)\b', desc_l)
        if m_kg:
            peso_kg = float(m_kg.group(1).replace(",", "."))

            # Si el usuario dice "cada uno", "cada caja", "por cada", etc.,
            # interpretar el peso como unitario y calcular total.
            if auto_paquetes and auto_paquetes > 1 and any(x in desc_l for x in [
                "cada uno", "cada una", "cada caja", "cada paquete", "cada bulto", "por cada"
            ]):
                peso_unitario_kg = peso_kg
                peso_total_kg = peso_unitario_kg * auto_paquetes
            else:
                peso_total_kg = peso_kg

        # Tamaño por riesgo: gas lleno no debe tratarse como paquete normal
        if es_gas:
            auto_tamano = ("Carga especial / a coordinar", 4, True)

        # Tamaño por peso total
        if peso_total_kg is not None and not auto_tamano:
            if peso_total_kg < 2:
                auto_tamano = ("Paquete pequeño", 1, False)
            elif peso_total_kg <= 10:
                auto_tamano = ("Paquete mediano", 2, True)
            elif peso_total_kg <= 30:
                auto_tamano = ("Paquete grande", 3, True)
            else:
                auto_tamano = ("Carga pesada", 4, True)

        # Tamaño por palabras clave si no hubo peso ni riesgo
        if not auto_tamano:
            if any(w in desc_l for w in ["documento", "documentos", "sobre", "carta", "hoja"]):
                auto_tamano = ("Sobre/Documento", 1, False)
            elif any(w in desc_l for w in ["pequeño", "pequeno", "chico", "liviano"]):
                auto_tamano = ("Paquete pequeño", 1, False)
            elif any(w in desc_l for w in ["silla", "mesa", "mueble", "colchon", "bicicleta", "televisor", "tv", "grande"]):
                auto_tamano = ("Paquete grande", 3, True)
            elif any(w in desc_l for w in ["costal", "maleta", "bolson", "saco", "mochila", "caja", "cerveza", "cervezas", "botella", "botellas", "bebida", "bebidas", "liquido", "líquido"]):
                auto_tamano = ("Paquete mediano", 2, True)

        cuidado_msgs = []

        if es_gas:
            cuidado_msgs.append("AVISO: Balón de gas/carga riesgosa. El conductor debe confirmar si puede trasladarlo por seguridad.")

        if es_bebida:
            cuidado_msgs.append("AVISO: Requiere cuidado: frágil/líquido. Si son bebidas alcohólicas, debe entregar y recibir una persona mayor de edad.")

        cuidado_extra = "\n".join(cuidado_msgs)
        if cuidado_extra:
            cuidado_extra += "\n"

        productos_bloque = ""
        if len(productos_detectados) > 1:
            productos_bloque = "Productos detectados:\n" + "\n".join(
                [f"{i+1}. {p}" for i, p in enumerate(productos_detectados)]
            ) + "\n"
        elif len(productos_detectados) == 1:
            productos_bloque = f"Producto detectado: {productos_detectados[0]}\n"

        if auto_paquetes and len(productos_detectados) > auto_paquetes:
            auto_paquetes = min(len(productos_detectados), 4)

        if auto_paquetes and auto_tamano:
            nombre_tam, equiv_pas, req_conf = auto_tamano
            datos["enc_paquetes"] = auto_paquetes
            datos["enc_tamano"] = nombre_tam
            datos["enc_equiv_pasajeros"] = equiv_pas
            datos["enc_requiere_confirmacion"] = req_conf
            datos["enc_tarifa_base"] = None
            datos["enc_cuidado_extra"] = cuidado_extra

            if peso_unitario_kg is not None and peso_total_kg is not None:
                peso_linea = f"⚖️ Peso: {peso_unitario_kg:g} kg por paquete / total aprox: {peso_total_kg:g} kg\n"
            elif peso_total_kg is not None:
                peso_linea = f"⚖️ Peso aproximado: {peso_total_kg:g} kg\n"
            else:
                peso_linea = ""

            paquetes_linea = _paquetes_txt(auto_paquetes)

            sesion["estado"] = S_ENCOMIENDA_CONFIRM_AUTO
            await enviar_mensaje(numero,
                f"📦 *Detecté tu encomienda:*\n\n"
                f"{productos_bloque}"
                f"Descripción: {texto}\n"
                f"Cantidad: {paquetes_linea}\n"
                f"Tamaño estimado: {nombre_tam}\n"
                f"{peso_linea}"
                f"{cuidado_extra}\n"
                "¿Está correcto?\n\n"
                "1️⃣ Sí, continuar\n"
                "2️⃣ Cambiar cantidad o tamaño\n"
                "0️⃣ Volver atrás\n"
                "*menu* Ir al inicio")
        elif auto_paquetes:
            datos["enc_paquetes"] = auto_paquetes
            sesion["estado"] = S_ENCOMIENDA_TAMANO
            await enviar_mensaje(numero,
                f"📦 *{texto}*\n✅ *{auto_paquetes} paquete(s)*\n\n"
                "📐 *¿Cuál es el tamaño?*\n\n"
                "1️⃣ Sobre / Documento — S/3\n"
                "2️⃣ Paquete pequeño _(hasta 2kg)_ — S/5\n"
                "3️⃣ Paquete mediano _(2-10kg)_ — S/8\n"
                "4️⃣ Paquete grande _(10-30kg)_ — S/12\n"
                "5️⃣ Carga pesada _(+30kg)_ — A coordinar\n\n"
                "0️⃣ Volver atrás\n"
                "*menu* Ir al inicio")
        elif auto_tamano:
            nombre_tam, equiv_pas, req_conf = auto_tamano
            datos["enc_tamano"] = nombre_tam
            datos["enc_equiv_pasajeros"] = equiv_pas
            datos["enc_requiere_confirmacion"] = req_conf
            datos["enc_tarifa_base"] = None
            sesion["estado"] = S_ENCOMIENDA_BULTOS
            await enviar_mensaje(numero,
                f"📦 *{texto}*\n✅ *{nombre_tam}* detectado\n\n"
                "🔢 *¿Cuántos paquetes son?*\n\n"
                "1️⃣ Solo 1 paquete\n"
                "2️⃣ 2 paquetes\n"
                "3️⃣ 3 paquetes\n"
                "4️⃣ 4 o más paquetes\n\n"
                "0️⃣ Volver atrás\n"
                "*menu* Ir al inicio")
        else:
            sesion["estado"] = S_ENCOMIENDA_BULTOS
            await enviar_mensaje(numero,
                f"📦 *{texto}*\n\n"
                "🔢 *¿Cuántos paquetes vas a enviar?*\n\n"
                "1️⃣ Solo 1 paquete\n"
                "2️⃣ 2 paquetes\n"
                "3️⃣ 3 paquetes\n"
                "4️⃣ 4 o más paquetes\n\n"
                "0️⃣ Volver atrás\n"
                "*menu* Ir al inicio")

    elif estado == S_ENCOMIENDA_CONFIRM_AUTO:
        if texto == "1":
            sesion["estado"] = S_ENCOMIENDA_FOTO
            await enviar_mensaje(numero,
                f"✅ *{datos.get('enc_paquetes', 1)} {'paquete' if int(datos.get('enc_paquetes', 1)) == 1 else 'paquetes'} — {datos.get('enc_tamano', 'Encomienda')}*\n\n"
                f"{datos.get('enc_cuidado_extra', '')}"
                "📸 *Envía una foto de tu encomienda*\n"
                "_(Para que el conductor sepa qué va a transportar)_\n\n"
                "O escribe *omitir* si no tienes foto ahora.\n\n"
                "0️⃣ Volver atrás\n"
                "*menu* Ir al inicio")
        elif texto == "2":
            for campo in ["enc_paquetes", "enc_tamano", "enc_equiv_pasajeros", "enc_requiere_confirmacion", "enc_tarifa_base", "enc_cuidado_extra"]:
                datos.pop(campo, None)
            sesion["estado"] = S_ENCOMIENDA_BULTOS
            await enviar_mensaje(numero,
                "Perfecto, lo cambiamos manualmente.\n\n"
                "🔢 *¿Cuántos paquetes son?*\n\n"
                "1️⃣ Solo 1 paquete\n"
                "2️⃣ 2 paquetes\n"
                "3️⃣ 3 paquetes\n"
                "4️⃣ 4 o más paquetes\n\n"
                "0️⃣ Volver atrás\n"
                "*menu* Ir al inicio")
        else:
            await enviar_mensaje(numero,
                "Responde una opción:\n\n"
                "1️⃣ Sí, continuar\n"
                "2️⃣ Cambiar cantidad o tamaño\n"
                "0️⃣ Volver atrás\n"
                "*menu* Ir al inicio")

    elif estado == S_ENCOMIENDA_BULTOS:
        paquetes_map = {"1": 1, "2": 2, "3": 3, "4": 4}
        if texto not in paquetes_map:
            await enviar_mensaje(numero, "Responde del *1* al *4*.")
            return

        datos["enc_paquetes"] = paquetes_map[texto]
        datos["enc_tamano"] = "A coordinar"
        datos["enc_equiv_pasajeros"] = 2 if datos["enc_paquetes"] <= 2 else 3
        datos["enc_requiere_confirmacion"] = True
        datos["enc_tarifa_base"] = None

        paquetes_txt = "1 bulto/paquete" if datos["enc_paquetes"] == 1 else f"{datos['enc_paquetes']} bultos/paquetes"

        sesion["estado"] = S_ENCOMIENDA_FOTO
        await enviar_mensaje(numero,
            f"✅ *{paquetes_txt}*\n"
            "📦 Tamaño/precio: *a coordinar con el conductor*\n\n"
            "📸 *Envía una foto de tu encomienda*\n"
            "_(Para que el conductor sepa qué va a transportar)_\n\n"
            "O escribe *omitir* si no tienes foto ahora.\n\n"
            "0️⃣ Volver atrás\n"
            "*menu* Ir al inicio")

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
        else:
            await enviar_mensaje(numero, "📸 Envía una foto o escribe *omitir*.")
            return

        sesion["estado"] = S_ENCOMIENDA_URGENCIA
        await enviar_mensaje(numero,
            f"✅ *{datos.get('enc_tamano', 'Encomienda')}*\n\n"
            "⏰ *¿Cuándo necesitas que llegue?*\n\n"
            "1️⃣ Urgente — ahora mismo 🚀 _(+S/2)_\n"
            "2️⃣ Hoy en el día 📅\n"
            "3️⃣ Programar fecha y hora 🗓️\n\n"
            "0️⃣ Volver atrás\n"
            "*menu* Ir al inicio")

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
            await enviar_mensaje(numero,
                "Indica nombre y DNI del destinatario.\n"
                "Ejemplo: Abel Salinas, 16874530")
            return

        nombre_dest, dni_dest = extraer_nombre_dni(texto)

        if len(nombre_dest) < 3:
            await enviar_mensaje(numero,
                "Indica el nombre del destinatario.\n"
                "Ejemplo: Abel Salinas, 16874530")
            return

        datos["enc_destinatario"] = normalizar_nombre_persona(nombre_dest)
        datos["enc_destinatario_dni"] = dni_dest

        sesion["estado"] = S_ENCOMIENDA_PAGO
        recargo_urgencia = datos.get("enc_recargo", 0)

        # Tarifa siempre a coordinar — conductor la propone al ver el paquete
        datos["enc_tarifa_final"] = None

        if recargo_urgencia > 0:
            tarifa_txt = (f"El conductor confirmará el precio al aceptar\n"
                          f"   + S/{recargo_urgencia:.0f} recargo por envío urgente")
        else:
            tarifa_txt = "El conductor confirmará el precio al aceptar"

        linea_dni = f"\n🪪 DNI: *{dni_dest}*" if dni_dest else ""

        await enviar_mensaje(numero,
            f"✅ Destinatario: *{datos['enc_destinatario']}*{linea_dni}\n\n"
            f"💰 *Precio:* {tarifa_txt}\n\n"
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
            f"🔢 {paquetes} {'paquete' if int(paquetes) == 1 else 'paquetes'} | 📸 {foto_txt}\n"
            f"⏰ {datos['enc_urgencia']}\n"
            f"📍 Recojo solicitado: {datos['enc_origen']}\n"
            f"🏁 Destino: {datos['enc_destino']}\n"
            f"👤 Destinatario: {datos['enc_destinatario']}\n"
            + (f"🪪 DNI destinatario: {datos['enc_destinatario_dni']}\n" if datos.get("enc_destinatario_dni") else "")
            + f"💰 {tarifa_txt}\n"
            f"💳 {datos['pago']}\n\n"
            "1️⃣ *REGISTRAR CUPO* ✅\n2️⃣ *CANCELAR* ❌" + NAV)

    elif estado == S_ENCOMIENDA_CONFIRMAR:
        if texto == "1":
            await notificar_conductores(sesion, numero, "ENCOMIENDA")
            guardar_viaje(numero, datos, "encomienda")
            datos_servicio = {"tipo": "encomienda", "destino": datos.get("enc_destino", "destino"), "conductor": "Pendiente"}
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                "🎉 *¡Encomienda registrada!*\n\nUn conductor te contactará pronto.\n\n━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir")
        elif texto == "2":
            sesiones.pop(numero, None)
            historial_ia.pop(numero, None)
            await enviar_mensaje(numero,
                "❌ *Encomienda cancelada.*\n\n"
                "━━━━━━━━━━━━━━━━\n"
                "1️⃣ Nueva solicitud\n"
                "0️⃣ Salir")
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
        datos["_turismo_nombre_temp"] = normalizar_nombre_persona(datos.get("nombre", ""))
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
            nombre_detectado, dni_detectado = extraer_nombre_dni(txt_norm)

            if len(nombre_detectado) < 3:
                await enviar_mensaje(numero, "✍️ Escribe el nombre completo del pasajero:")
                return

            datos["_turismo_nombre_temp"] = nombre_detectado

            # Si el usuario escribió nombre + DNI juntos, registrar ambos sin volver a pedir DNI.
            if dni_detectado:
                if not dni_detectado.isdigit() or not (7 <= len(dni_detectado) <= 9):
                    await enviar_mensaje(numero, "❌ DNI inválido. Debe tener 7 u 8 dígitos, solo números:")
                    return

                lista.append({"nombre": normalizar_nombre_persona(nombre_detectado), "dni": dni_detectado})
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
                    datos["turismo_pasajeros_extra"] = "\n".join(
                        [f"{n+2}. {p['nombre']} | DNI: {p['dni']}" for n, p in enumerate(lista[1:])]
                    ) if len(lista) > 1 else ""
            else:
                datos["_turismo_paso"] = "dni"
                await enviar_mensaje(numero,
                    f"👤 *{nombre_detectado}*\n"
                    f"🪪 *DNI del pasajero {idx+1}:*\n_(8 dígitos)_")
                return
        elif paso == "dni":
            dni = txt_norm.replace(" ", "")
            if not dni.isdigit() or not (7 <= len(dni) <= 9):
                await enviar_mensaje(numero, "❌ DNI inválido. Debe tener 7 u 8 dígitos, solo números:")
                return
            nombre_temp = datos.get("_turismo_nombre_temp", "")
            lista.append({"nombre": normalizar_nombre_persona(nombre_temp), "dni": dni})
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
                datos["turismo_pasajeros_extra"] = "\n".join(
                    [f"{n+2}. {p['nombre']} | DNI: {p['dni']}" for n, p in enumerate(lista[1:])]
                ) if len(lista) > 1 else ""
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
            + (f"👥 Pasajeros adicionales:\n{datos['turismo_pasajeros_extra']}\n" if datos.get('turismo_pasajeros_extra') else "")
            + f"📅 {datos['fecha']}\n"
            f"📍 Recojo solicitado: {datos['recojo_texto']}\n"
            f"⏱️ Duración aprox: {datos['ruta_duracion']}\n"
            f"💰 Precio referencial: S/{precio_total}{nota_caral}\n"
            f"💳 {datos['pago']}"
            f"{nota_negociacion}\n\n"
            "1️⃣ *REGISTRAR CUPO* ✅\n2️⃣ *CANCELAR* ❌" + NAV)

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
        messages = body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [])
        if not messages:
            return {"status": "ok"}

        for msg in messages:
            msg_id = msg.get("id")
            if msg_id and msg_id in mensajes_procesados:
                print(f"[SKIP] mensaje duplicado {msg_id}", flush=True)
                continue
            if msg_id:
                mensajes_procesados.add(msg_id)
                if len(mensajes_procesados) > 5000:
                    mensajes_procesados.clear()

            numero = msg.get("from")
            tipo = msg.get("type")
            if not numero:
                continue

            try:
                msg_age = time.time() - int(msg.get("timestamp", 0))
            except Exception:
                msg_age = 0
            if msg_age > 300:
                print(f"[SKIP] mensaje viejo {int(msg_age)}s - ignorando", flush=True)
                continue

            if tipo == "text":
                await procesar(numero, "text", msg.get("text", {}))
            elif tipo == "location":
                await procesar(numero, "location", msg.get("location", {}))
            elif tipo == "image":
                await procesar(numero, "image", msg.get("image", {}))
            elif tipo == "audio":
                await procesar_audio(numero, msg.get("audio", {}))
            else:
                await enviar_mensaje(numero, "Solo entiendo texto, ubicaciones e imágenes 😊\n\nEscribe *menu* para comenzar.")

        return {"status": "ok"}
    except Exception as e:
        import traceback
        print(f"[ERROR] {e}", flush=True)
        print(traceback.format_exc(), flush=True)
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

@app.get("/admin/recordatorio")
async def admin_disparar_recordatorio(clave: str = ""):
    """
    Dispara el recordatorio de inicio de turno MANUALMENTE (para pruebas).
    Uso: https://barranca-movil-bot.onrender.com/admin/recordatorio?clave=TU_CLAVE
    Revisa los logs de Render: si ves [TEMPLATE] -> plantilla aprobada y enviada.
    Si ves [TEMPLATE ERROR] status=400 -> la plantilla NO está aprobada en Meta.
    """
    if clave != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Clave inválida")

    conductores = await obtener_conductores_para_recordatorio_turno()
    print(f"[ADMIN] Disparo MANUAL de recordatorio a {len(conductores)} conductor(es)", flush=True)
    await enviar_recordatorio_inicio_turno_masivo()
    return {
        "ok": True,
        "accion": "recordatorio_disparado",
        "conductores_objetivo": len(conductores),
        "detalle": [c.get("telefono") for c in conductores],
        "nota": "Revisa los logs de Render. [TEMPLATE]=enviado OK. [TEMPLATE ERROR] status=400=plantilla no aprobada."
    }


@app.get("/admin/estado-conductores")
async def admin_estado_conductores(clave: str = ""):
    """
    Muestra qué conductores figuran ACTIVOS en Google Sheets en este momento.
    Uso: https://barranca-movil-bot.onrender.com/admin/estado-conductores?clave=TU_CLAVE
    """
    if clave != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Clave inválida")

    try:
        activos = await obtener_conductores_activos_desde_sheets()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {
        "ok": True,
        "activos_en_sheets": len(activos),
        "conductores": activos,
        "nota": "ACTIVO en Sheets NO garantiza entrega de WhatsApp: la ventana de 24h "
                "solo se abre cuando el conductor le escribe al bot (ej. responde al recordatorio)."
    }


@app.get("/")
async def root():
    return {"status": "El Cuervo Bot v1.0 activo 🦅 | Barranca Móvil integrado 🚖"}
