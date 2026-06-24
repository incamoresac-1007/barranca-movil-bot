import os
import json
import time
from datetime import datetime, timedelta
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
# Margen para considerar "abierta" la ventana de 24h de WhatsApp (usamos 23h por seguridad)
VENTANA_ABIERTA_HORAS = int(os.getenv("VENTANA_ABIERTA_HORAS", "23"))

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
        guardar_estado()

@app.on_event("startup")
async def startup():
    cargar_estado()  # recuperar sesiones que sobrevivieron al reinicio
    asegurar_seed_seg()  # migrar/garantizar proveedores de Seguridad aprobados
    print(f"[BOT] Estado persistente: {len(sesiones)} sesiones activas recuperadas", flush=True)
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
S_PROV_PANEL         = "PROV_PANEL"   # panel del proveedor (sigue activo / baja)
S_PROV_BAJA          = "PROV_BAJA"    # confirmación de baja

# ── Estructuras / Calaminas (INCAMORE) ───────────────────────────────────────
S_CAL_TIPO       = "CAL_TIPO"
S_CAL_RUC        = "CAL_RUC"
S_CAL_ESPESOR    = "CAL_ESPESOR"
S_CAL_COLOR      = "CAL_COLOR"
S_CAL_LARGO      = "CAL_LARGO"
S_CAL_CANTIDAD   = "CAL_CANTIDAD"
S_CAL_ACCESORIOS = "CAL_ACCESORIOS"
S_CAL_NOMBRE     = "CAL_NOMBRE"
S_CAL_POST       = "CAL_POST"
_CAL_ESTADOS = {S_CAL_TIPO, S_CAL_RUC, S_CAL_ESPESOR, S_CAL_COLOR, S_CAL_LARGO,
                S_CAL_CANTIDAD, S_CAL_ACCESORIOS, S_CAL_NOMBRE, S_CAL_POST}
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
S_TRANSPORTE_MENU    = "TRANSPORTE_MENU"   # Submenú El Cuervo

# Gastronomía
S_GASTRO_LISTA       = "GASTRO_LISTA"      # Lista de restaurantes

# Seguridad & Saneamiento
S_SEG_SUBCATEGORIA   = "SEG_SUBCATEGORIA"  # Elige servicio
S_SEG_DESCRIPCION    = "SEG_DESCRIPCION"   # Describe la necesidad
S_SEG_UBICACION      = "SEG_UBICACION"     # Dirección
S_SEG_URGENCIA       = "SEG_URGENCIA"      # Urgente o programado
S_SEG_PROGRAMAR      = "SEG_PROGRAMAR"     # Fecha y hora si programado
S_SEG_ESPERA_COT     = "SEG_ESPERA_COT"    # Esperando cotización de Marcos
S_SEG_CONFIRMAR_COT  = "SEG_CONFIRMAR_COT" # (legacy) aceptar/rechazar 1 cotización
S_SEG_ELEGIR_COT     = "SEG_ELEGIR_COT"    # Cliente elige entre varias cotizaciones
S_SEG_CALIFICAR      = "SEG_CALIFICAR"     # Calificación post servicio

# Educación
S_EDU_PARA_QUIEN     = "EDU_PARA_QUIEN"    # ¿para ti o para un menor a tu cargo?
S_EDU_NOMBRE         = "EDU_NOMBRE"        # nombre del apoderado/solicitante
S_EDU_ALUMNO         = "EDU_ALUMNO"        # nombre del alumno (si es menor)
S_EDU_NIVEL          = "EDU_NIVEL"         # primaria/secundaria/preuniversitario
S_EDU_MATERIA        = "EDU_MATERIA"       # materia/tema (texto libre)
S_EDU_MODALIDAD      = "EDU_MODALIDAD"     # presencial / virtual
S_EDU_DIRECCION      = "EDU_DIRECCION"     # dirección (solo presencial)
S_EDU_HORAS          = "EDU_HORAS"         # cuántas horas
S_EDU_CUANDO         = "EDU_CUANDO"        # cuándo (hoy/fecha + hora)
S_EDU_CONFIRMAR      = "EDU_CONFIRMAR"     # resumen y confirmación

# ── Únete / Registro de proveedores y abonados ───────────────────────────────
S_UNETE_TIPO         = "UNETE_TIPO"        # qué tipo de proveedor es
S_UNETE_CONDICIONES  = "UNETE_CONDICIONES" # acepta condiciones de lanzamiento
S_UNETE_NOMBRE       = "UNETE_NOMBRE"      # nombre completo del responsable
S_UNETE_NEGOCIO      = "UNETE_NEGOCIO"     # nombre del negocio (gastronómico)
S_UNETE_DIRECCION    = "UNETE_DIRECCION"   # dirección (gastronómico)
S_UNETE_PLACA        = "UNETE_PLACA"       # placa (taxista/colectivero)
S_UNETE_DETALLE      = "UNETE_DETALLE"     # detalle (profesor/seguridad)
S_UNETE_CONFIRMAR    = "UNETE_CONFIRMAR"   # confirmación final

# ── Servicios Técnicos (módulo madre: soporte técnico, gasfitería, etc.) ──────
S_TEC_OFICIO         = "TEC_OFICIO"        # elige el oficio
S_TEC_PROBLEMA       = "TEC_PROBLEMA"      # describe el problema/necesidad
S_TEC_DIRECCION      = "TEC_DIRECCION"     # dónde es el servicio
S_TEC_CUANDO         = "TEC_CUANDO"        # cuándo lo necesita
S_TEC_CONFIRMAR      = "TEC_CONFIRMAR"     # resumen y confirmación
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
    S_SEG_ELEGIR_COT:       S_SEG_ESPERA_COT,
    # Educación
    S_EDU_PARA_QUIEN:       S_MENU,
    S_EDU_NOMBRE:           S_EDU_PARA_QUIEN,
    S_EDU_ALUMNO:           S_EDU_NOMBRE,
    S_EDU_NIVEL:            S_EDU_NOMBRE,
    S_EDU_MATERIA:          S_EDU_NIVEL,
    S_EDU_MODALIDAD:        S_EDU_MATERIA,
    S_EDU_DIRECCION:        S_EDU_MODALIDAD,
    S_EDU_CONFIRMAR:        S_EDU_MODALIDAD,
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
    # Educación
    S_EDU_PARA_QUIEN:     "📚 *¿Para quién es la clase?*\n1️⃣ Para mí (soy mayor de edad)\n2️⃣ Para un menor a mi cargo\n0️⃣ Volver",
    S_EDU_NOMBRE:         "🙋 *Escribe tu nombre y DNI* _(apoderado)_\nEjemplo: Victor Calixto 12345678",
    S_EDU_ALUMNO:         "👦 *¿Nombre del alumno/a?*",
    S_EDU_NIVEL:          "🎓 *¿Qué nivel?*\n1️⃣ Primaria\n2️⃣ Secundaria\n3️⃣ Preuniversitario",
    S_EDU_MATERIA:        "📖 *¿Qué materia o tema necesita reforzar?*\n_(Ej: fracciones, álgebra, comunicación)_",
    S_EDU_MODALIDAD:      "💻 *¿Cómo prefieres la clase?*\n1️⃣ Presencial (a domicilio)\n2️⃣ Virtual (Zoom)",
    S_EDU_DIRECCION:      "📍 *¿Cuál es la dirección para la clase presencial?*\n• Comparte tu ubicación 📌\n• O escribe la dirección",
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

# ── Profesores registrados (Educación) ────────────────────────────────────────
# IMPORTANTE: da de alta SOLO profesores verificados (DNI + antecedentes).
# Son ellos quienes podrán entrar a domicilios, muchas veces con menores.
#   niveles:   PRIMARIA / SECUNDARIA / PREUNIVERSITARIO
#   modalidad: presencial / virtual
PROFESORES = {
    # IMPORTANTE: solo profesores verificados (DNI + antecedentes revisados FUERA del bot).
    # No guardar aquí datos sensibles de la verificación, solo lo operativo.
    # (Vacío: los profesores se registran por Únete y se aprueban por el flujo de validación.)
}

# Tarifas de Educación por HORA en soles. Edita estos montos cuando quieras.
TARIFAS_EDU = {
    "PRIMARIA":         15,
    "SECUNDARIA":       25,
    "PREUNIVERSITARIO": 35,
}
NIVEL_LABEL = {
    "PRIMARIA": "Primaria",
    "SECUNDARIA": "Secundaria",
    "PREUNIVERSITARIO": "Preuniversitario",
}

# Clases pendientes de que un profesor acepte {numero_apoderado: {...}}
clases_pendientes: dict[str, dict] = {}
# Clases ya tomadas (evita doble asignación)
clases_tomadas: set[str] = set()

# Servicios pendientes de aceptación {numero_cliente: datos_servicio}
servicios_pendientes: dict[str, dict] = {}
# Servicios ya tomados para evitar doble asignación
servicios_tomados: set[str] = set()
calificacion_pendiente: set[str] = set()  # números con calificación ya programada
historial_viajes: dict[str, list] = {}  # historial de viajes por número
ultima_actividad: dict[str, float] = {}  # timestamp última actividad por número

# ── Persistencia en disco (sobrevive reinicios y deploys de Render) ───────────
# Render monta un disco persistente en /var/data. Si no existe (entorno local),
# usa la carpeta del proyecto. Solo lo que está bajo el mount path sobrevive.
DATA_DIR = "/var/data" if os.path.isdir("/var/data") else os.path.dirname(os.path.abspath(__file__))
ESTADO_FILE = os.path.join(DATA_DIR, "sesiones.json")


def guardar_estado():
    """Guarda el estado conversacional en disco con escritura atómica.
    Nunca lanza excepción: si algo falla, lo registra y sigue."""
    try:
        bundle = {
            "sesiones": sesiones,
            "viajes_recurrentes": viajes_recurrentes,
            "viajes_programados": viajes_programados,
            "ultima_actividad": ultima_actividad,
        }
        tmp = ESTADO_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False)
        os.replace(tmp, ESTADO_FILE)  # atómico: evita archivos corruptos
    except Exception as e:
        print(f"[PERSIST ERROR] guardar: {e}", flush=True)


def cargar_estado():
    """Carga el estado conversacional desde disco al arrancar."""
    try:
        if not os.path.exists(ESTADO_FILE):
            print(f"[PERSIST] sin estado previo en {ESTADO_FILE}, arranque limpio", flush=True)
            return
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            bundle = json.load(f)
        sesiones.update(bundle.get("sesiones", {}) or {})
        viajes_recurrentes.update(bundle.get("viajes_recurrentes", {}) or {})
        vp = bundle.get("viajes_programados", []) or []
        if isinstance(vp, list):
            viajes_programados.extend(vp)
        ultima_actividad.update(bundle.get("ultima_actividad", {}) or {})
        print(f"[PERSIST] estado cargado: {len(sesiones)} sesiones, "
              f"{len(viajes_recurrentes)} recurrentes desde {ESTADO_FILE}", flush=True)
    except Exception as e:
        print(f"[PERSIST ERROR] cargar: {e}", flush=True)
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
El Cuervo realiza estos trabajos con su PROPIA red de técnicos y proveedores:
- TRANSPORTE: taxi, colectivo, encomiendas, turismo.
- GASTRONOMÍA: restaurantes, cevicherías, delivery.
- SEGURIDAD & SANEAMIENTO: extintores, fumigación, señalización, defensa civil.
- SERVICIOS TÉCNICOS: soporte de PC/laptop/celular/redes, gasfitería, cerrajería, electricista, electrodomésticos, y SOLDADURA / trabajos en fierro (rejas, portones, estructuras, bisagras).
- EDUCACIÓN: clases particulares y reforzamiento.
REGLA CRÍTICA: NUNCA recomiendes negocios, tiendas, talleres ni técnicos externos. El Cuervo hace estos trabajos con su propia red. Si el cliente describe una necesidad, dile que El Cuervo se encarga y anímalo a hacer su solicitud aquí mismo para enviarle un especialista.
Responde en español amigable y natural, máximo 3 oraciones."""

MSG_BIENVENIDA = """👋 ¡Hola! Soy *Elizabeth*, tu asistente de *El Cuervo* 🦅
_Red inteligente de servicios locales en Barranca_

¿En qué te puedo ayudar hoy?

1️⃣ 🚖 Transporte
2️⃣ 🍽️ Gastronomía
3️⃣ 🛡️ Seguridad & Saneamiento
4️⃣ 📚 Educación
5️⃣ 🔧 Servicios Técnicos
6️⃣ 🏗️ Estructuras & Calaminas (INCAMORE)
7️⃣ 🤝 Únete / Trabaja con nosotros
0️⃣ Salir

O escribe tu consulta libremente 💬"""

MSG_TRANSPORTE_MENU = """🚖 *Transporte — El Cuervo*

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

MSG_SEG_SUBMENU = (
    "🛡️ *Seguridad & Saneamiento*\n\n"
    "¿Qué servicio necesitas?\n\n"
    "1️⃣ Extintores (venta / recarga)\n"
    "2️⃣ Señalización de seguridad\n"
    "3️⃣ Fumigación / Control de plagas\n"
    "4️⃣ Capacitación y Defensa Civil\n"
    "5️⃣ Otro servicio\n"
    "0️⃣ Volver al menú principal" + NAV
)

MSG_SEG_FUERA_HORARIO = (
    "🛡️ *Seguridad & Saneamiento*\n\n"
    "⏰ Nuestro proveedor atiende de *8:00 am a 6:00 pm*.\n\n"
    "Escríbenos mañana en ese horario y con gusto te ayudamos 🙌\n\n"
    "Escribe *menu* para volver al inicio."
)

MSG_EDU_INTRO = (
    "📚 *Educación — Reforzamiento escolar*\n\n"
    "Profesores *verificados* que te ayudan con las clases, "
    "presencial a domicilio o virtual por Zoom.\n\n"
    "👨‍👩‍👧 *¿Para quién es la clase?*\n"
    "1️⃣ Para mí (soy mayor de edad)\n"
    "2️⃣ Para un menor a mi cargo\n"
    "0️⃣ Volver al menú principal" + NAV
)

MSG_EDU_NIVEL = (
    "🎓 *¿Qué nivel necesita el alumno/a?*\n\n"
    "1️⃣ Primaria\n"
    "2️⃣ Secundaria\n"
    "3️⃣ Preuniversitario" + NAV
)

MSG_EDU_MODALIDAD = (
    "💻 *¿Cómo prefieres la clase?*\n\n"
    "1️⃣ Presencial — el profe va al domicilio 🏠\n"
    "2️⃣ Virtual — por Zoom 💻" + NAV
)

MSG_EDU_HORAS = (
    "⏱️ *¿Cuántas horas de clase?*\n"
    "_(Escribe un número, ej: 1, 2)_" + NAV
)

MSG_TARIFAS = """💰 *Tarifas El Cuervo*

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


def _limpiar_param_template(s) -> str:
    """
    Limpia un texto para usarlo como variable de plantilla de WhatsApp.
    Meta rechaza variables con saltos de línea, tabs o 4+ espacios seguidos.
    """
    return " ".join(str(s or "").split())[:400]


async def enviar_template_solicitud(to: str, p1: str, p2: str, p3: str, p4: str):
    """
    Envía la plantilla aprobada de nueva solicitud de servicio.
    Plantilla Meta: nueva_solicitud_servicio_v2  (idioma es_PE)
    Variables: {{1}}=tipo  {{2}}=cliente  {{3}}=detalle  {{4}}=numero cliente
    Se usa cuando la ventana de 24h del conductor está cerrada, para garantizar entrega.
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
            "name": "nueva_solicitud_servicio_v2",
            "language": {"code": "es_PE"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": _limpiar_param_template(p1)},
                    {"type": "text", "text": _limpiar_param_template(p2)},
                    {"type": "text", "text": _limpiar_param_template(p3)},
                    {"type": "text", "text": _limpiar_param_template(p4)},
                ]
            }]
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=payload)

        if r.status_code >= 400:
            print(f"[TEMPLATE ERROR] nueva_solicitud_servicio_v2 to={to} status={r.status_code} {r.text}", flush=True)
            return False

        print(f"[TEMPLATE] nueva_solicitud_servicio_v2 enviado to={to} status={r.status_code}", flush=True)
        return True

    except Exception as e:
        print(f"[TEMPLATE EXCEPTION] nueva_solicitud_servicio_v2 to={to} error={e}", flush=True)
        return False


async def notificar_conductor_inteligente(tel: str, msg_libre: str, tipo_label: str,
                                          cliente_str: str, detalle_corto: str, num_cliente: str):
    """
    Entrega la solicitud al conductor de la forma más confiable y económica:
    - Ventana de 24h ABIERTA (escribió hace poco) -> texto libre (gratis, con todo el detalle).
      Si el texto libre falla por cualquier motivo -> cae automáticamente a plantilla.
    - Ventana CERRADA -> plantilla aprobada directo (entrega garantizada, costo mínimo).
    """
    ahora = time.time()
    ult = ultima_actividad.get(tel, 0)
    ventana_abierta = (ahora - ult) < (VENTANA_ABIERTA_HORAS * 3600)

    if ventana_abierta:
        ok = await enviar_mensaje(tel, msg_libre)
        if ok:
            return True
        print(f"[DESPACHO] Texto libre falló a {tel}, reintentando por plantilla", flush=True)

    return await enviar_template_solicitud(tel, tipo_label, cliente_str, detalle_corto, num_cliente)


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
    """Notifica la solicitud a TODOS los proveedores de Seguridad aprobados."""
    proveedores = proveedores_seg_aprobados()
    nombre = datos.get("nombre", "Cliente")
    tel    = telefono_sin_51(numero_cliente)
    subcat = datos.get("seg_subcategoria", "")
    desc   = datos.get("seg_descripcion", "")
    ubic   = datos.get("seg_ubicacion", "")
    urgenc = datos.get("seg_urgencia", "URGENTE")
    fecha  = datos.get("seg_fecha_programada", "")

    solicitudes_seg_pendientes[numero_cliente] = datos.copy()
    cotizaciones_seg_pendientes[numero_cliente] = []  # lista de cotizaciones recibidas
    sid = registrar_servicio("SEGURIDAD", datos, numero_cliente)  # queda en el dashboard como "solicitado"
    datos["id_servicio_seg"] = sid
    if numero_cliente in solicitudes_seg_pendientes:
        solicitudes_seg_pendientes[numero_cliente]["id_servicio_seg"] = sid

    if not proveedores:
        admin = os.getenv("ADMIN_WHATSAPP", "").strip()
        if admin:
            await enviar_mensaje(admin,
                f"⚠️ Solicitud de Seguridad sin proveedores aprobados.\n"
                f"Cliente: {nombre} (+{tel}) — {subcat}: {desc} — {ubic}")
        await enviar_mensaje(numero_cliente,
            "✅ *¡Solicitud registrada!*\n\n"
            "Estamos sumando especialistas a la red. Nuestro equipo te contactará a la brevedad.\n\n"
            "Escribe *menu* si necesitas otra cosa 🦅")
        return

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
    await asyncio.gather(*[
        enviar_mensaje(p.get("telefono", ""), msg) for p in proveedores if p.get("telefono")
    ], return_exceptions=True)
    print(f"[SEG] solicitud enviada a {len(proveedores)} proveedor(es) de seguridad", flush=True)

    await enviar_mensaje(numero_cliente,
        f"✅ *¡Solicitud enviada!*\n\n"
        f"🛡️ *{subcat}*\n"
        f"📍 {ubic}\n\n"
        f"La enviamos a *{len(proveedores)} especialista(s)* de la red. "
        f"Te llegarán sus cotizaciones y *tú eliges* la que prefieras.\n\n"
        f"⏳ Tiempo estimado: *15–30 minutos*\n\n"
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


# ── Capa de direcciones (limpieza + agente + GPS) ─────────────────────────────
_VIAS_DIRECCION = {
    "calle", "ca", "ca.", "jr", "jr.", "jiron", "jirón", "av", "av.", "avenida",
    "urb", "urb.", "urbanizacion", "urbanización", "pasaje", "psje", "psje.",
    "mz", "mz.", "manzana", "barrio", "prolongacion", "prolongación", "carretera",
    "plaza", "plazuela", "parque", "sector", "caserio", "caserío", "anexo", "block",
}
_ABREV_DIRECCION = {
    "jr": "Jr.", "jr.": "Jr.", "av": "Av.", "av.": "Av.", "ca": "Ca.", "ca.": "Ca.",
    "urb": "Urb.", "urb.": "Urb.", "mz": "Mz.", "mz.": "Mz.", "psje": "Psje.",
    "psje.": "Psje.", "jiron": "Jirón",
}


def capitalizar_direccion(texto: str) -> str:
    """Capitaliza una dirección (sin la lógica de nombres que deja 'el/la' en
    minúscula). 'el lino' → 'El Lino', 'av grau' → 'Av. Grau'."""
    txt = " ".join((texto or "").strip().split())
    if not txt:
        return ""
    out = []
    for p in txt.split():
        pl = p.lower()
        if pl in _ABREV_DIRECCION:
            out.append(_ABREV_DIRECCION[pl])
        elif any(ch.isdigit() for ch in p):
            out.append(p)  # números/alfanuméricos tal cual
        else:
            out.append(p.capitalize())
    return " ".join(out)


def _direccion_pobre(texto: str) -> bool:
    """True si la dirección se ve incompleta/ambigua (vale la pena pasarla al agente)."""
    palabras = (texto or "").lower().split()
    if len(palabras) < 3:
        return True
    return not any(v in palabras for v in _VIAS_DIRECCION)


async def _agente_corregir_direccion(texto: str) -> str:
    """Agente (Claude): formatea/completa una dirección sin inventar datos. '' si no aplica."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""
    sys = (
        "Corrige y formatea una dirección en Barranca, Perú. "
        "Devuelve SOLO la dirección corregida en una línea, sin comillas ni explicaciones. "
        "Agrega el tipo de vía si es evidente (Calle, Jr., Av., Urb.), corrige mayúsculas "
        "y añade ', Barranca' si no menciona la ciudad. "
        "NO inventes números de casa ni datos que la persona no escribió; si algo no está, "
        "no lo agregues. Si ya está bien, devuélvela igual. "
        "Ejemplo: 'el lino' → 'Calle El Lino, Barranca'."
    )

    def _claude():
        return httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 80,
                  "system": sys, "messages": [{"role": "user", "content": texto}]},
            timeout=6.0,
        )

    try:
        r = await asyncio.to_thread(_claude)
        if r.status_code >= 400:
            print(f"[AGENTE ERROR] direccion status={r.status_code} {r.text[:150]}", flush=True)
            return ""
        data = r.json()
        out = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        ).strip().strip('"').strip()
        return out[:120]
    except Exception as e:
        print(f"[AGENTE ERROR] direccion: {e}", flush=True)
        return ""


async def limpiar_direccion(texto: str) -> str:
    """Capa central de direcciones de texto libre:
    1) capitaliza (gratis); 2) si se ve pobre, el agente la corrige; 3) red de seguridad."""
    base = capitalizar_direccion(texto)
    if not base:
        return ""
    if _direccion_pobre(texto):
        corregida = await _agente_corregir_direccion(texto)
        if corregida:
            print(f"[AGENTE] direccion '{texto}' -> '{corregida}'", flush=True)
            return corregida
    return base


async def direccion_desde_gps(lat, lng) -> str:
    """Convierte coordenadas a dirección legible + link de Maps. Nunca deja números crudos."""
    legible = await coords_a_direccion(lat, lng)
    link = f"https://maps.google.com/?q={lat},{lng}"
    if legible:
        return f"{legible} (📍 {link})"
    return f"Ubicación compartida 📍 {link}"

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
                if tel in _conductores_baja_set():
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
            "Aún no hay conductores *ACTIVO* en El Cuervo.\\n\\n"
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
    """Busca con autocomplete tipo Waze.
    1 resultado unico  → auto-confirma y avanza directo (sin preguntar)
    2-4 resultados     → lista, usuario elige y va DIRECTO
    0 resultados       → ACEPTA el texto libre tal cual (Barranca está mal indexado
                         en Google; la ubicación la resuelve el conductor o el GPS)."""
    sugerencias = await buscar_lugares_barranca(texto)
    unicas = _dedup_sugerencias(sugerencias) if sugerencias else []

    # Varias opciones → mostrar lista y esperar elección
    if len(unicas) >= 2:
        numeros = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        opciones_txt = "\n".join([f"{numeros[i]} {s['nombre'].split(',')[0]}" for i, s in enumerate(unicas)])
        datos["_sugerencias"] = unicas
        await enviar_mensaje(numero,
            f"📍 ¿Cuál de estas?\n\n{opciones_txt}\n\n_(O escribe otra dirección)_")
        return

    # Determinar dirección y coordenadas
    if len(unicas) == 1:
        sug = unicas[0]
        direccion, coords = await coords_de_place_id(sug["place_id"], sug["nombre"])
    else:
        # 0 resultados → aceptar lo que escribió el cliente, limpiado por la capa de direcciones
        direccion, coords = await limpiar_direccion(texto), ""

    # Avanzar según el paso
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
        km = await calcular_distancia_km(datos.get("recojo_coords", ""), coords) if coords else None
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


# ── Enrutador inteligente de Elizabeth (detección de intención) ────────────────
PALABRAS_INTENCION = {
    "TRANSPORTE": [
        "taxi", "colectivo", "encomienda", "movilidad", "carrera", "recoj", "recog",
        "llevame", "llévame", "lleva me", "viaje", "tour", "turismo", "paquete", "envio",
        "envío", "enviar", "transporte", "mototaxi", "auto", "pasaje", "traslado",
        "ir a", "voy a", "moto", "delivery de paquete"
    ],
    "GASTRONOMIA": [
        "comida", "comer", "hambre", "almuerzo", "almorzar", "cena", "cenar", "restaurante",
        "pollo", "brasa", "chifa", "ceviche", "cevicheria", "pizza", "hamburguesa",
        "delivery", "pedir comida", "antojo", "desayuno", "menu del dia", "menú del día",
        "lo que hay de comer", "tengo hambre", "quiero comer", "pollada"
    ],
    "SEGURIDAD": [
        "extintor", "extintores", "fumiga", "plaga", "señaliz", "senaliz", "señaliz",
        "defensa civil", "saneamiento", "capacitacion", "capacitación", "recarga de extintor",
        "control de plagas", "desinfecc", "desratiz", "fumigacion", "fumigación"
    ],
    "EDUCACION": [
        "clase", "clases", "profesor", "profesora", "profe", "reforzamiento", "refuerzo",
        "tutoria", "tutoría", "nivelacion", "nivelación", "matematica", "matemática", "mates",
        "tarea", "examen", "academia", "apoyo escolar", "ayuda con", "leccion", "lección",
        "preuniversitario", "preu", "secundaria", "primaria", "estudiar", "aprender",
        "comunicacion", "comunicación", "fisica", "física", "quimica", "química", "algebra",
        "álgebra", "aritmetica", "aritmética", "razonamiento", "trigonometria", "trigonometría"
    ],
    "SERVICIOS_TECNICOS": [
        "laptop", "computadora", "compu", "pc", "ordenador", "celular", "impresora",
        "no enciende", "no prende", "formatear", "virus", "pantalla", "wifi", "internet", "red",
        "camara", "cámara", "gasfit", "caño", "caños", "tuberia", "tubería", "desague", "desagüe",
        "fuga de agua", "inodoro", "grifo", "cerrajer", "cerradura", "chapa", "candado",
        "electricista", "cableado", "enchufe", "corto circuito", "tablero", "sin luz",
        "refrigerad", "lavadora", "microondas", "congeladora", "secadora",
        "soldad", "soldador", "soldar", "soldadura", "fierro", "reja", "rejas", "porton",
        "portón", "estructura metalica", "estructura metálica", "metalmecanica", "metalmecánica",
        "bisagra", "vizagra", "baranda", "reparar", "arreglar", "malogr", "averi", "tecnico", "técnico"
    ],
}


def _intencion_por_palabras(texto: str):
    """Atajo gratis e instantáneo: detecta categoría por palabras clave.
    Devuelve la categoría si hay un ganador claro, o None si no hay match o hay empate."""
    t = (texto or "").lower()
    puntajes = {cat: sum(1 for p in palabras if p in t) for cat, palabras in PALABRAS_INTENCION.items()}
    mejor = max(puntajes, key=puntajes.get)
    if puntajes[mejor] == 0:
        return None
    empatados = [c for c, v in puntajes.items() if v == puntajes[mejor]]
    return mejor if len(empatados) == 1 else None


async def clasificar_intencion(texto: str) -> str:
    """Devuelve TRANSPORTE | GASTRONOMIA | SEGURIDAD | CONSULTA.
    Primero intenta por palabras clave; si no es claro, usa Groq; si falla, CONSULTA."""
    if es_consulta_calaminas(texto):
        return "CALAMINAS"
    rapido = _intencion_por_palabras(texto)
    if rapido:
        return rapido

    sys = (
        "Eres un clasificador de intención para un asistente de servicios locales en Barranca, Perú. "
        "Lee el mensaje del cliente y responde SOLO con UNA palabra, sin explicaciones ni puntuación, "
        "eligiendo la categoría correcta:\n"
        "TRANSPORTE = taxi, colectivo, encomienda o envío de paquetes, tours o turismo, movilidad en general.\n"
        "GASTRONOMIA = pedir comida, restaurantes, delivery de comida, antojos.\n"
        "SEGURIDAD = extintores, fumigación o control de plagas, señalización, defensa civil, saneamiento.\n"
        "EDUCACION = clases particulares, reforzamiento escolar, profesor de matemática u otra materia, tutorías, apoyo con tareas o exámenes.\n"
        "SERVICIOS_TECNICOS = soporte técnico de PC/laptop/celular/impresora/red/cámaras, gasfitería, cerrajería, electricista, reparación de electrodomésticos, arreglos del hogar o negocio.\n"
        "CONSULTA = saludos, preguntas generales, dudas, o cualquier cosa que no encaje claramente en las anteriores.\n"
        "Responde únicamente una de estas palabras: TRANSPORTE, GASTRONOMIA, SEGURIDAD, EDUCACION, SERVICIOS_TECNICOS, CONSULTA."
    )

    def _groq():
        return groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": texto}],
            max_tokens=4, temperature=0.0
        )

    try:
        completion = await asyncio.wait_for(asyncio.to_thread(_groq), timeout=3.0)
        raw = (completion.choices[0].message.content or "").strip().upper()
        for cat in ("TRANSPORTE", "GASTRONOMIA", "SEGURIDAD", "EDUCACION", "SERVICIOS_TECNICOS", "CONSULTA"):
            if cat in raw:
                return cat
    except (asyncio.TimeoutError, Exception):
        pass
    return "CONSULTA"


# ── Servicios Técnicos: catálogo de oficios ──────────────────────────────────
TEC_OFICIOS = {
    "1": "Soporte técnico (PC, laptops, celulares, redes)",
    "2": "Gasfitería",
    "3": "Cerrajería",
    "4": "Electricista",
    "5": "Técnico de electrodomésticos",
    "6": "Soldadura y trabajos en fierro (rejas, portones, estructuras, bisagras)",
}

MSG_TEC_MENU = (
    "🔧 *Servicios Técnicos — El Cuervo*\n"
    "Técnicos y especialistas para tu hogar o negocio.\n\n"
    "¿Qué necesitas?\n"
    "1️⃣ 💻 Soporte técnico (PC, laptops, celulares, redes)\n"
    "2️⃣ 🔧 Gasfitería\n"
    "3️⃣ 🔑 Cerrajería\n"
    "4️⃣ ⚡ Electricista\n"
    "5️⃣ 🧊 Técnico de electrodomésticos\n"
    "6️⃣ 🔥 Soldadura y trabajos en fierro (rejas, portones, estructuras)\n"
    "0️⃣ Volver al menú\n\n"
    "_El técnico coordina el precio contigo según el trabajo._"
)


async def extraer_datos_transporte(texto: str) -> dict:
    """Agente (Claude API): extrae datos de una solicitud de transporte en texto libre.
    Devuelve solo lo identificado. Sin API key o ante error -> {}."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or len((texto or "").split()) < 4:
        return {}
    sys = (
        "Extrae datos de una solicitud de transporte en Barranca, Perú. "
        "Responde SOLO un JSON válido, sin texto adicional ni markdown, con estas claves "
        "(usa null si no se menciona):\n"
        '{"servicio": "taxi"|"colectivo"|"encomienda"|"turismo"|null, "nombre": string|null, '
        '"destino": string|null, "pasajeros": number|null, "ida_vuelta": true/false/null}\n'
        "Reglas: servicio=taxi si pide taxi/movilidad/carro; colectivo si menciona colectivo o compartido; "
        "encomienda si va a enviar un paquete/cosa; turismo si pide tour/paseo/ruta turística. "
        "destino: el lugar a donde va (ej: Puerto Supe, Lima, Plaza de Armas). "
        "nombre: solo si la persona da su nombre y apellido. "
        "pasajeros: número de personas que viajan. ida_vuelta=true si dice ida y vuelta/retorno."
    )
    def _claude():
        return httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 200, "system": sys,
                  "messages": [{"role": "user", "content": texto}]},
            timeout=6.0)
    try:
        r = await asyncio.to_thread(_claude)
        if r.status_code >= 400:
            print(f"[AGENTE-TRANS ERROR] status={r.status_code} {r.text[:200]}", flush=True)
            return {}
        data = r.json()
        raw = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        out = {}
        s = (parsed.get("servicio") or "").lower()
        mapa = {"taxi": "TAXI", "colectivo": "COLECTIVO", "encomienda": "ENCOMIENDA", "turismo": "TURISMO"}
        if s in mapa:
            out["servicio"] = mapa[s]
        if isinstance(parsed.get("nombre"), str) and len(parsed["nombre"].split()) >= 2:
            out["nombre"] = normalizar_nombre_persona(parsed["nombre"])
        if isinstance(parsed.get("destino"), str) and parsed["destino"].strip():
            out["destino_texto"] = parsed["destino"].strip()[:80]
        try:
            p = int(parsed.get("pasajeros"))
            if p > 0:
                out["pasajeros"] = p
        except (TypeError, ValueError):
            pass
        if isinstance(parsed.get("ida_vuelta"), bool):
            out["ida_vuelta"] = parsed["ida_vuelta"]
        notas = []
        if out.get("pasajeros"):
            notas.append(f"{out['pasajeros']} pasajeros")
        if out.get("ida_vuelta"):
            notas.append("ida y vuelta")
        if notas:
            out["nota_cliente"] = " · ".join(notas)
        return out
    except Exception as e:
        print(f"[AGENTE-TRANS ERROR] {e}", flush=True)
        return {}

def _trans_resumen_entendido(e: dict) -> str:
    serv = {"TAXI": "taxi", "COLECTIVO": "colectivo", "ENCOMIENDA": "encomienda",
            "TURISMO": "ruta turística"}.get(e.get("servicio"), "")
    partes = []
    if serv:
        partes.append(serv)
    if e.get("destino_texto"):
        partes.append(f"a *{e['destino_texto']}*")
    if e.get("pasajeros"):
        partes.append(f"{e['pasajeros']} pasajeros")
    if e.get("ida_vuelta"):
        partes.append("ida y vuelta")
    if not partes:
        return ""
    return "🚖 *Entendí:* " + ", ".join(partes) + ".\nCompletamos lo que falta 👇"

async def _trans_tras_nombre(numero, sesion):
    """Ramifica al paso siguiente según el servicio (reutilizable: lo llama S_NOMBRE
    y la entrada por texto libre cuando el nombre ya vino dado)."""
    datos = sesion["datos"]
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
                                for k, v in COLECTIVO_RUTAS.items()])
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
    else:
        sesion["estado"] = S_TRANSPORTE_MENU
        await enviar_mensaje(numero, MSG_TRANSPORTE_MENU)

async def _trans_post_recojo(numero, sesion):
    """Tras fijar el recojo: si el destino ya vino del texto libre, NO lo vuelve a
    preguntar (tarifa a coordinar con el conductor). Si no, pide el destino normal."""
    datos = sesion["datos"]
    if datos.get("servicio") == "TAXI" and datos.get("destino_texto") and not datos.get("destino_coords"):
        datos.update({"tarifa": "a coordinar", "tarifa_detalle": "coord. conductor", "km": 0})
        sesion["estado"] = S_PAGO
        nota = f"📝 {datos['nota_cliente']}\n" if datos.get("nota_cliente") else ""
        await enviar_mensaje(numero,
            f"📋 *Resumen:*\n\n"
            f"👤 {datos.get('nombre','')}\n📍 {datos.get('recojo_texto','')}\n"
            f"🏁 {datos['destino_texto']}\n{nota}"
            f"💰 Tarifa: *a coordinar con el conductor*\n\n"
            "💳 *¿Cómo pagas?*\n1️⃣ Efectivo\n2️⃣ Yape" + NAV)
        return
    sesion["estado"] = S_DESTINO
    await enviar_mensaje(numero,
        f"✅ Recojo: *{datos.get('recojo_texto','')}*\n\n"
        "🏁 *¿A dónde vas?*\n\n"
        "• 📌 Comparte ubicación del destino\n"
        "• ✍️ O escribe el destino")

async def _trans_entrar_texto_libre(numero, sesion, texto):
    """Entrada por texto libre a Transporte: extrae, pre-llena y pide solo lo que falta."""
    extraido = await extraer_datos_transporte(texto)
    serv = extraido.get("servicio")
    if not serv:
        await enrutar_categoria(numero, sesion, "TRANSPORTE",
            prefijo="🚖 ¡Claro! Te llevo a *Transporte*.\n\n")
        return
    datos = {"servicio": serv}
    if extraido.get("nombre"):
        datos["nombre"] = extraido["nombre"]
    if serv == "TAXI" and extraido.get("destino_texto"):
        datos["destino_texto"] = extraido["destino_texto"]
    if extraido.get("nota_cliente"):
        datos["nota_cliente"] = extraido["nota_cliente"]
    sesion["datos"] = datos
    resumen = _trans_resumen_entendido(extraido)
    if resumen:
        await enviar_mensaje(numero, resumen)
    if datos.get("nombre"):
        await _trans_tras_nombre(numero, sesion)
    else:
        sesion["estado"] = S_NOMBRE
        await enviar_mensaje(numero,
            "🙋 Para empezar, escribe tu *nombre y primer apellido*.\nEjemplo: *Ana Torres*")


async def _extraer_json_claude(texto, sys, etiqueta):
    """Llama a Claude Haiku y devuelve el JSON parseado, o {} ante error."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or len((texto or "").split()) < 4:
        return {}
    def _claude():
        return httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 200, "system": sys,
                  "messages": [{"role": "user", "content": texto}]},
            timeout=6.0)
    try:
        r = await asyncio.to_thread(_claude)
        if r.status_code >= 400:
            print(f"[AGENTE-{etiqueta} ERROR] status={r.status_code} {r.text[:160]}", flush=True)
            return {}
        data = r.json()
        raw = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[AGENTE-{etiqueta} ERROR] {e}", flush=True)
        return {}

async def extraer_datos_tecnico(texto: str) -> dict:
    sys = (
        "Extrae datos de una solicitud de servicio técnico/oficio en Barranca, Perú. "
        "Responde SOLO un JSON válido, sin markdown, con estas claves (null si no aplica):\n"
        '{"oficio": "soporte"|"gasfiteria"|"cerrajeria"|"electricista"|"electrodomesticos"|"soldadura"|null, "problema": string|null}\n'
        "soporte=PC/laptop/celular/impresora/red/cámaras/internet. gasfiteria=agua/caños/tuberías/desagüe. "
        "cerrajeria=SOLO cerraduras/chapas/llaves/candados. electricista=instalación eléctrica/enchufes/cableado/luz. "
        "electrodomesticos=refrigeradora/lavadora/microondas/cocina. "
        "soldadura=trabajos en FIERRO/metal: rejas, portones, estructuras metálicas, barandas, escaleras, "
        "y bisagras/visagras de fierro. IMPORTANTE: una puerta o bisagra de FIERRO rota o caída es SOLDADURA, "
        "NO cerrajería (aunque el cliente diga 'cerrajero'). "
        "problema: breve descripción de lo que necesita."
    )
    p = await _extraer_json_claude(texto, sys, "TEC")
    out = {}
    mapa = {"soporte": "1", "gasfiteria": "2", "cerrajeria": "3", "electricista": "4", "electrodomesticos": "5", "soldadura": "6"}
    o = (p.get("oficio") or "").lower()
    if o in mapa:
        out["oficio_idx"] = mapa[o]
    if isinstance(p.get("problema"), str) and p["problema"].strip():
        out["problema"] = p["problema"].strip()[:200]
    return out

async def extraer_datos_seguridad(texto: str) -> dict:
    sys = (
        "Extrae datos de una solicitud de seguridad/saneamiento en Barranca, Perú. "
        "Responde SOLO un JSON válido, sin markdown, con estas claves (null si no aplica):\n"
        '{"subcat": "extintores"|"senalizacion"|"fumigacion"|"capacitacion"|"otro"|null, "descripcion": string|null}\n'
        "extintores=venta/recarga de extintores. senalizacion=señales de seguridad. "
        "fumigacion=control de plagas/desinfección. capacitacion=charlas/defensa civil. "
        "descripcion: breve detalle de lo que necesita."
    )
    p = await _extraer_json_claude(texto, sys, "SEG")
    out = {}
    mapa = {"extintores": "1", "senalizacion": "2", "fumigacion": "3", "capacitacion": "4", "otro": "5"}
    s = (p.get("subcat") or "").lower()
    if s in mapa:
        out["subcat_idx"] = mapa[s]
    if isinstance(p.get("descripcion"), str) and p["descripcion"].strip():
        out["descripcion"] = p["descripcion"].strip()[:200]
    return out

def _tec_resumen_entendido(d):
    return ("🛠️ *Entendí:* " + d["tec_oficio"] + ".\nCompletamos lo que falta 👇") if d.get("tec_oficio") else ""

def _seg_resumen_entendido(d):
    return ("🛡️ *Entendí:* " + d["seg_subcategoria"] + ".\nCompletamos lo que falta 👇") if d.get("seg_subcategoria") else ""

async def _tec_entrar_texto_libre(numero, sesion, texto):
    e = await extraer_datos_tecnico(texto)
    datos = {"servicio": "SERVICIO_TECNICO"}
    if e.get("oficio_idx") in TEC_OFICIOS:
        datos["tec_oficio"] = TEC_OFICIOS[e["oficio_idx"]]
    prob = e.get("problema") or (texto or "").strip()
    if len(prob) >= 4:
        datos["tec_problema"] = prob
    sesion["datos"] = datos
    resumen = _tec_resumen_entendido(datos)
    if resumen:
        await enviar_mensaje(numero, resumen)
    if datos.get("tec_oficio"):
        sesion["estado"] = S_TEC_DIRECCION
        await enviar_mensaje(numero,
            "📍 ¿Dónde sería el servicio?\n• Comparte tu ubicación 📌\n• O escribe la dirección")
    else:
        sesion["estado"] = S_TEC_OFICIO
        await enviar_mensaje(numero, "🔧 Entendido. Te llevo a *Servicios Técnicos*.\n\n" + MSG_TEC_MENU)

async def _seg_entrar_texto_libre(numero, sesion, texto):
    e = await extraer_datos_seguridad(texto)
    datos = {}
    if e.get("subcat_idx") in SEG_SUBCATEGORIAS:
        datos["seg_subcategoria"] = SEG_SUBCATEGORIAS[e["subcat_idx"]]
    desc = e.get("descripcion") or (texto or "").strip()
    if len(desc) >= 5:
        datos["seg_descripcion"] = desc
    sesion["datos"] = datos
    resumen = _seg_resumen_entendido(datos)
    if resumen:
        await enviar_mensaje(numero, resumen)
    if datos.get("seg_subcategoria"):
        sesion["estado"] = S_SEG_UBICACION
        await enviar_mensaje(numero,
            "📍 *¿Cuál es la dirección donde se realizará el servicio?*\n"
            "• Comparte tu ubicación 📌\n"
            "• O escribe la dirección completa" + NAV)
    else:
        sesion["estado"] = S_SEG_SUBCATEGORIA
        await enviar_mensaje(numero, "🛡️ Entendido. Te llevo a *Seguridad & Saneamiento*.\n\n" + MSG_SEG_SUBMENU)


async def enrutar_categoria(numero: str, sesion: dict, categoria: str, prefijo: str = "") -> bool:
    """Lleva al cliente al flujo de la categoría detectada.
    Fuente única de verdad para el menú principal (la usan tanto las opciones
    numéricas como el enrutador inteligente por texto libre)."""
    if categoria == "TRANSPORTE":
        sesion["estado"] = S_TRANSPORTE_MENU
        await enviar_mensaje(numero, prefijo + MSG_TRANSPORTE_MENU)
        return True
    if categoria == "GASTRONOMIA":
        sesion["estado"] = S_GASTRO_LISTA
        await enviar_mensaje(numero, prefijo + MSG_GASTRO_PROXIMAMENTE)
        return True
    if categoria == "SEGURIDAD":
        # SASI SAC recibe solicitudes 24/7 (sin restricción de horario)
        sesion["estado"] = S_SEG_SUBCATEGORIA
        await enviar_mensaje(numero, prefijo + MSG_SEG_SUBMENU)
        return True
    if categoria == "EDUCACION":
        sesion["estado"] = S_EDU_PARA_QUIEN
        sesion["datos"] = {"servicio": "EDUCACION"}
        await enviar_mensaje(numero, prefijo + MSG_EDU_INTRO)
        return True
    if categoria == "SERVICIOS_TECNICOS":
        sesion["estado"] = S_TEC_OFICIO
        sesion["datos"] = {"servicio": "SERVICIO_TECNICO"}
        await enviar_mensaje(numero, prefijo + MSG_TEC_MENU)
        return True
    return False


def tarifa_hora_edu(nivel: str) -> int:
    """Tarifa por hora del nivel (S/)."""
    return TARIFAS_EDU.get(nivel, 0)


async def _edu_siguiente_paso(numero: str, sesion: dict):
    """Motor del flujo de Educación: detecta el primer dato faltante y pide solo ese.
    Permite que el agente pre-llene campos y el bot salte directo a lo que falta."""
    d = sesion["datos"]

    # 1) ¿Para quién?
    if d.get("edu_para_menor") is None:
        sesion["estado"] = S_EDU_PARA_QUIEN
        await enviar_mensaje(numero, MSG_EDU_INTRO)
        return

    # 2) Nombre + DNI del apoderado/solicitante
    if not d.get("nombre") or not d.get("edu_dni"):
        sesion["estado"] = S_EDU_NOMBRE
        aviso = ("👨‍👩‍👧 Como la clase es para un menor, *tú (apoderado) coordinas y debes "
                 "estar presente durante la clase*.\n\n" if d.get("edu_para_menor") else "")
        await enviar_mensaje(numero,
            aviso + "🙋 Escribe tu *nombre y DNI*.\nEjemplo: *Victor Calixto 12345678*" + NAV)
        return

    # 3) Nombre del alumno (solo si es para un menor)
    if d.get("edu_para_menor") and not d.get("edu_alumno"):
        sesion["estado"] = S_EDU_ALUMNO
        await enviar_mensaje(numero, "👦 ¿Cuál es el *nombre del alumno/a*?" + NAV)
        return
    if not d.get("edu_para_menor") and not d.get("edu_alumno"):
        d["edu_alumno"] = d.get("nombre", "")

    # 4) Nivel
    if not d.get("edu_nivel"):
        sesion["estado"] = S_EDU_NIVEL
        verbo = "necesita el alumno/a" if d.get("edu_para_menor") else "necesitas"
        await enviar_mensaje(numero,
            f"🎓 *¿Qué nivel {verbo}?*\n"
            "1️⃣ Primaria\n2️⃣ Secundaria\n3️⃣ Preuniversitario" + NAV)
        return

    # 5) Materia / tema
    if not d.get("edu_materia"):
        sesion["estado"] = S_EDU_MATERIA
        verbo = "necesita" if d.get("edu_para_menor") else "necesitas"
        await enviar_mensaje(numero,
            f"📖 ¿Qué *materia o tema* {verbo} reforzar?\n"
            "_(Ej: fracciones, álgebra, comunicación, preparación de examen)_" + NAV)
        return

    # 6) Modalidad
    if not d.get("edu_modalidad"):
        sesion["estado"] = S_EDU_MODALIDAD
        await enviar_mensaje(numero, MSG_EDU_MODALIDAD)
        return

    # 7) Dirección (solo presencial)
    if d.get("edu_modalidad") == "presencial" and not d.get("edu_direccion"):
        sesion["estado"] = S_EDU_DIRECCION
        await enviar_mensaje(numero,
            "📍 ¿Cuál es la *dirección* para la clase presencial?\n"
            "• Comparte tu ubicación 📌\n• O escribe la dirección" + NAV)
        return

    # 8) Todo listo → resumen
    await _edu_mostrar_resumen(numero, sesion)


def _edu_resumen_entendido(e: dict) -> str:
    """Frase corta confirmando lo que el agente entendió de la frase libre."""
    partes = []
    if e.get("edu_para_menor") is True:
        partes.append("clase para un menor")
    elif e.get("edu_para_menor") is False:
        partes.append("clase para ti")
    if e.get("edu_nivel"):
        partes.append(NIVEL_LABEL.get(e["edu_nivel"], e["edu_nivel"]).lower())
    if e.get("edu_materia"):
        partes.append(e["edu_materia"])
    if e.get("edu_modalidad"):
        partes.append("presencial" if e["edu_modalidad"] == "presencial" else "virtual")
    if not partes:
        return ""
    return "📚 Entendí: *" + ", ".join(partes) + "*. Completemos lo que falta 👇"


async def extraer_datos_educacion(texto: str) -> dict:
    """Agente (Claude API): extrae datos de una frase libre de Educación.
    Devuelve solo lo identificado con confianza. Sin API key o ante error → {}.
    Convive con el flujo: lo que no extraiga, el bot lo preguntará igual."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or len((texto or "").split()) < 4:
        return {}

    sys = (
        "Extrae datos de una solicitud de clase particular en Barranca, Perú. "
        "Responde SOLO un JSON válido, sin texto adicional ni markdown, con estas claves "
        "(usa null si no se menciona):\n"
        '{"para_menor": true/false/null, "nivel": "PRIMARIA"|"SECUNDARIA"|"PREUNIVERSITARIO"|null, '
        '"materia": string|null, "modalidad": "presencial"|"virtual"|null}\n'
        "Reglas: para_menor=true si la clase es para un hijo, sobrino o alumno menor; "
        "false si la persona dice que es para sí misma; null si no está claro. "
        "nivel: 1ro-6to de primaria=PRIMARIA; 1ro-5to de secundaria=SECUNDARIA; "
        "ciclo/preu/academia/UNI=PREUNIVERSITARIO. "
        "modalidad: 'a domicilio'/'en mi casa'/'presencial'=presencial; "
        "'virtual'/'zoom'/'online'/'por internet'=virtual. "
        "materia: el curso o tema (ej: matematica, fracciones, algebra, comunicacion)."
    )

    def _claude():
        return httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 200,
                "system": sys,
                "messages": [{"role": "user", "content": texto}],
            },
            timeout=6.0,
        )

    try:
        r = await asyncio.to_thread(_claude)
        if r.status_code >= 400:
            print(f"[AGENTE ERROR] status={r.status_code} {r.text[:200]}", flush=True)
            return {}
        data = r.json()
        raw = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        ).strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)

        out = {}
        if isinstance(parsed.get("para_menor"), bool):
            out["edu_para_menor"] = parsed["para_menor"]
        if parsed.get("nivel") in ("PRIMARIA", "SECUNDARIA", "PREUNIVERSITARIO"):
            out["edu_nivel"] = parsed["nivel"]
        if isinstance(parsed.get("materia"), str) and parsed["materia"].strip():
            out["edu_materia"] = parsed["materia"].strip()[:80]
        if parsed.get("modalidad") in ("presencial", "virtual"):
            out["edu_modalidad"] = parsed["modalidad"]
        print(f"[AGENTE] educacion extrajo: {out}", flush=True)
        return out
    except (asyncio.TimeoutError, Exception) as e:
        print(f"[AGENTE ERROR] extraer_datos_educacion: {e}", flush=True)
        return {}


async def _edu_mostrar_resumen(numero: str, sesion: dict):
    """Muestra el resumen de la solicitud de clase y pasa a confirmación."""
    d = sesion["datos"]
    sesion["estado"] = S_EDU_CONFIRMAR
    nivel = d.get("edu_nivel", "PRIMARIA")
    modalidad = d.get("edu_modalidad", "virtual")
    resumen = (
        "📋 *Confirma tu solicitud de clase*\n\n"
        + (f"👤 Apoderado: {d.get('nombre','')} (DNI {d.get('edu_dni','')})\n"
           f"🎓 Alumno: {d.get('edu_alumno','')}\n"
           if d.get('edu_para_menor') else
           f"👤 Estudiante: {d.get('nombre','')} (DNI {d.get('edu_dni','')}) — mayor de edad\n")
        + f"📚 Nivel: {NIVEL_LABEL.get(nivel, nivel)}\n"
        f"📖 Tema: {d.get('edu_materia','')}\n"
        f"💻 Modalidad: {'Presencial (domicilio)' if modalidad=='presencial' else 'Virtual (Zoom)'}\n"
        + (f"📍 Dirección: {d.get('edu_direccion','')}\n" if modalidad == 'presencial' else "")
        + f"💰 *Tarifa: S/{tarifa_hora_edu(nivel)} por hora*\n"
        "_(El horario y la duración los coordinas con el profesor)_\n\n"
        + ("⚠️ En clases presenciales el apoderado debe estar presente durante toda la clase.\n\n"
           if modalidad == 'presencial' and d.get('edu_para_menor') else "")
        + "1️⃣ Confirmar y buscar profesor\n2️⃣ Cancelar" + NAV
    )
    await enviar_mensaje(numero, resumen)


def _profesores_aprobados_tel():
    """Teléfonos de profesores APROBADOS por el flujo 'Trabaja con nosotros'."""
    try:
        return {p.get("telefono", "") for p in cargar_proveedores_aprobados("profesor") if p.get("telefono")}
    except Exception:
        return set()

def _profe_info(numero: str) -> dict:
    """Datos del profesor, venga de la lista hardcodeada o de los aprobados por Únete."""
    if numero in PROFESORES:
        return PROFESORES[numero]
    for p in cargar_proveedores_aprobados("profesor"):
        if p.get("telefono") == numero:
            return {"nombre": p.get("nombre", "Profesor verificado")}
    return {"nombre": "Profesor verificado"}

def _es_profesor(numero: str) -> bool:
    return numero in PROFESORES or numero in _profesores_aprobados_tel()


async def notificar_profesores(sesion: dict, numero_apoderado: str):
    """Despacha la solicitud de clase a los profesores que cubren el nivel y la
    modalidad pedidos. Reusa el envío inteligente (texto libre / plantilla)."""
    d = sesion["datos"]
    nivel = d.get("edu_nivel", "PRIMARIA")
    modalidad = d.get("edu_modalidad", "virtual")
    tarifa = tarifa_hora_edu(nivel)
    alumno = d.get("edu_alumno") or d.get("nombre", "Alumno")

    candidatos = [
        tel for tel, info in PROFESORES.items()
        if nivel in info.get("niveles", []) and modalidad in info.get("modalidad", [])
    ]
    # Profesores APROBADOS por 'Trabaja con nosotros' (se autoseleccionan con ACEPTO).
    for _p in cargar_proveedores_aprobados("profesor"):
        _tel = _p.get("telefono", "")
        if _tel and _tel not in candidatos:
            candidatos.append(_tel)

    if not candidatos:
        await enviar_mensaje(numero_apoderado,
            "😔 *Por ahora no tenemos un profesor disponible* para ese nivel y modalidad.\n\n"
            "Hemos registrado tu solicitud y te contactaremos apenas haya un profe disponible.\n\n"
            "Escribe *menu* para volver al inicio.")
        if "sheets_evento" in globals():
            asyncio.create_task(sheets_evento("add_alerta", {
                "id_servicio": f"EDU-SIN-PROFE-{int(time.time())}",
                "tipo_alerta": "EDUCACION_SIN_PROFESOR",
                "prioridad": "ALTA",
                "descripcion": (f"Solicitud de clase sin profe disponible. Nivel={nivel} "
                                f"Modalidad={modalidad} Apoderado=+{numero_apoderado} "
                                f"Tema={d.get('edu_materia','')}"),
                "requiere_accion": "SI",
                "estado_alerta": "ABIERTA",
                "responsable": "Operador"
            }))
        return

    msg = (
        f"📚 *NUEVA CLASE — {NIVEL_LABEL.get(nivel, nivel)}*\n\n"
        + (f"👤 Apoderado: {d.get('nombre','N/A')} | 📱 +{numero_apoderado}\n"
           f"🎓 Alumno: {alumno}\n"
           if d.get('edu_para_menor') else
           f"👤 Estudiante: {d.get('nombre','N/A')} (mayor de edad) | 📱 +{numero_apoderado}\n")
        + f"📖 Tema: {d.get('edu_materia','reforzamiento')}\n"
        f"💻 Modalidad: {'Presencial (domicilio)' if modalidad=='presencial' else 'Virtual (Zoom)'}\n"
        + (f"📍 Dirección: {d.get('edu_direccion','')}\n" if modalidad == 'presencial' else "")
        + f"💰 Tarifa: S/{tarifa}/hora\n\n"
        + ("⚠️ *Clase presencial:* el apoderado estará presente durante toda la clase.\n\n"
           if modalidad == 'presencial' and d.get('edu_para_menor') else "")
        + "Para tomar la clase responde: *ACEPTO* ✅"
    )

    cliente_str = _limpiar_param_template(f"{d.get('nombre','Apoderado')} | +{numero_apoderado}")
    detalle_corto = _limpiar_param_template(
        f"{NIVEL_LABEL.get(nivel, nivel)} | {d.get('edu_materia','reforzamiento')} | "
        f"{'Presencial' if modalidad=='presencial' else 'Virtual'} | S/{tarifa}/h"
    )

    clases_pendientes[numero_apoderado] = {
        "tipo": "EDUCACION",
        "estado": "PENDIENTE_PROFESOR",
        "datos": d.copy(),
        "creado_en": time.time(),
        "profesores_notificados": list(candidatos),
    }

    tareas = [
        notificar_conductor_inteligente(tel, msg, "CLASE", cliente_str, detalle_corto, numero_apoderado)
        for tel in candidatos
    ]
    await asyncio.gather(*tareas)

    await enviar_mensaje(numero_apoderado,
        "✅ *¡Solicitud enviada!*\n\n"
        f"Estamos contactando a nuestros profesores de *{NIVEL_LABEL.get(nivel, nivel)}*.\n"
        "Apenas uno acepte, te aviso con sus datos. 📚\n\n"
        "Escribe *menu* para volver al inicio.")


async def _asignar_clase_a_profe(numero_profe: str, num_ap_full: str):
    """Asigna una clase pendiente a un profesor y notifica a ambos + cierra a los demás."""
    clases_tomadas.add(num_ap_full)
    clase = clases_pendientes.pop(num_ap_full)
    profe = _profe_info(numero_profe)
    marcar_servicio_atendido(num_ap_full, profe.get("nombre", ""))
    d = clase["datos"]
    modalidad = d.get("edu_modalidad", "virtual")
    nivel_lbl = NIVEL_LABEL.get(d.get("edu_nivel"), d.get("edu_nivel", ""))

    # Avisar a los demás profes que ya se tomó
    for tel in clase.get("profesores_notificados", []):
        if tel != numero_profe:
            await enviar_mensaje(tel,
                f"❌ *Clase tomada*\nLa clase de {d.get('edu_alumno','el alumno')} "
                f"ya fue tomada por otro profesor.")

    # Confirmar al profesor con los datos del apoderado
    await enviar_mensaje(numero_profe,
        f"✅ *¡Clase asignada para ti!*\n\n"
        + (f"👤 Apoderado: {d.get('nombre','N/A')} (DNI {d.get('edu_dni','')}) | 📱 +{num_ap_full}\n"
           f"🎓 Alumno: {d.get('edu_alumno','')}\n"
           if d.get('edu_para_menor') else
           f"👤 Estudiante: {d.get('nombre','N/A')} (DNI {d.get('edu_dni','')}, mayor de edad) | 📱 +{num_ap_full}\n")
        + f"📚 Nivel: {nivel_lbl}\n"
        f"📖 Tema: {d.get('edu_materia','')}\n"
        f"💻 Modalidad: {'Presencial' if modalidad=='presencial' else 'Virtual (Zoom)'}\n"
        + (f"📍 Dirección: {d.get('edu_direccion','')}\n" if modalidad == 'presencial' else "")
        + f"💰 Tarifa: S/{tarifa_hora_edu(d.get('edu_nivel'))}/hora\n\n"
        + ("⚠️ El apoderado estará presente durante toda la clase.\n"
           "💡 Para trasladarte puedes pedir un taxi por este mismo bot. 🚖\n\n"
           if modalidad == 'presencial' and d.get('edu_para_menor') else
           ("💡 Para trasladarte puedes pedir un taxi por este mismo bot. 🚖\n\n"
            if modalidad == 'presencial' else
            "Coordina el enlace de *Zoom* directamente con el estudiante.\n\n"))
        + "Contacta para acordar *horario y duración*.")

    # Notificar al apoderado con los datos del profesor
    await enviar_mensaje(num_ap_full,
        f"📚 *¡Profesor asignado!*\n\n"
        f"👨‍🏫 {profe.get('nombre','Profesor verificado')}\n"
        f"📱 Contacto: +{numero_profe}\n"
        f"📖 {d.get('edu_materia','')} — {nivel_lbl}\n"
        f"💻 {'Presencial (domicilio)' if modalidad=='presencial' else 'Virtual (Zoom)'}\n"
        f"💰 Tarifa: S/{tarifa_hora_edu(d.get('edu_nivel'))}/hora\n\n"
        + ("El profesor te contactará para coordinar *horario y duración*. "
           "Recuerda *estar presente* durante la clase.\n\n"
           if modalidad == 'presencial' and d.get('edu_para_menor') else
           "El profesor te contactará para coordinar *horario y duración*.\n\n")
        + "Escribe *menu* para otra solicitud.")

    print(f"[EDU ASIGNADA] apoderado=+{num_ap_full} profe={profe.get('nombre','')} "
          f"nivel={d.get('edu_nivel')} tarifa=S/{tarifa_hora_edu(d.get('edu_nivel'))}/h", flush=True)

    async def _limpiar_clase_tomada():
        await asyncio.sleep(300)
        clases_tomadas.discard(num_ap_full)
    asyncio.create_task(_limpiar_clase_tomada())

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
    """Avisa al asesor (por correo) que un cliente pidió que lo llamen.
    Incluye el número listo para marcar (botón Llamar en el celular)."""
    tel = f"+{numero}"
    asunto = f"📞 Cliente quiere que lo llames — {tel}"
    consulta_txt = (consulta or "(sin detalle)").strip()
    texto = (
        f"Un cliente de El Cuervo pidió hablar con un asesor.\n\n"
        f"Número (WhatsApp): {tel}\n"
        f"Consulta: {consulta_txt}\n\n"
        f"Llámalo cuando puedas. (Marca {tel})"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#222">
      <h2 style="color:#A6452F;margin-bottom:2px">El Cuervo</h2>
      <p style="margin-top:0;color:#666">Un cliente pidió que lo llamen 📞</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <tr><td style="padding:5px 0;color:#666">Número</td><td><b>{tel}</b></td></tr>
        <tr><td style="padding:5px 0;color:#666">Consulta</td><td>{consulta_txt}</td></tr>
      </table>
      <div style="margin:22px 0">
        <a href="tel:{tel}" style="display:inline-block;background:#1faa59;color:#fff;
           text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:bold">📞 Llamar al cliente</a>
      </div>
      <p style="color:#999;font-size:12px">Toca el botón desde tu celular para llamar directo. — INCAMORE / El Cuervo</p>
    </div>"""
    try:
        await asyncio.to_thread(_enviar_correo_sync, asunto, html, texto)
    except Exception as e:
        print(f"[OPERADOR-CORREO ERROR] {e}", flush=True)
    # Respaldo opcional por WhatsApp si hay un operador configurado distinto al bot
    if OPERADOR_WA:
        try:
            await enviar_mensaje(OPERADOR_WA,
                f"📞 *Cliente quiere que lo llames*\n{tel}\n_{consulta_txt}_")
        except Exception:
            pass


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
               "Para tomar el servicio responde: *ACEPTO* ✅")
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
               "Para tomar el servicio responde: *ACEPTO* ✅")
    elif tipo == "COLECTIVO":
        msg = (f"🚌 *NUEVO COLECTIVO*\n\n"
               f"👤 {d.get('nombre')} | 📱 +{numero_cliente}\n"
               f"{d.get('colectivo_emoji','')} {d.get('colectivo_ruta')}\n"
               f"🕐 {d.get('colectivo_horario')}\n"
               f"👥 {d.get('colectivo_asientos')} asiento(s) confirmados\n"
               f"📍 Recojo solicitado: {d.get('colectivo_recojo')}\n"
               f"💰 S/{d.get('colectivo_total')} | 💳 {d.get('colectivo_pago')}\n\n"
               f"💡 Puedes completar el cupo en el paradero\n\n"
               "Para tomar el servicio responde: *ACEPTO* ✅")
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
               "Para tomar el servicio responde: *ACEPTO* ✅")
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

    # ── Parámetros para plantilla de respaldo (cuando la ventana de 24h está cerrada) ──
    tipo_label = {
        "TAXI": "TAXI", "ENCOMIENDA": "ENCOMIENDA",
        "COLECTIVO": "COLECTIVO", "TURISMO": "TOUR"
    }.get(tipo, "SERVICIO")
    cliente_str = _limpiar_param_template(f"{d.get('nombre','Cliente')} | +{numero_cliente}")

    if tipo == "TAXI":
        detalle_corto = f"Recojo: {d.get('recojo_texto','')} | Destino: {d.get('destino_texto','')} | {tarifa_txt} | {d.get('pago','')}"
    elif tipo == "ENCOMIENDA":
        detalle_corto = f"{d.get('enc_descripcion','')} | {d.get('enc_origen','')} a {d.get('enc_destino','')} | {tarifa_txt} | {d.get('pago','')}"
    elif tipo == "COLECTIVO":
        detalle_corto = f"{d.get('colectivo_ruta','')} | {d.get('colectivo_horario','')} | {d.get('colectivo_asientos','')} asiento(s) | S/{d.get('colectivo_total','')}"
    elif tipo == "TURISMO":
        detalle_corto = f"{d.get('ruta_nombre','')} | {d.get('fecha','')} | {d.get('personas','')} pax | {precio_txt}"
    else:
        detalle_corto = "Nueva solicitud de servicio"
    detalle_corto = _limpiar_param_template(detalle_corto)

    # Envío PARALELO con lógica inteligente de ventana 24h
    # (texto libre si está abierta; plantilla si está cerrada -> garantiza entrega)
    tareas = [
        notificar_conductor_inteligente(
            num_conductor, msg, tipo_label, cliente_str, detalle_corto, numero_cliente
        )
        for num_conductor in conductores_disponibles
    ]
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
    """Separa nombre y DNI si el usuario escribe ambos juntos. Ej: 'Victor Calixto, 15862130'."""
    import re
    raw = (texto or "").strip()
    m = re.search(r"\b(\d{7,9})\b", raw)
    if not m:
        return normalizar_nombre_persona(raw.strip(" ,.-")), ""

    dni = m.group(1)
    nombre = (raw[:m.start()] + " " + raw[m.end():]).strip(" ,.-")
    nombre = " ".join(nombre.split())

    return normalizar_nombre_persona(nombre), dni


# ── Únete / Registro de proveedores ──────────────────────────────────────────
UNETE_TIPOS = {
    "1": "Negocio gastronómico (restaurante/cevichería/chifa)",
    "2": "Taxista",
    "3": "Colectivero",
    "4": "Profesor",
    "5": "Seguridad y Defensa Civil",
    "6": "Técnico / Especialista",
}

MSG_UNETE_CONDICIONES = (
    "📋 *Condiciones — Etapa de Lanzamiento*\n\n"
    "✅ El registro y la permanencia son *GRATIS durante el lanzamiento*.\n"
    "✅ Recibes *promoción y publicidad* de tu negocio en nuestras redes.\n"
    "📌 Al terminar el lanzamiento se aplicará una *tarifa por el servicio*, "
    "que te comunicaremos *con anticipación*. Tu permanencia es *voluntaria*: "
    "si no deseas continuar, te das de baja sin compromiso.\n"
    "📌 Tu registro será *revisado y validado* por nuestro equipo antes de activarte.\n\n"
    "Responde *ACEPTO* para continuar, o *0* para volver."
)

PROVEEDORES_FILE = os.path.join(DATA_DIR, "proveedores.json")
CONDUCTORES_BAJA_FILE = os.path.join(DATA_DIR, "conductores_baja.json")

# Motivos de rechazo predefinidos (código -> texto que recibe el candidato)
MOTIVOS_RECHAZO = {
    "datos": "los datos proporcionados están incompletos o no se pudieron verificar",
    "documentos": "faltan documentos o no se pudo validar tus antecedentes",
    "requisitos": "por ahora no cumple con los requisitos de la red",
    "zona": "por el momento no cubrimos tu zona o rubro",
    "otro": "no se ajusta al perfil que buscamos en esta etapa",
}
SERVICIOS_FILE = os.path.join(DATA_DIR, "servicios.json")

CATEGORIA_SERVICIO = {
    "TAXI": "Transporte", "COLECTIVO": "Transporte", "ENCOMIENDA": "Transporte",
    "TURISMO": "Turismo", "EDUCACION": "Educación", "SEGURIDAD": "Seguridad",
    "SERVICIO_TECNICO": "Servicios Técnicos",
}


def _monto_de(datos: dict) -> float:
    """Extrae un monto numérico de los datos del servicio (0 si es 'a coordinar')."""
    for k in ("tarifa", "precio", "monto", "tarifa_total"):
        v = datos.get(k)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.replace("S/", "").replace(",", ".").strip())
            except (ValueError, AttributeError):
                continue
    return 0.0


def registrar_servicio(tipo_servicio: str, datos: dict, numero: str) -> str:
    """Registra un servicio solicitado en disco para el dashboard. Devuelve su id."""
    try:
        data = []
        if os.path.exists(SERVICIOS_FILE):
            with open(SERVICIOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or []
        ahora = datetime.now()
        sid = f"SV-{int(time.time()*1000) % 10000000}"
        registro = {
            "id": sid, "tipo": tipo_servicio,
            "categoria": CATEGORIA_SERVICIO.get(tipo_servicio, "Otro"),
            "cliente": datos.get("nombre", ""), "telefono": numero,
            "monto": _monto_de(datos), "estado": "solicitado", "proveedor": "",
            "oficio": datos.get("tec_oficio", ""),
            "fecha": ahora.strftime("%Y-%m-%d %H:%M:%S"), "dia": ahora.strftime("%Y-%m-%d"),
        }
        data.append(registro)
        if len(data) > 5000:
            data = data[-5000:]
        tmp = SERVICIOS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, SERVICIOS_FILE)
        print(f"[SERVICIO] {tipo_servicio} registrado {sid} cliente={numero} monto={registro['monto']}", flush=True)
        return sid
    except Exception as e:
        print(f"[SERVICIO ERROR] registrar: {e}", flush=True)
        return ""


def marcar_servicio_atendido(numero_cliente: str, proveedor: str = ""):
    """Marca el servicio 'solicitado' más reciente de un cliente como 'atendido'."""
    try:
        if not os.path.exists(SERVICIOS_FILE):
            return
        with open(SERVICIOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or []
        for r in reversed(data):
            if r.get("telefono") == numero_cliente and r.get("estado") == "solicitado":
                r["estado"] = "atendido"
                if proveedor:
                    r["proveedor"] = proveedor
                break
        tmp = SERVICIOS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, SERVICIOS_FILE)
    except Exception as e:
        print(f"[SERVICIO ERROR] atender: {e}", flush=True)


def guardar_proveedor(registro: dict):
    """Agrega un registro de proveedor al archivo en disco (lista JSON)."""
    try:
        data = []
        if os.path.exists(PROVEEDORES_FILE):
            with open(PROVEEDORES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or []
        data.append(registro)
        tmp = PROVEEDORES_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, PROVEEDORES_FILE)
        print(f"[PROVEEDOR] registrado: {registro.get('tipo')} - {registro.get('nombre')} ({registro.get('telefono')})", flush=True)
        return len(data)
    except Exception as e:
        print(f"[PROVEEDOR ERROR] guardar: {e}", flush=True)
        return None


def actualizar_estado_proveedor(pid: str, nuevo_estado: str):
    """Cambia el estado de un proveedor (por id) en disco. Devuelve el registro o None."""
    try:
        if not os.path.exists(PROVEEDORES_FILE):
            return None
        with open(PROVEEDORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or []
        encontrado = None
        for r in data:
            if r.get("id") == pid:
                r["estado"] = nuevo_estado
                r["validado_el"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                encontrado = r
                break
        if not encontrado:
            return None
        tmp = PROVEEDORES_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, PROVEEDORES_FILE)
        print(f"[PROVEEDOR] {pid} -> {nuevo_estado}", flush=True)
        return encontrado
    except Exception as e:
        print(f"[PROVEEDOR ERROR] actualizar: {e}", flush=True)
        return None


def cargar_proveedores_aprobados(filtro_tipo: str = "") -> list:
    """Devuelve los proveedores APROBADOS (opcionalmente filtrando por texto del tipo)."""
    try:
        if not os.path.exists(PROVEEDORES_FILE):
            return []
        with open(PROVEEDORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or []
        out = [r for r in data if r.get("estado") == "APROBADO"]
        if filtro_tipo:
            ft = filtro_tipo.lower()
            out = [r for r in out if ft in (r.get("tipo", "").lower())]
        return out
    except Exception as e:
        print(f"[PROVEEDOR ERROR] cargar aprobados: {e}", flush=True)
        return []


def _conductores_baja_set() -> set:
    try:
        with open(CONDUCTORES_BAJA_FILE, encoding="utf-8") as f:
            return set(json.load(f) or [])
    except Exception:
        return set()

def _conductor_baja_add(numero: str):
    s = _conductores_baja_set(); s.add(numero)
    try:
        tmp = CONDUCTORES_BAJA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(sorted(s), f)
        os.replace(tmp, CONDUCTORES_BAJA_FILE)
    except Exception as e:
        print(f"[COND-BAJA ERROR] {e}", flush=True)

def _proveedor_por_numero(numero: str):
    """Reconoce si un número es proveedor (conductor/profesor/técnico/seguridad)."""
    if "CONDUCTORES" in globals() and isinstance(CONDUCTORES, dict) and numero in CONDUCTORES:
        if numero in _conductores_baja_set():
            return None
        info = CONDUCTORES[numero]
        nom = (info.get("nombre") if isinstance(info, dict) else "") or "Conductor"
        return {"tipo": "Conductor", "nombre": nom, "id": None, "fuente": "conductor"}
    if numero in PROFESORES:
        return {"tipo": "Profesor", "nombre": PROFESORES[numero].get("nombre", "Profesor"),
                "id": None, "fuente": "profesor_hc"}
    for p in cargar_proveedores_aprobados(""):
        if p.get("telefono") == numero:
            return {"tipo": p.get("tipo") or "Proveedor", "nombre": p.get("nombre", "Proveedor"),
                    "id": p.get("id"), "fuente": "json"}
    return None

def _es_saludo_activacion(texto: str) -> bool:
    t = (texto or "").strip().lower()
    if not t:
        return False
    claves = ["hola", "ola", "buenas", "buenos dias", "buenos días", "buenas tardes",
              "buenas noches", "activo", "activa", "activar", "estoy activo", "estoy activa",
              "sigo activo", "sigo activa", "presente", "disponible", "aqui estoy", "aquí estoy"]
    return any(t == k or t.startswith(k + " ") for k in claves)

_FRASES_MOTIVADORAS = [
    "🦅 El que vuela alto nunca pierde de vista su presa. ¡Sigamos cazando oportunidades!",
    "💪 Cada solicitud es una puerta; El Cuervo te la trae, tú la conviertes en ingresos.",
    "🔥 Los grandes no esperan la suerte, la construyen. ¡Hoy puede ser tu mejor día!",
    "🦅 El Cuervo vuela contigo: tu esfuerzo de hoy es tu tranquilidad de mañana.",
    "⚡ El que persevera, alcanza. ¡Mantente listo, que las solicitudes están por llegar!",
]
def _frase_motivadora():
    import random
    return random.choice(_FRASES_MOTIVADORAS)

async def _mostrar_panel_proveedor(numero, prov):
    sesiones[numero] = {"estado": S_PROV_PANEL, "datos": {"prov": prov}}
    nombre = prov.get("nombre") or "proveedor"
    await enviar_mensaje(numero,
        f"🦅 *Hola, {nombre}.*\n\n"
        "Notamos que hace un tiempo no recibías solicitudes por aquí. "
        "Queremos confirmar si sigues *activo y listo* para atender lo que llegue.\n\n"
        f"{_frase_motivadora()}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "1️⃣ ✅ Sí, sigo activo\n"
        "2️⃣ 👋 Quiero darme de baja\n"
        "3️⃣ 🛒 Necesito un servicio (como cliente)")

async def _panel_proveedor_respuesta(numero, sesion, texto):
    op = (texto or "").strip().lower()
    prov = sesion.get("datos", {}).get("prov", {})
    nombre = prov.get("nombre") or "proveedor"
    if op in ("1", "si", "sí", "activo", "activa", "sigo activo", "sigo activa"):
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        await enviar_mensaje(numero,
            f"✅ ¡Excelente, {nombre}! Quedas *activo* y tu canal está abierto. 🦅\n\n"
            f"{_frase_motivadora()}\n\n"
            "Apenas llegue una solicitud para ti, te avisamos por aquí. "
            "_Tip: escríbenos *activo* cada cierto tiempo para no perderte ninguna._")
        return
    if op in ("2", "baja", "darme de baja", "salir"):
        sesion["estado"] = S_PROV_BAJA
        await enviar_mensaje(numero,
            f"👋 {nombre}, ¿seguro que quieres darte de *baja*?\n"
            "Dejarás de recibir solicitudes hasta que vuelvas a activarte.\n\n"
            "1️⃣ Sí, dar de baja\n2️⃣ No, mejor sigo activo")
        return
    if op in ("3", "servicio", "cliente", "menu", "menú"):
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        await enviar_mensaje(numero, MSG_BIENVENIDA)
        return
    await enviar_mensaje(numero,
        "No te entendí 🙈.\n1️⃣ Sigo activo  ·  2️⃣ Darme de baja  ·  3️⃣ Necesito un servicio")

async def _dar_de_baja_proveedor(numero, prov):
    tipo = prov.get("tipo", "Proveedor"); nombre = prov.get("nombre", "Proveedor")
    fuente = prov.get("fuente")
    if fuente == "json" and prov.get("id"):
        actualizar_estado_proveedor(prov["id"], "BAJA")
    elif fuente == "conductor":
        _conductor_baja_add(numero)
    asunto = f"👋 Baja de proveedor — {nombre} ({tipo})"
    texto = (f"Un proveedor se dio de baja desde el bot.\n\n"
             f"Nombre: {nombre}\nTipo: {tipo}\nNúmero: +{numero}\n\n"
             "Ya no recibirá solicitudes. Si fue un error, puedes reactivarlo.")
    html = (f'<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#222">'
            f'<h2 style="color:#A6452F">El Cuervo</h2><p>Un proveedor se dio de baja 👋</p>'
            f'<table style="font-size:14px">'
            f'<tr><td style="color:#666;padding:4px 8px 4px 0">Nombre</td><td><b>{nombre}</b></td></tr>'
            f'<tr><td style="color:#666;padding:4px 8px 4px 0">Tipo</td><td>{tipo}</td></tr>'
            f'<tr><td style="color:#666;padding:4px 8px 4px 0">Número</td><td>+{numero}</td></tr></table>'
            f'<p style="color:#999;font-size:12px">Ya no recibirá solicitudes. — INCAMORE / El Cuervo</p></div>')
    try:
        await asyncio.to_thread(_enviar_correo_sync, asunto, html, texto)
    except Exception as e:
        print(f"[BAJA-CORREO ERROR] {e}", flush=True)

async def _panel_proveedor_baja(numero, sesion, texto):
    op = (texto or "").strip().lower()
    prov = sesion.get("datos", {}).get("prov", {})
    nombre = prov.get("nombre") or "proveedor"
    if op in ("1", "si", "sí", "baja", "dar de baja"):
        await _dar_de_baja_proveedor(numero, prov)
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        await enviar_mensaje(numero,
            f"👋 Listo, {nombre}. Te diste de *baja* y ya no recibirás solicitudes.\n\n"
            "Cuando quieras volver, escríbenos *activo* y te reactivamos al toque. "
            "¡Las puertas de El Cuervo siempre estarán abiertas para ti! 🦅")
        return
    sesiones[numero] = {"estado": S_MENU, "datos": {}}
    await enviar_mensaje(numero, f"😊 ¡Qué bueno, {nombre}! Sigues *activo*. {_frase_motivadora()}")


def proveedores_seg_aprobados() -> list:
    """Proveedores de Seguridad & Saneamiento APROBADOS (desde proveedores.json)."""
    return cargar_proveedores_aprobados("seguridad")


def es_proveedor_seg(numero: str) -> bool:
    """True si el número es un proveedor de Seguridad aprobado."""
    return any(p.get("telefono") == numero for p in proveedores_seg_aprobados())


# Proveedores "semilla" de Seguridad que se migran a proveedores.json al iniciar.
SEG_SEED = [
    {
        "id": "PV-SASI0001",
        "tipo": "Seguridad y Defensa Civil",
        "nombre": "Marcos Espinoza",
        "telefono": "51960459741",
        "negocio": "SASI SAC",
        "direccion": "",
        "placa": "",
        "detalle": "Extintores, señalización, fumigación, capacitación y defensa civil. Cobertura: Barranca, distritos y Huacho.",
        "fecha": "seed",
        "estado": "APROBADO",
    },
]


def asegurar_seed_seg():
    """Inserta los proveedores semilla de Seguridad en proveedores.json si no existen (idempotente)."""
    try:
        data = []
        if os.path.exists(PROVEEDORES_FILE):
            with open(PROVEEDORES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or []
        nums = {r.get("telefono") for r in data}
        nuevos = 0
        for s in SEG_SEED:
            if s["telefono"] not in nums:
                data.append(dict(s)); nuevos += 1
        if nuevos:
            tmp = PROVEEDORES_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, PROVEEDORES_FILE)
            print(f"[SEED] {nuevos} proveedor(es) de Seguridad migrado(s) a proveedores.json", flush=True)
    except Exception as e:
        print(f"[SEED ERROR] {e}", flush=True)


def _seg_texto_opciones(num_cliente: str) -> str:
    """Arma el mensaje con la lista de cotizaciones para que el cliente elija."""
    lista = cotizaciones_seg_pendientes.get(num_cliente, [])
    datos = sesiones.get(num_cliente, {}).get("datos", solicitudes_seg_pendientes.get(num_cliente, {}))
    subcat = datos.get("seg_subcategoria", "")
    lineas = [f"💰 *Cotizaciones recibidas — {subcat}*", ""]
    for i, c in enumerate(lista, 1):
        extra = f" — {c['descripcion']}" if c.get("descripcion") else ""
        lineas.append(f"{i}\u20e3 *{c.get('prov_negocio','')}* · S/{c.get('monto','')}{extra}")
    lineas.append("")
    lineas.append("Responde el *número* de la cotización que eliges.")
    lineas.append("_(Puedes esperar más cotizaciones antes de decidir.)_")
    return "\n".join(lineas)


def _seg_actualizar_servicio(sid: str, numero_cliente: str, *, cotizacion: dict | None = None,
                             estado: str | None = None, proveedor: str | None = None, monto=None):
    """Actualiza el registro de Seguridad en servicios.json: agrega una cotización
    y/o cambia estado, proveedor y monto. Permite seguimiento completo en el dashboard."""
    try:
        if not os.path.exists(SERVICIOS_FILE):
            return
        with open(SERVICIOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or []
        rec = None
        if sid:
            rec = next((r for r in data if r.get("id") == sid), None)
        if rec is None:
            for r in reversed(data):
                if r.get("telefono") == numero_cliente and r.get("tipo") == "SEGURIDAD":
                    rec = r; break
        if rec is None:
            return
        if cotizacion is not None:
            cots = rec.setdefault("cotizaciones", [])
            ex = next((c for c in cots if c.get("prov_num") == cotizacion.get("prov_num")), None)
            if ex:
                ex.update(cotizacion)
            else:
                cots.append(cotizacion)
        if estado is not None:
            rec["estado"] = estado
        if proveedor is not None:
            rec["proveedor"] = proveedor
        if monto is not None:
            try:
                rec["monto"] = float(str(monto).replace("S/", "").replace("s/", "").strip() or 0)
            except Exception:
                rec["monto"] = 0
        tmp = SERVICIOS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, SERVICIOS_FILE)
    except Exception as e:
        print(f"[SERVICIO ERROR] actualizar seg: {e}", flush=True)


def _enviar_correo_sync(asunto: str, cuerpo_html: str, cuerpo_texto: str):
    """Envía un correo vía SMTP (Gmail por defecto). Lee credenciales de env.
    Variables: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_TO (destino).
    Si falta configuración, no hace nada (no rompe el flujo)."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    pwd = os.getenv("SMTP_PASS", "").strip()
    destino = os.getenv("SMTP_TO", "").strip() or user
    if not user or not pwd or not destino:
        print("[CORREO] SMTP no configurado (faltan SMTP_USER/SMTP_PASS/SMTP_TO); se omite envío.", flush=True)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = f"El Cuervo Bot <{user}>"
    msg["To"] = destino
    msg.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))
    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(user, pwd)
            server.sendmail(user, [destino], msg.as_string())
        print(f"[CORREO] enviado a {destino}: {asunto}", flush=True)
        return True
    except Exception as e:
        print(f"[CORREO ERROR] {e}", flush=True)
        return False


async def enviar_correo_registro(registro: dict):
    """Arma y envía (en hilo aparte) el correo de un nuevo registro de proveedor."""
    tipo = registro.get("tipo", "")
    nombre = registro.get("nombre", "")
    tel = registro.get("telefono", "")
    fecha = registro.get("fecha", "")
    filas = [("Tipo", tipo), ("Nombre", nombre), ("WhatsApp", "+" + tel)]
    if registro.get("negocio"):   filas.append(("Negocio", registro["negocio"]))
    if registro.get("direccion"): filas.append(("Dirección", registro["direccion"]))
    if registro.get("placa"):     filas.append(("Placa", registro["placa"]))
    if registro.get("detalle"):   filas.append(("Detalle", registro["detalle"]))
    filas.append(("Fecha", fecha))
    filas.append(("Estado", registro.get("estado", "PENDIENTE_VALIDACION")))

    filas_html = "".join(
        f'<tr><td style="padding:8px 14px;background:#faf7ef;border:1px solid #eee;'
        f'font-weight:bold;color:#8a6d1a;width:140px">{k}</td>'
        f'<td style="padding:8px 14px;border:1px solid #eee;color:#222">{v}</td></tr>'
        for k, v in filas)
    html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto">
      <div style="background:#0e0f15;padding:18px 22px;border-radius:10px 10px 0 0">
        <h2 style="color:#e8b04b;margin:0">🦅 El Cuervo — Nuevo registro</h2>
        <p style="color:#cfd0db;margin:4px 0 0;font-size:13px">Solicitud para unirse a la red</p>
      </div>
      <table style="border-collapse:collapse;width:100%;font-size:14px">{filas_html}</table>
      <div style="padding:14px 22px;background:#f4f5f9;border-radius:0 0 10px 10px;font-size:12px;color:#777">
        Pendiente de validación · Responde al WhatsApp del solicitante para coordinar.
      </div>
    </div>"""
    texto = "El Cuervo — Nuevo registro\n\n" + "\n".join(f"{k}: {v}" for k, v in filas)
    asunto = f"🦅 Nuevo registro El Cuervo — {tipo}: {nombre}"

    base = os.getenv("PUBLIC_URL", "https://barranca-movil-bot.onrender.com").rstrip("/")
    pid = registro.get("id", "")
    url_val = f"{base}/proveedor/validar?clave={ADMIN_KEY}&id={pid}"
    url_ok = f"{base}/proveedor/aprobar?clave={ADMIN_KEY}&id={pid}"
    rechazos = "".join(
        f'<a href="{base}/proveedor/rechazar?clave={ADMIN_KEY}&id={pid}&motivo={cod}" '
        f'style="display:inline-block;background:#3a1c1c;color:#ff9a9a;text-decoration:none;'
        f'padding:7px 14px;border-radius:7px;font-size:12px;margin:4px">✕ {txt[:34]}</a>'
        for cod, txt in MOTIVOS_RECHAZO.items())
    botones = f"""
      <div style="padding:22px;text-align:center;background:#f4f5f9">
        <a href="{url_val}" style="display:inline-block;background:#e8b04b;color:#1a1a1a;
           text-decoration:none;padding:12px 26px;border-radius:8px;font-weight:bold;margin:4px">🔍 Poner en validación</a>
        <a href="{url_ok}" style="display:inline-block;background:#22b07d;color:#fff;
           text-decoration:none;padding:12px 26px;border-radius:8px;font-weight:bold;margin:4px">✅ Aprobar</a>
        <div style="margin-top:14px;border-top:1px solid #e0e0e8;padding-top:12px">
          <div style="font-size:12px;color:#999;margin-bottom:6px">Rechazar por:</div>
          {rechazos}
        </div>
      </div>"""
    html = html.replace(
        '<div style="padding:14px 22px;background:#f4f5f9;border-radius:0 0 10px 10px;',
        botones + '<div style="padding:14px 22px;background:#f4f5f9;border-radius:0 0 10px 10px;')
    try:
        await asyncio.to_thread(_enviar_correo_sync, asunto, html, texto)
    except Exception as e:
        print(f"[CORREO ERROR] async: {e}", flush=True)


async def iniciar_unete(numero: str, sesion: dict):
    """Inicia el flujo de registro de proveedor/abonado."""
    sesion["estado"] = S_UNETE_TIPO
    sesion["datos"] = {"servicio": "UNETE"}
    await enviar_mensaje(numero,
        "🤝 *¡Únete a El Cuervo!*\n"
        "Estamos en lanzamiento y queremos sumar a los mejores de Barranca.\n\n"
        "¿Qué eres?\n"
        "1️⃣ Restaurante / Cevichería / Chifa\n"
        "2️⃣ Taxista\n"
        "3️⃣ Colectivero\n"
        "4️⃣ Profesor (reforzamiento escolar)\n"
        "5️⃣ Seguridad y Defensa Civil\n"
        "6️⃣ Técnico / Especialista (soporte técnico, gasfitería, etc.)\n"
        "0️⃣ Volver al menú")


async def _unete_mostrar_resumen(numero: str, sesion: dict):
    """Muestra el resumen del registro de proveedor y pasa a confirmación."""
    d = sesion["datos"]
    sesion["estado"] = S_UNETE_CONFIRMAR
    lineas = [f"👤 {d.get('nombre','')}", f"📋 {d.get('unete_tipo_label','')}"]
    if d.get("unete_negocio"):
        lineas.append(f"🏪 {d['unete_negocio']}")
    if d.get("unete_direccion"):
        lineas.append(f"📍 {d['unete_direccion']}")
    if d.get("unete_placa"):
        lineas.append(f"🚗 Placa: {d['unete_placa']}")
    if d.get("unete_detalle"):
        lineas.append(f"📝 {d['unete_detalle']}")
    await enviar_mensaje(numero,
        "📋 *Confirma tu registro:*\n\n" + "\n".join(lineas) + "\n\n"
        "1️⃣ Confirmar y enviar\n"
        "2️⃣ Cancelar")


async def _unete_finalizar(numero: str, sesion: dict):
    """Guarda el registro, avisa al admin y agradece al interesado."""
    d = sesion["datos"]
    registro = {
        "id": f"PV-{int(time.time()*1000) % 100000000}",
        "tipo": d.get("unete_tipo_label", ""),
        "nombre": d.get("nombre", ""),
        "telefono": numero,
        "negocio": d.get("unete_negocio", ""),
        "direccion": d.get("unete_direccion", ""),
        "placa": d.get("unete_placa", ""),
        "detalle": d.get("unete_detalle", ""),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "estado": "PENDIENTE_VALIDACION",
    }
    guardar_proveedor(registro)

    # Aviso al admin (si hay número configurado en Render)
    admin = os.getenv("ADMIN_WHATSAPP", "").strip()
    if admin:
        extra = ""
        if registro["negocio"]:
            extra += f"🏪 {registro['negocio']}\n"
        if registro["direccion"]:
            extra += f"📍 {registro['direccion']}\n"
        if registro["placa"]:
            extra += f"🚗 Placa: {registro['placa']}\n"
        if registro["detalle"]:
            extra += f"📝 {registro['detalle']}\n"
        await enviar_mensaje(admin,
            f"🆕 *Nuevo registro — {registro['tipo']}*\n\n"
            f"👤 {registro['nombre']}\n"
            f"📱 +{numero}\n"
            f"{extra}"
            f"🕒 {registro['fecha']}\n\n"
            "_Pendiente de validación._")

    # Enviar también por correo (para seguimiento y aprobación formal)
    await enviar_correo_registro(registro)

    sesion["estado"] = S_MENU
    sesion["datos"] = {}
    await enviar_mensaje(numero,
        "✅ *¡Registro recibido!*\n\n"
        "Gracias por querer ser parte de *El Cuervo* 🦅\n"
        "Nuestro equipo revisará tus datos y te contactará pronto para validarte y activarte en la red.\n\n"
        "Escribe *menu* para volver al inicio.")


async def _tec_finalizar(numero: str, sesion: dict):
    """Registra la solicitud técnica, avisa al admin y cierra con el cliente."""
    d = sesion["datos"]
    registrar_servicio("SERVICIO_TECNICO", d, numero)

    admin = os.getenv("ADMIN_WHATSAPP", "").strip()
    if admin:
        await enviar_mensaje(admin,
            f"🔧 *Nueva solicitud — Servicios Técnicos*\n\n"
            f"🛠️ Oficio: {d.get('tec_oficio','')}\n"
            f"👤 {d.get('nombre','(sin nombre)')}\n"
            f"📱 +{numero}\n"
            f"📝 {d.get('tec_problema','')}\n"
            f"📍 {d.get('tec_direccion','(no indicada)')}\n"
            f"🕒 {d.get('tec_cuando','(a coordinar)')}\n\n"
            "_Asignar un técnico y coordinar._")

    # Notificar a los técnicos APROBADOS (los que aprobaste por correo)
    tecnicos = cargar_proveedores_aprobados("técnico")
    if tecnicos:
        aviso_tec = (
            "🔧 *Nueva solicitud de servicio técnico*\n\n"
            f"🛠️ {d.get('tec_oficio','')}\n"
            f"📝 {d.get('tec_problema','')}\n"
            f"📍 {d.get('tec_direccion','(no indicada)')}\n"
            f"🕒 {d.get('tec_cuando','(a coordinar)')}\n\n"
            f"📱 Contacto del cliente: +{numero}\n"
            f"👤 {d.get('nombre','(cliente)')}\n\n"
            "_Si puedes atenderlo, comunícate directamente con el cliente para coordinar visita y precio._")
        await asyncio.gather(*[
            enviar_mensaje(t.get("telefono", ""), aviso_tec) for t in tecnicos if t.get("telefono")
        ], return_exceptions=True)
        print(f"[TEC] solicitud enviada a {len(tecnicos)} técnico(s) aprobado(s)", flush=True)

    sesion["estado"] = S_MENU
    sesion["datos"] = {}
    await enviar_mensaje(numero,
        "✅ *¡Solicitud recibida!*\n\n"
        "Estamos buscando un técnico disponible para tu necesidad. "
        "En breve te contactaremos para coordinar la visita y el precio.\n\n"
        "Escribe *menu* para volver al inicio. 🦅")



import re  # (calaminas)

# ==========================================================================
#  MÓDULO ESTRUCTURAS — PARTE 1: CALAMINAS (INCAMORE)
#  Integrado de forma nativa: usa sesiones[], enviar_mensaje() y sheets_evento().
# ==========================================================================
import base64 as _b64, tempfile as _tmp

CAL_YAPE        = "914287306"
CAL_PRECIO_M2   = {"0.40": 26.0, "0.30": 23.0}     # mismo precio para los 4 colores
CAL_COLORES     = ["azul", "rojo", "blanco", "verde"]
CAL_MINIMO      = 15
CAL_IGV         = 0.18
CAL_ACCESORIOS  = {
    "autoperforantes_ciento": ("Autoperforantes (ciento, 100 und)", 15.0),
    "autoperforantes_millar": ("Autoperforantes (millar, 1000 und)", 100.0),
    "cumbreras":              ("Cumbreras (metro)", 20.0),
    "canaletas":              ("Canaletas (metro)", 20.0),
}
CAL_PALABRAS = ["calamina", "calaminas", "calaminon", "aluzinc", "aluzin", "alucin", "tr4", "tr-4",
                "cumbrera", "canaleta", "autoperforante", "estructura", "estructuras", "cobertura",
                "techo", "techado", "plancha", "planchas", "galvanizada", "calderia", "caldería"]
CAL_LOGO_B64 = "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CpNt1grwAUIYCASaNG581VVXAgBwhmos93d9+ulnnyz4JDcnJ2FEgSAIRUVF99xz98X9L+ZpkQjBUaPG7Nm925wkJSx9hI3F2dS1CquIs2kDd4LyPJUAigxy0CIZVpRSu92+etXK556bwWlWTpc/N316nTq1g8FgzPqBMKw8ms0jnx5VWFiUZhoYT8lt36593759vV6uzFYbGjLGGAB//rkRZMDZG2KAbBWEY9+OHTtSxcmCdNE3hisoLy+/8oora9WqpShKRoSslkE7avRoq8WScGAIwUDA37x58ymTn+WBtIIgLFy06NNPF+Tm5aUXew9To2UUzoLErGhMja0KrlXNZALLAHxgZW/K9Cef4srOnjV79h9/rBcEzBgjhDZo0GDixImehD3nodpvcffuXaNGjUq7oAHjNRnuuP32ao8OYoxJkrRp82aiECO0wADZ08EVIIx8Pt+ePXtMkpRgQcNMznsWC5SSJN18882VHBhCk5555sCB/RaLJUl+F/J6vBMnTMirlSfLMsa4oKBg+PARFeuwIAHvCiu2s2GSPzE1Y2tGO6o2TS6TgoFxcQ48NktRlKFDhwaDQQhVAuH+++679NJLS0sT9/dWFCUnN3fevLe//HJhmqQBv87ll1/etFmzQCAYDpRj1bLmTSbTvvx9x44fhxAajIEBsjUOsgCAAwcPHjlyVJSkRIVNYLreLharZvr9/jZt25x99lkcMTMlCr777vs333w7OztHTqSTYoxKS0v+c9l/bh80SFEIhAgh9PSo0fn5+WZLytbWOs9WNfXePb2vLDH6AZD6eSpdyiHB26EOp+P3339/7rnneCQABABj/MILz9ttKi2ecKWZLZZRo0YVFxenQxpACIlCXC5Xv37n+3w+jFF11YZhjAmiUFRYtGnTJgBAmu44QwyQraRQRgAAm/78011WJghClPEJq7QpIUR+v7/f+f0sFktG4bGUMoTwyZMnH398iCQJyYBSVhSb1fb8rNkII0qJKApffrnw/ffey81N2iiBj0Gvfv7djsRExxlM3mQhsXeyGoQoJDsne9bs59erpAFQFNKhQ4exY8e6S0sFQYiHUEqpxWLds2f3xImT0iMNeIdxdt0116ondPXViEEQKnJo3dp1wAgwMEC25gUCADZs3AgohRDEISys+MtJdgilVBCE//zn0swVDYoQHDHi6f378y0W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+MRSC544ceK/52l5ZLUgCBDCTz/97J577/nww48QgllZWQwASkni8zhW42Lx60+PxNGhQlErHmPs8/nuv/fenr16EpKgFQLvQuh2ux966OGXXn4pJydHa+LNmVaMMVEUt9sNARp8x+APP/ygZ88eeoQ9dOjQHYMHJ9OREULBYKBhw4Yff/SR1WoF4VIjdwy+88iRI2aziTEWU9cGQijLssvp+umn/910042HDh3etHmTKEoYoRQImog7TKHOJm44pksugMlq1rJE81w5EIYI+nw+n89324ABH37wAQDsp5/+Z7dnxZs1vD7hls1bGjRs2KtXT84SmM3m1q1affDBh5IkJTQgGIAY45WrVg0YMMCRlcUZT16F8qKLLrrowgu3bd++e9cuWVFMJlOkqTBj3A8WCoU+WbDAZDKdd17f6PcLIYRZWVmfLFhQWloqCDWYswcBoIwyxixWKxKEFStWfPb5536fv0OH9na7XVMRDGD9N2qyeu/WL7/8etnlV9w2cOCuXbtq5eVhjGVFphWk16SumZIioj0q2olSajKb2rVvBxKBCmPM6/V+/vkX5/e78ONPPqlbpy5XrDDGEMJQKFTqLi0qLBAE4dZbb/npp/+9Pe+tBg0aaC1FuUo1YuTTp06dSrTP1e0YCARmPDe9Tp06/MjBGD//4ovLly1zOBwKIfEmOsao3OsZO2ZMbm5u8+bNFy788ssvvrBpBaWqM0sBxiR2pcfEsmphC3h4Vof27T//7LMPP/ygUeNGI0aObNuunS9J8xhCSJbDMWbM2N27dwuCAAFQFOWiiy566KEHi4uKRDFRpAGjZrP58OHDw58aofkwOfmrKMq55567fNlvH3/8Ue/e5waDwaLCAq/XSwmBCHFSwmKxZGVlPf3009ded+OWLVs4OgO1LSO12+3t27evdt9XQpUWQkgoBYzl5eW53e5x48b17tP37XnzGKXcJ2ZotVEz9o93EXJ+kx/vGzf+OXPmzEVfLSIKcTgdjLGKE65g1P5niTSn+IJcsYwtU7cxIYrValuzenXjxo1iznyu1+zYseP++x/YuHEjZTQYCPJvIixYrdY6dep07NC+X79+V111VatWrfg+1/wzPND1g/kfDL7rrtzcxI0SMBZKSotvuO76zz77VOci23ze+f0whhBCyljMs/C+VV27dV3222+iICpEkSTpxx+X3HDj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"
CAL_PENDIENTES = {}   # numero_cliente -> ruta_pdf (borradores por aprobar)
CAL_APROBACION = {}   # folio -> {datos, cot, ruta, numero, estado}
_CAL_FOLIO = {"n": 41}
_CAL_FOLIO_FILE = os.path.join(DATA_DIR, "cal_folio.json")

def es_consulta_calaminas(texto: str) -> bool:
    t = (texto or "").lower()
    return any(p in t for p in CAL_PALABRAS)

def _cal_num(texto):
    m = re.search(r"[-+]?\d*[.,]?\d+", (texto or "").replace(",", "."))
    return float(m.group()) if m else None

def _cal_si(texto):
    return (texto or "").strip().lower() in ("si", "sí", "s", "yes", "ok", "dale", "1")

def _cal_money(v):
    return f"S/ {v:,.2f}"

def _cal_folio():
    """Folio ÚNICO y persistente. El contador se guarda en /var/data (sobrevive
    reinicios de Render) y, como red de seguridad anti-colisión, se salta cualquier
    folio cuyo PDF ya exista en disco."""
    year = datetime.now().year
    cotdir = os.path.join(DATA_DIR, "cotizaciones")
    os.makedirs(cotdir, exist_ok=True)
    try:
        with open(_CAL_FOLIO_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    n = int(data.get(str(year), 41))
    while True:
        n += 1
        folio = f"COT-{year}-{n:04d}"
        if not os.path.exists(os.path.join(cotdir, f"{folio}.pdf")):
            break
    data[str(year)] = n
    try:
        tmp = _CAL_FOLIO_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, _CAL_FOLIO_FILE)
    except Exception as e:
        print(f"[CAL-FOLIO ERROR] {e}", flush=True)
    _CAL_FOLIO["n"] = n
    return folio

def _cal_logo_tmp():
    fd, ruta = _tmp.mkstemp(suffix=".png")
    with os.fdopen(fd, "wb") as f:
        f.write(_b64.b64decode(CAL_LOGO_B64))
    return ruta

def cal_construir_cotizacion(e: dict) -> dict:
    factura = (e.get("tipo") == "factura")
    items = []; base = 0.0
    p_m2 = CAL_PRECIO_M2[e["espesor"]]
    m2 = round(e["largo"] * e["cantidad"], 2)
    sub = round(p_m2 * m2, 2); base += sub
    items.append({
        "desc": f"Calamina TR4 e={e['espesor']} mm, color {e['color']}\nLargo {e['largo']:.2f} m - ancho util 1.00 m",
        "cant": e["cantidad"], "medida": f"{m2:.2f} m2",
        "punit": _cal_money(p_m2), "subtotal": _cal_money(sub)})
    for key, cant in e.get("accesorios", {}).items():
        nombre, precio = CAL_ACCESORIOS[key]
        s = round(precio * cant, 2); base += s
        items.append({"desc": nombre, "cant": cant, "medida": "-",
                      "punit": _cal_money(precio), "subtotal": _cal_money(s)})
    if factura:
        igv = round(base * CAL_IGV, 2); total = round(base + igv, 2)
        totales = [("Valor de venta", _cal_money(base)), ("IGV (18%)", _cal_money(igv)),
                   ("Entrega en Barranca", "Sin costo")]
        total_label, nota_igv = "Total", "Incluye IGV (18%) discriminado"
    else:
        total = round(base, 2)
        totales = [("Entrega en Barranca", "Sin costo")]
        total_label, nota_igv = "Total referencial", "Precios incluyen IGV"
    return {
        "folio": _cal_folio(), "fecha": datetime.now().strftime("%d/%m/%Y"),
        "cliente": e.get("nombre", "Cliente"),
        "contacto": f"{e['numero']} - Barranca (sin costo)",
        "ruc": e.get("ruc"), "razon": e.get("razon"),
        "items": items, "totales": totales,
        "total_label": total_label, "total": _cal_money(total), "total_value": total,
        "nota_igv": nota_igv,
        "condiciones": ("Cotizacion referencial, sujeta a confirmacion de stock. "
                        "Adelanto del 75% para iniciar el pedido. Entrega del material: "
                        "3 dias habiles desde confirmado el adelanto. Validez: 7 dias.")}

def cal_generar_pdf(d: dict) -> str:
    from fpdf import FPDF
    ROJO=(166,69,47); AZUL=(60,106,148); GRIS=(120,120,120); NEGRO=(31,31,31); CREMA=(245,243,236)
    pdf = FPDF(format="A4", unit="mm"); pdf.add_page(); pdf.set_auto_page_break(False)
    M=14; W=210-2*M
    logo=_cal_logo_tmp(); pdf.image(logo, x=M, y=14, h=26)
    pdf.set_font("Helvetica","B",8); pdf.set_fill_color(*AZUL); pdf.set_text_color(255,255,255)
    pdf.set_xy(210-M-30,15); pdf.cell(30,6,"via El Cuervo",align="C",fill=True)
    pdf.set_text_color(80,80,80); pdf.set_font("Helvetica","",9)
    pdf.set_xy(110,23); pdf.cell(W-96,5,"RUC 20603707703",align="R",ln=1)
    pdf.set_x(110); pdf.cell(W-96,5,"Barranca, Peru",align="R",ln=1)
    pdf.set_x(110); pdf.cell(W-96,5,"incamore.sac@gmail.com",align="R",ln=1)
    pdf.set_draw_color(*ROJO); pdf.set_line_width(1.1); pdf.line(M,43,210-M,43)
    pdf.set_xy(M,49); pdf.set_text_color(*NEGRO); pdf.set_font("Helvetica","B",20); pdf.cell(80,10,"COTIZACION")
    pdf.set_font("Helvetica","",10); pdf.set_text_color(80,80,80)
    pdf.set_xy(110,49); pdf.cell(W-96,5,f"N {d['folio']}",align="R",ln=1)
    pdf.set_x(110); pdf.cell(W-96,5,f"Fecha: {d['fecha']}",align="R",ln=1)
    pdf.set_draw_color(228,225,216); pdf.set_line_width(0.3); pdf.line(M,63,210-M,63)
    pdf.set_fill_color(*CREMA); pdf.rect(M,67,W/2-3,16,"F"); pdf.rect(M+W/2+3,67,W/2-3,16,"F")
    pdf.set_xy(M+3,69); pdf.set_font("Helvetica","",8); pdf.set_text_color(*GRIS); pdf.cell(60,5,"Cliente",ln=1)
    pdf.set_xy(M+3,74); pdf.set_font("Helvetica","B",11); pdf.set_text_color(*NEGRO); pdf.cell(80,6,d["cliente"])
    pdf.set_xy(M+W/2+6,69); pdf.set_font("Helvetica","",8); pdf.set_text_color(*GRIS); pdf.cell(60,5,"Contacto / entrega",ln=1)
    pdf.set_xy(M+W/2+6,74); pdf.set_font("Helvetica","B",11); pdf.set_text_color(*NEGRO); pdf.cell(80,6,d["contacto"])
    if d.get("ruc"):
        pdf.set_xy(M+3,78.5); pdf.set_font("Helvetica","",7); pdf.set_text_color(*GRIS)
        pdf.cell(80,4,f"RUC {d['ruc']} - {d.get('razon','')}"[:60])
    y=90; pdf.set_xy(M,y); pdf.set_font("Helvetica","B",8); pdf.set_text_color(*GRIS)
    cols=[(90,"Descripcion","L"),(20,"Cant.","C"),(24,"Medida","R"),(24,"P.unit.","R"),(24,"Subtotal","R")]
    x=M
    for w,t,a in cols:
        pdf.set_xy(x,y); pdf.cell(w,7,t,align=a); x+=w
    pdf.set_draw_color(207,202,187); pdf.set_line_width(0.4); pdf.line(M,y+7,210-M,y+7)
    y+=9; pdf.set_font("Helvetica","",9); pdf.set_text_color(*NEGRO)
    for it in d["items"]:
        x=M; filas=[(90,it["desc"],"L"),(20,str(it["cant"]),"C"),(24,it["medida"],"R"),(24,it["punit"],"R"),(24,it["subtotal"],"R")]
        for w,t,a in filas:
            pdf.set_xy(x,y)
            if w==90: pdf.multi_cell(w,5,t,align=a)
            else: pdf.cell(w,5,t,align=a)
            x+=w
        pdf.set_draw_color(236,233,224); pdf.set_line_width(0.2); pdf.line(M,y+9.5,210-M,y+9.5)
        y+=12
    y+=2; bx=210-M-75
    for etq,val in d["totales"]:
        pdf.set_xy(bx,y); pdf.set_font("Helvetica","",9); pdf.set_text_color(90,90,90)
        pdf.cell(45,5,etq); pdf.cell(30,5,val,align="R"); y+=6
    pdf.set_draw_color(207,202,187); pdf.set_line_width(0.4); pdf.line(bx,y+1,210-M,y+1); y+=3
    pdf.set_xy(bx,y); pdf.set_font("Helvetica","B",11); pdf.set_text_color(*NEGRO); pdf.cell(40,7,d["total_label"])
    pdf.set_font("Helvetica","B",15); pdf.set_text_color(*ROJO); pdf.cell(35,7,d["total"],align="R"); y+=8
    pdf.set_xy(bx,y); pdf.set_font("Helvetica","",7.5); pdf.set_text_color(*GRIS); pdf.cell(75,4,d["nota_igv"],align="R"); y+=8
    pdf.set_fill_color(238,244,251); pdf.rect(M,y,W,14,"F")
    pdf.set_xy(M+3,y+2.5); pdf.set_font("Helvetica","",8.5); pdf.set_text_color(47,90,134)
    pdf.multi_cell(W-6,4.2,d["condiciones"]); y+=18
    pdf.set_draw_color(236,233,224); pdf.set_line_width(0.3); pdf.line(M,y,210-M,y); y+=3
    pdf.set_xy(M,y); pdf.set_font("Helvetica","B",9); pdf.set_text_color(*NEGRO); pdf.cell(100,5,"INCAMORE S.A.C",ln=1)
    pdf.set_x(M); pdf.set_font("Helvetica","I",8); pdf.set_text_color(*ROJO); pdf.cell(100,5,"Ingenieria a tu medida")
    pdf.set_xy(110,y+1); pdf.set_font("Helvetica","",8); pdf.set_text_color(*GRIS); pdf.cell(W-96,5,"Gracias por su preferencia",align="R")
    _cotdir=os.path.join(DATA_DIR,"cotizaciones"); os.makedirs(_cotdir,exist_ok=True)
    ruta=os.path.join(_cotdir, f"{d['folio']}.pdf"); pdf.output(ruta)
    try: os.remove(logo)
    except Exception: pass
    return ruta

def cal_base_url():
    return (os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/") or "https://barranca-movil-bot.onrender.com")

def cal_link_cotizacion(folio: str) -> str:
    return f"{cal_base_url()}/cotizacion/{folio}"

async def cal_enviar_documento(to: str, ruta_pdf: str, caption: str = "") -> bool:
    """Envía el PDF como documento usando un ENLACE público servido por el propio bot.
    Es más confiable que subir el archivo al API de Meta."""
    folio = os.path.splitext(os.path.basename(ruta_pdf))[0]
    link = cal_link_cotizacion(folio)
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": to, "type": "document",
                   "document": {"link": link, "filename": f"{folio}.pdf", "caption": caption}}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            print(f"[CAL-DOC LINK ERROR] {r.status_code} {r.text[:300]}", flush=True); return False
        print(f"[CAL-DOC] enviado (link) a {to}", flush=True); return True
    except Exception as e:
        print(f"[CAL-DOC EXCEPTION] {e}", flush=True); return False

async def cal_registrar_lead(datos: dict):
    """Trazabilidad: Sheets (si existe el webhook) + log. No rompe si falla."""
    try:
        if "sheets_evento" in globals():
            await sheets_evento("add_cotizacion", datos)
    except Exception as e:
        print(f"[CAL-LEAD sheets] {e}", flush=True)
    print(f"[CAL-LEAD] {datos}", flush=True)

def _cal_admin():
    return os.getenv("ADMIN_WHATSAPP", "").strip() or (OPERADOR_WA or "")

def _cal_pregunta_espesor():
    return "¿Qué espesor de calamina TR4 necesitas?\n- 0.30 mm\n- 0.40 mm"

async def iniciar_calaminas(numero, sesion):
    sesion["estado"] = S_CAL_TIPO
    sesion["datos"] = {"servicio": "CALAMINAS", "numero": numero, "accesorios": {}}
    await enviar_mensaje(numero,
        "🔧 Te ayudo con eso. Este servicio lo ejecuta *INCAMORE S.A.C.*, "
        "nuestra empresa de estructuras metálicas y caldería.\n\n"
        "Para empezar, ¿tu comprobante será *boleta* o *factura*?\n"
        "1️⃣ Boleta\n"
        "2️⃣ Factura (necesito tu RUC)\n\n"
        "_(puedes escribir *atrás* para corregir o *cancelar* para salir)_")

CAL_PALABRAS_PRECIO = ("cuanto", "cuánto", "precio", "precios", "cuesta", "cuestan",
                       "vale", "valen", "a como", "a cómo", "a cuanto", "a cuánto",
                       "costo", "tarifa", "el metro", "por metro", "x metro", "metro cuadrado", "m2")

def _cal_es_consulta_precio(low: str) -> bool:
    return any(p in low for p in CAL_PALABRAS_PRECIO)

def _cal_texto_precios() -> str:
    return ("💰 *Precios referenciales (incluyen IGV):*\n"
            "• Calamina TR4 0.30 mm — S/ 23 el m²\n"
            "• Calamina TR4 0.40 mm — S/ 26 el m²\n"
            "• Cumbreras — S/ 20 el metro\n"
            "• Canaletas — S/ 20 el metro\n"
            "• Autoperforantes — S/ 15 el ciento / S/ 100 el millar\n\n"
            "_El precio final según tu medida sale en la cotización formal._")

def _cal_pregunta_de(estado, d):
    if estado == S_CAL_TIPO:
        return ("¿Tu comprobante será *boleta* o *factura*?\n1️⃣ Boleta\n2️⃣ Factura (necesito tu RUC)")
    if estado == S_CAL_RUC:
        return "Pásame el *RUC* (11 dígitos) y la *razón social*.\nEj: 20123456789 MI EMPRESA SAC"
    if estado == S_CAL_ESPESOR:
        return _cal_pregunta_espesor()
    if estado == S_CAL_COLOR:
        return "Color de la calamina:\n- " + "\n- ".join(c.capitalize() for c in CAL_COLORES)
    if estado == S_CAL_LARGO:
        return "¿Qué *largo* necesitas por calamina, en metros? (ej: 3.00)"
    if estado == S_CAL_CANTIDAD:
        return "¿Cuántas calaminas necesitas?"
    if estado == S_CAL_ACCESORIOS:
        return ("¿Necesitas accesorios? (elige varios o escribe *no*)\n"
                "- Autoperforantes (ciento S/15 / millar S/100)\n"
                "- Cumbreras (S/20 el metro)\n- Canaletas (S/20 el metro)")
    if estado == S_CAL_NOMBRE:
        return "¿A nombre de quién va la cotización?"
    return ""

def _cal_paso_anterior(estado, d):
    if estado == S_CAL_TIPO:       return None
    if estado == S_CAL_RUC:        return S_CAL_TIPO
    if estado == S_CAL_ESPESOR:    return S_CAL_RUC if d.get("tipo") == "factura" else S_CAL_TIPO
    if estado == S_CAL_COLOR:      return S_CAL_ESPESOR
    if estado == S_CAL_LARGO:      return S_CAL_COLOR
    if estado == S_CAL_CANTIDAD:   return S_CAL_LARGO
    if estado == S_CAL_ACCESORIOS: return S_CAL_CANTIDAD
    if estado == S_CAL_NOMBRE:     return S_CAL_ACCESORIOS
    return None

async def manejar_calaminas(numero, sesion, texto):
    estado = sesion["estado"]; d = sesion["datos"]; t = (texto or "").strip()
    low = t.lower()

    # ── Válvula de escape: cancelar / volver al menú ──
    if low in ("cancelar", "cancela", "salir", "menu", "menú", "inicio", "empezar de nuevo"):
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        await enviar_mensaje(numero, "Listo, cancelé tu cotización. 👋\n\n" + MSG_BIENVENIDA)
        return

    # ── Retroceder un paso para corregir ──
    if low in ("atras", "atrás", "volver", "regresar", "corregir", "anterior", "back"):
        prev = _cal_paso_anterior(estado, d)
        if prev is None:
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, "No hay un paso anterior, te regreso al menú. 👋\n\n" + MSG_BIENVENIDA)
        else:
            sesion["estado"] = prev
            await enviar_mensaje(numero, "↩️ Volvamos un paso.\n\n" + _cal_pregunta_de(prev, d))
        return

    # ── Consulta de precio en cualquier momento: responde y sigue donde estaba ──
    if _cal_es_consulta_precio(low) and estado in (S_CAL_TIPO, S_CAL_ESPESOR, S_CAL_COLOR,
                                                    S_CAL_LARGO, S_CAL_CANTIDAD, S_CAL_ACCESORIOS):
        await enviar_mensaje(numero, _cal_texto_precios())
        q = _cal_pregunta_de(estado, d)
        if q:
            await enviar_mensaje(numero, "Sigamos 👇\n\n" + q)
        return

    if estado == S_CAL_TIPO:
        if "2" in t or "factura" in t.lower() or "empresa" in t.lower():
            d["tipo"] = "factura"; sesion["estado"] = S_CAL_RUC
            await enviar_mensaje(numero, "Perfecto, factura. Pásame el *RUC* (11 dígitos) y la *razón social*.\nEj: 20123456789 MI EMPRESA SAC")
        else:
            d["tipo"] = "boleta"; sesion["estado"] = S_CAL_ESPESOR
            await enviar_mensaje(numero, _cal_pregunta_espesor())
        return

    if estado == S_CAL_RUC:
        m = re.search(r"\d{11}", t)
        if not m:
            await enviar_mensaje(numero, "Necesito el RUC (11 dígitos) y la razón social. Ej: 20123456789 MI EMPRESA SAC"); return
        d["ruc"] = m.group(); d["razon"] = t.replace(m.group(), "").strip(" ,.-") or "-"
        sesion["estado"] = S_CAL_ESPESOR
        await enviar_mensaje(numero, _cal_pregunta_espesor()); return

    if estado == S_CAL_ESPESOR:
        tt = t.replace(".", "").replace(",", "")
        if "0.30" in t or "0,30" in t or "030" in tt or t in ("30", "0.3", "0,3") or "delgad" in low or "fina" in low:
            d["espesor"] = "0.30"
        elif "0.40" in t or "0,40" in t or "040" in tt or t in ("40", "0.4", "0,4") or "grues" in low:
            d["espesor"] = "0.40"
        else:
            await enviar_mensaje(numero,
                "No te entendí el espesor 🙏\nEscríbelo así:\n- *0.30* (más delgada)\n- *0.40* (más gruesa)"); return
        sesion["estado"] = S_CAL_COLOR
        await enviar_mensaje(numero, "Color de la calamina:\n- " + "\n- ".join(c.capitalize() for c in CAL_COLORES)); return

    if estado == S_CAL_COLOR:
        col = next((x for x in CAL_COLORES if x in t.lower()), None)
        if not col:
            await enviar_mensaje(numero, "Indícame un color: " + ", ".join(CAL_COLORES)); return
        d["color"] = col; sesion["estado"] = S_CAL_LARGO
        await enviar_mensaje(numero, "¿Qué *largo* necesitas por calamina, en metros? (ej: 3.00)"); return

    if estado == S_CAL_LARGO:
        v = _cal_num(t)
        if not v or v <= 0:
            await enviar_mensaje(numero, "Indícame el largo en metros (ej: 3.00)."); return
        d["largo"] = v; sesion["estado"] = S_CAL_CANTIDAD
        await enviar_mensaje(numero, "¿Cuántas calaminas necesitas?"); return

    if estado == S_CAL_CANTIDAD:
        v = _cal_num(t)
        if not v or v <= 0:
            await enviar_mensaje(numero, "Indícame la cantidad de calaminas."); return
        if v < CAL_MINIMO:
            await enviar_mensaje(numero, f"Para este tipo de pedido el mínimo es de {CAL_MINIMO} calaminas (las fabricamos a medida).\n¿Cuántas necesitas? (mínimo {CAL_MINIMO})"); return
        d["cantidad"] = int(v); sesion["estado"] = S_CAL_ACCESORIOS
        await enviar_mensaje(numero,
            "¿Necesitas accesorios? (elige varios o escribe *no*)\n"
            "- Autoperforantes (ciento S/15 / millar S/100)\n"
            "- Cumbreras (S/20 el metro)\n"
            "- Canaletas (S/20 el metro)\n\n"
            "Ej: _cumbreras 10, canaletas 5, autoperforantes 1 millar_"); return

    if estado == S_CAL_ACCESORIOS:
        low = t.lower()
        if low in ("no", "ninguno", "ninguna", "0"):
            sesion["estado"] = S_CAL_NOMBRE
            await enviar_mensaje(numero, "Listo. ¿A nombre de quién va la cotización?"); return
        cap = d.get("accesorios", {}); n = int(_cal_num(t) or 1)
        if "millar" in low: cap["autoperforantes_millar"] = n
        elif "ciento" in low or "autoperf" in low or "tornillo" in low: cap["autoperforantes_ciento"] = n
        if "cumbrera" in low: cap["cumbreras"] = n
        if "canaleta" in low: cap["canaletas"] = n
        d["accesorios"] = cap; sesion["estado"] = S_CAL_NOMBRE
        msg = "Anotado." if cap else "Ok, sin accesorios."
        await enviar_mensaje(numero, f"{msg} ¿A nombre de quién va la cotización?"); return

    if estado == S_CAL_NOMBRE:
        d["nombre"] = (t.title() if t else "Cliente")
        await _cal_finalizar(numero, sesion); return

    if estado == S_CAL_POST:
        if _cal_si(t):
            await cal_registrar_lead({"tipo_lead": "CONSULTA_ASESOR", "estado": "NUEVO",
                "numero": numero, "cliente": d.get("nombre", ""),
                "motivo": "Confirmar antes del adelanto", "folio": d.get("folio", "")})
            adm = _cal_admin()
            if adm:
                await enviar_mensaje(adm, f"📞 PEDIDO DE ASESOR: {d.get('nombre','')} ({numero}) quiere confirmar antes del adelanto. Folio {d.get('folio','')}.")
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, "Perfecto 👍 Un asesor de INCAMORE te contacta en el día para confirmar los detalles. ¡Gracias!")
        elif low in ("no", "n", "no gracias", "datos", "pago", "yape", "deposito", "depósito"):
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                f"Para iniciar tu pedido, el adelanto es del *75%* del total.\n"
                f"📱 Yape: *{CAL_YAPE}* (INCAMORE S.A.C)\n"
                f"Apenas confirmes el adelanto, la entrega del material es de *3 días hábiles*.\n\n"
                f"*INCAMORE S.A.C — Ingeniería a tu medida.*")
        else:
            await enviar_mensaje(numero,
                "¿Quieres que un *asesor* confirme contigo antes del adelanto?\n"
                "Responde *SI* para que te contacte, o *NO* para recibir los datos de pago. 📱")
        return

async def cal_enviar_correo_aprobacion(cot, d, numero):
    """Envía la cotización al correo INCAMORE con botones APROBAR / CORREGIR."""
    base = cal_base_url()
    folio = cot["folio"]
    link_pdf = cal_link_cotizacion(folio)
    link_ok = f"{base}/cotizacion/{folio}/aprobar?clave={ADMIN_KEY}"
    link_edit = f"{base}/cotizacion/{folio}/corregir?clave={ADMIN_KEY}"
    items_txt = "\n".join(f"- {it['cant']} x {it['desc'].splitlines()[0]} = {it['subtotal']}" for it in cot["items"])
    asunto = f"🧾 Cotización {folio} — {cot['cliente']} ({cot['total']})"
    texto = (
        f"Nueva cotización de calaminas/estructuras lista para tu revisión.\n\n"
        f"Folio: {folio}\nCliente: {cot['cliente']}  ({numero})\n"
        f"Comprobante: {d['tipo'].upper()}" + (f"  RUC: {d.get('ruc','')}" if d.get('ruc') else "") + "\n"
        f"Detalle:\n{items_txt}\n{cot['total_label']}: {cot['total']}\n\n"
        f"PDF: {link_pdf}\n\n"
        f"APROBAR Y ENVIAR AL CLIENTE: {link_ok}\n"
        f"CORREGIR ANTES DE ENVIAR: {link_edit}\n"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#222">
      <h2 style="color:#A6452F;margin-bottom:4px">INCAMORE S.A.C</h2>
      <p style="margin-top:0;color:#666">Nueva cotización lista para tu revisión</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <tr><td style="padding:4px 0;color:#666">Folio</td><td><b>{folio}</b></td></tr>
        <tr><td style="padding:4px 0;color:#666">Cliente</td><td>{cot['cliente']} ({numero})</td></tr>
        <tr><td style="padding:4px 0;color:#666">Comprobante</td><td>{d['tipo'].upper()} {('RUC '+str(d.get('ruc'))) if d.get('ruc') else ''}</td></tr>
        <tr><td style="padding:4px 0;color:#666">{cot['total_label']}</td><td><b>{cot['total']}</b></td></tr>
      </table>
      <pre style="background:#f5f5f5;padding:10px;border-radius:6px;font-size:13px;white-space:pre-wrap">{items_txt}</pre>
      <p><a href="{link_pdf}" style="color:#3C6A94">📄 Ver PDF de la cotización</a></p>
      <div style="margin:24px 0">
        <a href="{link_ok}" style="display:inline-block;background:#1faa59;color:#fff;text-decoration:none;
           padding:12px 22px;border-radius:8px;font-weight:bold;margin-right:10px">✅ APROBAR Y ENVIAR</a>
        <a href="{link_edit}" style="display:inline-block;background:#A6452F;color:#fff;text-decoration:none;
           padding:12px 22px;border-radius:8px;font-weight:bold">✏️ CORREGIR</a>
      </div>
      <p style="color:#999;font-size:12px">El cliente recibirá el PDF solo cuando apruebes. — INCAMORE S.A.C, Ingeniería a tu medida.</p>
    </div>"""
    try:
        await asyncio.to_thread(_enviar_correo_sync, asunto, html, texto)
    except Exception as e:
        print(f"[CAL-CORREO ERROR] {e}", flush=True)


async def _cal_finalizar(numero, sesion):
    d = sesion["datos"]
    cot = cal_construir_cotizacion(d)
    ruta = cal_generar_pdf(cot)
    folio = cot["folio"]
    CAL_PENDIENTES[numero] = ruta
    CAL_APROBACION[folio] = {"datos": dict(d), "cot": cot, "ruta": ruta,
                             "numero": numero, "estado": "PENDIENTE"}
    await cal_enviar_correo_aprobacion(cot, d, numero)
    await cal_registrar_lead({"tipo_lead": "COTIZACION_CALAMINAS", "estado": "PENDIENTE",
        "folio": folio, "numero": numero, "cliente": cot["cliente"],
        "comprobante": d["tipo"], "ruc": d.get("ruc", ""), "total": cot["total_value"], "fecha": cot["fecha"]})
    sesion["estado"] = S_MENU
    sesion["datos"] = {}
    await enviar_mensaje(numero,
        "✅ ¡Listo! Ya tengo todos tus datos. 🙌\n\n"
        "Estoy preparando tu *cotización formal de INCAMORE* y te la envío por aquí en muy poco. "
        "Gracias por tu preferencia. 🦅\n\n"
        "_INCAMORE S.A.C — Ingeniería a tu medida._")


async def cal_enviar_aprobada_al_cliente(reg):
    """Envía el PDF + datos de pago al cliente (al aprobar o corregir)."""
    cli = reg["numero"]; ruta = reg["ruta"]; cot = reg["cot"]
    await cal_enviar_documento(cli, ruta, caption="📄 Tu cotización — INCAMORE S.A.C")
    await enviar_mensaje(cli,
        "📄 ¡Aquí está tu cotización de *INCAMORE*! 🦅\n\n"
        f"Para iniciar tu pedido, el adelanto es del *75%* del total.\n"
        f"📱 Yape: *{CAL_YAPE}* (INCAMORE S.A.C)\n"
        "Entrega del material: *3 días hábiles* desde confirmado el adelanto.\n\n"
        "Cualquier duda, aquí estoy. *INCAMORE S.A.C — Ingeniería a tu medida.*")
    reg["estado"] = "APROBADA"


async def _cal_finalizar_OLD(numero, sesion):
    d = sesion["datos"]
    cot = cal_construir_cotizacion(d)
    ruta = cal_generar_pdf(cot)
    CAL_PENDIENTES[numero] = ruta
    adm = _cal_admin()
    if adm:
        await enviar_mensaje(adm,
            f"🧾 *BORRADOR DE COTIZACIÓN para aprobar*\n"
            f"Cliente: {cot['cliente']} ({numero})\nTipo: {d['tipo'].upper()}\n"
            f"Total: {cot['total']}\n\nResponde: *APROBAR {numero}*  o  *EDITAR {numero}*")
        ok_doc = await cal_enviar_documento(adm, ruta, caption=f"Borrador {cot['folio']}")
        if not ok_doc:
            await enviar_mensaje(adm,
                f"⚠️ No pude adjuntar el PDF automáticamente, pero aquí está el enlace de descarga:\n"
                f"{cal_link_cotizacion(cot['folio'])}\n\n"
                f"Resumen: {cot['cliente']} · {d['tipo'].upper()} · {cot['total']}")
    await cal_registrar_lead({"tipo_lead": "COTIZACION_CALAMINAS", "estado": "NUEVO",
        "folio": cot["folio"], "numero": numero, "cliente": cot["cliente"],
        "comprobante": d["tipo"], "ruc": d.get("ruc", ""), "total": cot["total_value"], "fecha": cot["fecha"]})
    sesion["estado"] = S_CAL_POST
    sesion["datos"] = {"servicio": "CALAMINAS", "numero": numero, "folio": cot["folio"],
                       "pdf": ruta, "nombre": cot["cliente"]}
    await enviar_mensaje(numero,
        "✅ Listo, ya tengo tu pedido. Te preparo la cotización formal y te llega en el día.\n\n"
        "Antes de tu adelanto del 75%, ¿quieres que un *asesor de INCAMORE* confirme contigo los detalles?\n"
        "Responde *SI* para que te contacte, o *NO* si prefieres recibir los datos de pago.")

async def cal_comando_admin(numero, texto) -> bool:
    """Maneja 'APROBAR <num>' / 'EDITAR <num>' del admin. Devuelve True si lo atendió."""
    adm = _cal_admin()
    if not adm or numero != adm:
        return False
    up = (texto or "").strip().upper()
    if up.startswith("APROBAR ") or up.startswith("EDITAR "):
        partes = texto.strip().split()
        cli = partes[1] if len(partes) >= 2 else ""
        cli = cli if cli.startswith("51") else f"51{cli}"
        ruta = CAL_PENDIENTES.get(cli)
        if up.startswith("APROBAR "):
            if ruta:
                await cal_enviar_documento(cli, ruta, caption="📄 Tu cotización - INCAMORE S.A.C")
                await enviar_mensaje(cli, "Aquí tienes tu cotización 📄\n*INCAMORE S.A.C — Ingeniería a tu medida.*\nResponde *SI* si quieres que un asesor confirme contigo, o *NO* para recibir los datos de pago.")
                await enviar_mensaje(numero, f"✅ Cotización enviada al cliente {cli}.")
            else:
                await enviar_mensaje(numero, f"⚠️ No encontré borrador pendiente para {cli}.")
        else:
            await enviar_mensaje(numero, f"✏️ Ok, edita y reenvía manualmente la cotización de {cli}.")
        return True
    return False


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

    # ── Estructuras: admin aprueba/edita cotización de calaminas ──
    if await cal_comando_admin(numero, texto):
        return

    # Comando operador: ver calificaciones
    if texto.lower() in ["calificaciones", "/calificaciones", "ratings"]:
        await enviar_mensaje(numero, resumen_calificaciones())
        return

    # Comando cliente: ver historial
    if texto.lower() in ["mis viajes", "historial", "mis servicios", "/historial"]:
        await enviar_mensaje(numero, formato_historial(numero))
        return

    # ── Proveedor Seguridad responde COTIZO ──────────────────────────────────
    if es_proveedor_seg(numero) and texto.upper().startswith("COTIZO"):
        partes = texto.strip().split(maxsplit=3)
        # Formato: COTIZO [tel_cliente] [monto] [descripcion]
        if len(partes) >= 3:
            tel_raw     = partes[1].replace("+51", "").replace("51", "", 1) if partes[1].startswith("+51") or (partes[1].startswith("51") and len(partes[1]) == 11) else partes[1]
            num_cliente = tel_raw if tel_raw.startswith("51") else f"51{tel_raw}"
            monto_str   = partes[2]
            descripcion = partes[3] if len(partes) >= 4 else ""
            prov = next((p for p in proveedores_seg_aprobados() if p.get("telefono") == numero), {})
            prov_nombre  = prov.get("nombre", "Especialista")
            prov_negocio = prov.get("negocio", "") or prov_nombre

            if num_cliente not in solicitudes_seg_pendientes:
                await enviar_mensaje(numero,
                    f"❌ No encontré solicitud activa para el número {tel_raw}.\n"
                    f"Verifica el número e intenta de nuevo.")
                return

            lista = cotizaciones_seg_pendientes.setdefault(num_cliente, [])
            existente = next((c for c in lista if c.get("prov_num") == numero), None)
            if existente:
                existente.update({"monto": monto_str, "descripcion": descripcion})
            else:
                lista.append({
                    "prov_num": numero, "prov_nombre": prov_nombre,
                    "prov_negocio": prov_negocio, "monto": monto_str, "descripcion": descripcion,
                })

            datos_cli = sesiones.get(num_cliente, {}).get("datos", solicitudes_seg_pendientes.get(num_cliente, {}))
            sesiones[num_cliente] = {"estado": S_SEG_ELEGIR_COT, "datos": datos_cli}
            _seg_actualizar_servicio(datos_cli.get("id_servicio_seg", ""), num_cliente,
                cotizacion={"prov_num": numero, "prov_negocio": prov_negocio,
                            "prov_nombre": prov_nombre, "monto": monto_str, "descripcion": descripcion})

            await enviar_mensaje(numero,
                "✅ Cotización registrada. El cliente la verá y podrá elegir. ¡Gracias!")
            await enviar_mensaje(num_cliente, _seg_texto_opciones(num_cliente))
        else:
            await enviar_mensaje(numero,
                "⚠️ Formato incorrecto. Usa:\n"
                "*COTIZO [teléfono_cliente] [monto] [descripción breve]*\n\n"
                "Ejemplo: COTIZO 987654321 150 recarga 3 extintores 6kg")
        return

    # ── Profesor responde ACEPTO (Educación) — solo "acepto", sin número ──────
    _notificado_clase = any(
        numero in clases_pendientes[na].get("profesores_notificados", [])
        for na in clases_pendientes)
    if _es_profesor(numero) or _notificado_clase:
        _clases_profe = [na for na in clases_pendientes
                         if na not in clases_tomadas
                         and numero in clases_pendientes[na].get("profesores_notificados", [])]
        _txt_low = texto.strip().lower()
        _es_acepto = texto.upper().startswith("ACEPTO") or (
            _txt_low in {"acepto", "listo", "si", "sí", "ok", "dale", "voy", "ya", "tomo", "vamos"}
            and _clases_profe)
        if _es_acepto:
            partes = texto.strip().split()
            # ¿Vino número explícito? (ACEPTO 51999...)
            num_arg = partes[1].replace("+", "") if (partes[0].upper() == "ACEPTO" and len(partes) >= 2) else ""
            if num_arg:
                num_ap_full = num_arg if num_arg.startswith("51") else f"51{num_arg}"
                if num_ap_full not in clases_pendientes or num_ap_full in clases_tomadas:
                    await enviar_mensaje(numero, "❌ Esa clase ya no está disponible o fue tomada.")
                    return
                if numero not in clases_pendientes[num_ap_full].get("profesores_notificados", []):
                    await enviar_mensaje(numero, "❌ No estás en la lista de profesores para esta clase.")
                    return
                await _asignar_clase_a_profe(numero, num_ap_full)
            elif len(_clases_profe) == 1:
                await _asignar_clase_a_profe(numero, _clases_profe[0])
            elif len(_clases_profe) > 1:
                lista = "\n".join(
                    f"• Responde *ACEPTO {na}* — {clases_pendientes[na]['datos'].get('edu_alumno','alumno')}"
                    for na in _clases_profe)
                await enviar_mensaje(numero,
                    f"Tienes {len(_clases_profe)} clases pendientes. ¿Cuál tomas?\n\n{lista}")
            else:
                await enviar_mensaje(numero, "No tienes clases pendientes por aceptar.")
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
            marcar_servicio_atendido(numero_cliente_full, conductor.get("nombre", ""))

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
                marcar_servicio_atendido(numero_cliente_full, conductor.get("nombre", ""))

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

            # Educación: al volver a un paso, limpiar ese dato y TODOS los siguientes
            # (integridad: lo que viene después de lo que vas a corregir puede quedar inválido)
            EDU_ORDEN = [
                (S_EDU_PARA_QUIEN, ["edu_para_menor"]),
                (S_EDU_NOMBRE,     ["nombre", "edu_dni"]),
                (S_EDU_ALUMNO,     ["edu_alumno"]),
                (S_EDU_NIVEL,      ["edu_nivel"]),
                (S_EDU_MATERIA,    ["edu_materia"]),
                (S_EDU_MODALIDAD,  ["edu_modalidad"]),
                (S_EDU_DIRECCION,  ["edu_direccion"]),
            ]
            _estados_edu = [e for e, _ in EDU_ORDEN]
            if prev_estado in _estados_edu:
                idx = _estados_edu.index(prev_estado)
                for _, campos in EDU_ORDEN[idx:]:
                    for c in campos:
                        datos.pop(c, None)

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
            "_El Cuervo — siempre a tu servicio_ 🚖")
        return

    # Confirmar cancelación
    if datos.get("_confirmando_salida"):
        if texto == "1":
            sesiones.pop(numero, None)
            historial_ia.pop(numero, None)
            await enviar_mensaje(numero,
                "👋 *¡Hasta pronto!*\n\n"
                "Cuando necesites un servicio escribe *hola* o *1*.\n\n"
                "_El Cuervo — siempre a tu servicio_ 🚖")
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
                f"• *ACEPTO* — aceptar el servicio que te llegó\n"
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

    # ── Panel del proveedor (reengagement / baja) ────────────────────────────
    if estado == S_PROV_PANEL:
        await _panel_proveedor_respuesta(numero, sesion, texto)
        return
    if estado == S_PROV_BAJA:
        await _panel_proveedor_baja(numero, sesion, texto)
        return
    if estado == S_MENU and _es_saludo_activacion(texto):
        _prov = _proveedor_por_numero(numero)
        if _prov:
            await _mostrar_panel_proveedor(numero, _prov)
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

        OPCIONES_FINAL = ("\n\n━━━━━━━━━━━━━━━━\n1️⃣ Nuevo servicio\n0️⃣ Salir\n\n"
                          "💬 _O escríbeme tu pedido directo (ej: \"taxi a Puerto Supe para 3\") y te ayudo._")

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
        if es_consulta_calaminas(texto):
            await iniciar_calaminas(numero, sesion)
            return
        if texto == "1":
            await enrutar_categoria(numero, sesion, "TRANSPORTE")
        elif texto == "2":
            await enrutar_categoria(numero, sesion, "GASTRONOMIA")
        elif texto == "3":
            await enrutar_categoria(numero, sesion, "SEGURIDAD")
        elif texto == "4":
            await enrutar_categoria(numero, sesion, "EDUCACION")
        elif texto == "5":
            await enrutar_categoria(numero, sesion, "SERVICIOS_TECNICOS")
        elif texto == "6":
            await iniciar_calaminas(numero, sesion)
        elif texto == "7":
            await iniciar_unete(numero, sesion)
        elif texto == "0":
            sesiones.pop(numero, None)
            historial_ia.pop(numero, None)
            await enviar_mensaje(numero,
                "👋 *¡Hasta pronto!*\n\n"
                "Cuando necesites algo escribe *hola* o *menu*.\n\n"
                "_El Cuervo — servicios locales siempre a tu disposición_ 🦅")
        else:
            # ¿Quiere unirse como proveedor?
            _t = (texto or "").lower()
            if any(p in _t for p in ["unirme", "unir me", "trabajar con", "trabajar contigo",
                                     "quiero trabajar", "registrar mi", "registrarme",
                                     "ser parte", "afiliar", "afiliarme", "quiero ser conductor",
                                     "quiero ser profesor", "inscribir mi negocio", "abonado"]):
                await iniciar_unete(numero, sesion)
                return
            # Enrutador inteligente: detecta la intención del texto libre
            if not es_consulta_calaminas(texto):
                await enviar_mensaje(numero, "⏳ Un momento, ya te ayudo...")
            categoria = await clasificar_intencion(texto)
            print(f"[INTENCION] {numero}: '{texto}' -> {categoria}", flush=True)

            if categoria == "CALAMINAS":
                await iniciar_calaminas(numero, sesion)
                return
            if categoria == "TRANSPORTE":
                await _trans_entrar_texto_libre(numero, sesion, texto)
                return
            elif categoria == "GASTRONOMIA":
                await enrutar_categoria(numero, sesion, "GASTRONOMIA",
                    prefijo="🍽️ ¡Buenísimo! Te llevo a *Gastronomía*.\n\n")
            elif categoria == "SEGURIDAD":
                await _seg_entrar_texto_libre(numero, sesion, texto)
            elif categoria == "EDUCACION":
                extraido = await extraer_datos_educacion(texto)
                sesion["datos"] = {"servicio": "EDUCACION", **extraido}
                if extraido:
                    resumen_e = _edu_resumen_entendido(extraido)
                    if resumen_e:
                        await enviar_mensaje(numero, resumen_e)
                    await _edu_siguiente_paso(numero, sesion)
                else:
                    await enrutar_categoria(numero, sesion, "EDUCACION",
                        prefijo="📚 ¡Perfecto! Te llevo a *Educación*.\n\n")
            elif categoria == "SERVICIOS_TECNICOS":
                await _tec_entrar_texto_libre(numero, sesion, texto)
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

    # ══ ÚNETE / Registro de proveedores ═══════════════════════════════════════
    elif estado in _CAL_ESTADOS:
        await manejar_calaminas(numero, sesion, texto)

    elif estado == S_UNETE_TIPO:
        if texto == "0":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, MSG_BIENVENIDA)
            return
        if texto not in UNETE_TIPOS:
            await enviar_mensaje(numero, "Elige una opción del *1* al *6*, o *0* para volver.")
            return
        datos["unete_tipo"] = texto
        datos["unete_tipo_label"] = UNETE_TIPOS[texto]
        sesion["estado"] = S_UNETE_CONDICIONES
        await enviar_mensaje(numero, MSG_UNETE_CONDICIONES)

    elif estado == S_UNETE_CONDICIONES:
        if texto == "0":
            await iniciar_unete(numero, sesion)
            return
        if texto.strip().lower() not in ("acepto", "si", "sí", "ok", "acepta", "de acuerdo"):
            await enviar_mensaje(numero,
                "Para continuar necesito que aceptes las condiciones.\n"
                "Responde *ACEPTO*, o *0* para volver.")
            return
        sesion["estado"] = S_UNETE_NOMBRE
        await enviar_mensaje(numero,
            "🙋 Escribe tu *nombre completo*.\nEjemplo: Victor Calixto")

    elif estado == S_UNETE_NOMBRE:
        nombre = normalizar_nombre_persona(texto)
        if len(nombre) < 3:
            await enviar_mensaje(numero, "Por favor escribe tu nombre completo.")
            return
        datos["nombre"] = nombre
        t = datos.get("unete_tipo")
        if t == "1":  # gastronómico
            sesion["estado"] = S_UNETE_NEGOCIO
            await enviar_mensaje(numero, "🏪 ¿Cuál es el *nombre de tu negocio*?")
        elif t in ("2", "3"):  # taxista / colectivero
            sesion["estado"] = S_UNETE_PLACA
            await enviar_mensaje(numero, "🚗 ¿Cuál es la *placa* de tu vehículo?\nEjemplo: ABC-123")
        elif t == "4":  # profesor
            sesion["estado"] = S_UNETE_DETALLE
            await enviar_mensaje(numero,
                "📚 ¿Qué *niveles y materias* enseñas?\n_(Ej: primaria, matemática y comunicación)_")
        elif t == "6":  # técnico / especialista
            sesion["estado"] = S_UNETE_DETALLE
            await enviar_mensaje(numero,
                "🛠️ ¿Cuál es tu *oficio o especialidad*?\n"
                "_(Ej: soporte técnico de PC y celulares, gasfitería, cerrajería, electricista)_")
        else:  # seguridad
            sesion["estado"] = S_UNETE_DETALLE
            await enviar_mensaje(numero,
                "🛡️ ¿Cuál es tu *especialidad*?\n_(Ej: extintores, defensa civil, instalaciones)_")

    elif estado == S_UNETE_NEGOCIO:
        if len(texto.strip()) < 2:
            await enviar_mensaje(numero, "Por favor escribe el nombre de tu negocio.")
            return
        datos["unete_negocio"] = texto.strip()
        sesion["estado"] = S_UNETE_DIRECCION
        await enviar_mensaje(numero,
            "📍 ¿Cuál es la *dirección* de tu negocio?\n• Comparte tu ubicación 📌\n• O escríbela")

    elif estado == S_UNETE_DIRECCION:
        if tipo == "location" and isinstance(contenido, dict):
            datos["unete_direccion"] = await direccion_desde_gps(contenido.get("latitude"), contenido.get("longitude"))
        elif lat and lng:
            datos["unete_direccion"] = await direccion_desde_gps(lat, lng)
        elif (texto or "").strip():
            datos["unete_direccion"] = await limpiar_direccion(texto)
        else:
            await enviar_mensaje(numero, "Por favor escribe la dirección o comparte tu ubicación 📌.")
            return
        await _unete_mostrar_resumen(numero, sesion)

    elif estado == S_UNETE_PLACA:
        if len(texto.strip()) < 4:
            await enviar_mensaje(numero, "Por favor escribe la placa de tu vehículo.\nEjemplo: ABC-123")
            return
        datos["unete_placa"] = texto.strip().upper()
        await _unete_mostrar_resumen(numero, sesion)

    elif estado == S_UNETE_DETALLE:
        if len(texto.strip()) < 3:
            await enviar_mensaje(numero, "Cuéntame un poco más, por favor.")
            return
        datos["unete_detalle"] = texto.strip()
        await _unete_mostrar_resumen(numero, sesion)

    elif estado == S_UNETE_CONFIRMAR:
        if texto == "1" or texto.strip().lower() in ("confirmo", "si", "sí", "ok"):
            await _unete_finalizar(numero, sesion)
        elif texto == "2" or texto.strip().lower() in ("no", "cancelar"):
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, "❌ Registro cancelado.\n\n" + MSG_BIENVENIDA)
        else:
            await enviar_mensaje(numero, "Responde *1* para confirmar o *2* para cancelar.")

    # ══ SERVICIOS TÉCNICOS ════════════════════════════════════════════════════
    elif estado == S_TEC_OFICIO:
        if texto == "0":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, MSG_BIENVENIDA)
            return
        if texto not in TEC_OFICIOS:
            await enviar_mensaje(numero, "Elige una opción del *1* al *6*, o *0* para volver.")
            return
        datos["tec_oficio"] = TEC_OFICIOS[texto]
        if datos.get("tec_problema"):
            sesion["estado"] = S_TEC_DIRECCION
            await enviar_mensaje(numero,
                "📍 ¿Dónde sería el servicio?\n• Comparte tu ubicación 📌\n• O escribe la dirección")
        else:
            sesion["estado"] = S_TEC_PROBLEMA
            await enviar_mensaje(numero,
                f"🛠️ *{datos['tec_oficio']}*\n\n"
                "Cuéntame, ¿cuál es el problema o qué necesitas? "
                "Descríbelo con el mayor detalle posible.")

    elif estado == S_TEC_PROBLEMA:
        if len((texto or "").strip()) < 4:
            await enviar_mensaje(numero, "Por favor descríbeme un poco más qué necesitas.")
            return
        datos["tec_problema"] = texto.strip()
        sesion["estado"] = S_TEC_DIRECCION
        await enviar_mensaje(numero,
            "📍 ¿Dónde sería el servicio?\n• Comparte tu ubicación 📌\n• O escribe la dirección")

    elif estado == S_TEC_DIRECCION:
        if tipo == "location" and isinstance(contenido, dict):
            datos["tec_direccion"] = await direccion_desde_gps(contenido.get("latitude"), contenido.get("longitude"))
        elif lat and lng:
            datos["tec_direccion"] = await direccion_desde_gps(lat, lng)
        elif (texto or "").strip():
            datos["tec_direccion"] = await limpiar_direccion(texto)
        else:
            await enviar_mensaje(numero, "Por favor escribe la dirección o comparte tu ubicación 📌.")
            return
        sesion["estado"] = S_TEC_CUANDO
        await enviar_mensaje(numero,
            "🕒 ¿Para cuándo lo necesitas?\n_(Ej: hoy en la tarde, mañana 9am, lo antes posible)_")

    elif estado == S_TEC_CUANDO:
        if len((texto or "").strip()) < 2:
            await enviar_mensaje(numero, "Cuéntame para cuándo lo necesitas.")
            return
        datos["tec_cuando"] = texto.strip()
        sesion["estado"] = S_TEC_CONFIRMAR
        await enviar_mensaje(numero,
            "📋 *Confirma tu solicitud:*\n\n"
            f"🛠️ {datos.get('tec_oficio','')}\n"
            f"📝 {datos.get('tec_problema','')}\n"
            f"📍 {datos.get('tec_direccion','')}\n"
            f"🕒 {datos.get('tec_cuando','')}\n\n"
            "_El técnico coordinará el precio contigo según el trabajo._\n\n"
            "1️⃣ Confirmar y enviar\n"
            "2️⃣ Cancelar")

    elif estado == S_TEC_CONFIRMAR:
        if texto == "1" or texto.strip().lower() in ("confirmo", "si", "sí", "ok"):
            await _tec_finalizar(numero, sesion)
        elif texto == "2" or texto.strip().lower() in ("no", "cancelar"):
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, "❌ Solicitud cancelada.\n\n" + MSG_BIENVENIDA)
        else:
            await enviar_mensaje(numero, "Responde *1* para confirmar o *2* para cancelar.")

    # ══ TRANSPORTE (El Cuervo) ═══════════════════════════════════════════
    elif estado == S_TRANSPORTE_MENU:
        if texto_es_promo(texto):
            datos["promo_activa"] = True
            datos["promo_codigo"] = PROMO_CODIGO
            await enviar_mensaje(numero,
                "🎉 *Promo de lanzamiento El Cuervo*\n\n"
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
        if datos.get("seg_descripcion"):
            sesion["estado"] = S_SEG_UBICACION
            await enviar_mensaje(numero,
                "📍 *¿Cuál es la dirección donde se realizará el servicio?*\n"
                "• Comparte tu ubicación 📌\n"
                "• O escribe la dirección completa" + NAV)
        else:
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

    elif estado == S_SEG_ELEGIR_COT:
        lista = cotizaciones_seg_pendientes.get(numero, [])
        if not lista:
            await enviar_mensaje(numero,
                "⏳ Aún no hay cotizaciones. Te avisaremos en cuanto lleguen." + NAV)
            return
        if not texto.isdigit() or not (1 <= int(texto) <= len(lista)):
            await enviar_mensaje(numero, _seg_texto_opciones(numero))
            return
        elegida = lista[int(texto) - 1]
        cotizaciones_seg_pendientes.pop(numero, None)
        solicitudes_seg_pendientes.pop(numero, None)
        datos["seg_cotizacion_aceptada"] = elegida.get("monto", "")
        datos["seg_proveedor"] = elegida.get("prov_negocio", "")
        datos["seg_estado"] = "CONFIRMADO"
        nombre_cliente = datos.get("nombre", "Cliente")
        tel_cliente = telefono_sin_51(numero)
        # Avisar al proveedor elegido
        await enviar_mensaje(elegida.get("prov_num", ""),
            f"✅ *¡Te eligieron!*\n\n"
            f"👤 Cliente: {nombre_cliente}\n"
            f"📱 Teléfono: +{tel_cliente}\n"
            f"🛡️ Servicio: {datos.get('seg_subcategoria','')}\n"
            f"📍 Dirección: {datos.get('seg_ubicacion','')}\n"
            f"💰 Monto: S/{elegida.get('monto','')}\n"
            f"⏰ Urgencia: {datos.get('seg_urgencia','')}\n"
            f"{'📅 Fecha: ' + datos.get('seg_fecha_programada','') if datos.get('seg_fecha_programada') else ''}\n\n"
            f"Coordina directamente con el cliente. ¡Éxitos! 🦅")
        # Avisar a los demás proveedores
        for c in lista:
            if c.get("prov_num") and c.get("prov_num") != elegida.get("prov_num"):
                await enviar_mensaje(c["prov_num"],
                    "Gracias por cotizar. En esta ocasión el cliente eligió otra opción. "
                    "Te avisaremos en la próxima solicitud 🦅")
        # Registrar en el dashboard (Sheets)
        _seg_actualizar_servicio(datos.get("id_servicio_seg", ""), numero,
            estado="atendido", proveedor=elegida.get("prov_negocio", ""), monto=elegida.get("monto", ""))
        asyncio.create_task(sheets_evento("upsert_servicio", {
            "FECHA":        datetime.now().strftime("%d/%m/%Y %H:%M"),
            "ID_SERVICIO":  generar_id_servicio(numero, "SEG"),
            "CATEGORIA":    "SEGURIDAD",
            "SUBCATEGORIA": datos.get("seg_subcategoria", ""),
            "CLIENTE":      datos.get("nombre", ""),
            "TELEFONO":     telefono_sin_51(numero),
            "DESCRIPCION":  datos.get("seg_descripcion", ""),
            "UBICACION":    datos.get("seg_ubicacion", ""),
            "URGENCIA":     datos.get("seg_urgencia", ""),
            "PROVEEDOR":    elegida.get("prov_negocio", ""),
            "MONTO":        elegida.get("monto", ""),
            "ESTADO":       "CONFIRMADO",
        }))
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        await enviar_mensaje(numero,
            f"✅ *¡Servicio confirmado!*\n\n"
            f"🛡️ *{datos.get('seg_subcategoria','')}*\n"
            f"👷 Especialista: *{elegida.get('prov_negocio','')}*\n"
            f"💰 Monto: *S/{elegida.get('monto','')}*\n\n"
            f"El especialista coordinará contigo los detalles finales.\n\n"
            f"Escribe *menu* para volver al inicio 🦅")

    # ══ EDUCACIÓN ══════════════════════════════════════════════════════════════
    elif estado == S_EDU_PARA_QUIEN:
        if texto == "1":
            datos["edu_para_menor"] = False
            await _edu_siguiente_paso(numero, sesion)
        elif texto == "2":
            datos["edu_para_menor"] = True
            await _edu_siguiente_paso(numero, sesion)
        else:
            await enviar_mensaje(numero,
                "Responde *1* (para mí) o *2* (para un menor a mi cargo), o *0* para volver." + NAV)

    elif estado == S_EDU_NOMBRE:
        nombre, dni = extraer_nombre_dni(texto)
        if not dni or len(nombre) < 3:
            await enviar_mensaje(numero,
                "Necesito tu *nombre y DNI* juntos.\nEjemplo: *Victor Calixto 12345678*" + NAV)
            return
        datos["nombre"] = nombre
        datos["edu_dni"] = dni
        await _edu_siguiente_paso(numero, sesion)

    elif estado == S_EDU_ALUMNO:
        alumno = normalizar_nombre_persona(texto)
        if len(alumno) < 2:
            await enviar_mensaje(numero, "Por favor escribe el nombre del alumno/a." + NAV)
            return
        datos["edu_alumno"] = alumno
        await _edu_siguiente_paso(numero, sesion)

    elif estado == S_EDU_NIVEL:
        mapa = {"1": "PRIMARIA", "2": "SECUNDARIA", "3": "PREUNIVERSITARIO"}
        if texto not in mapa:
            # Salida elegante: si pide nivel universitario/superior (fuera de alcance)
            t = (texto or "").lower()
            if any(w in t for w in ["universi", "superior", "instituto", "carrera",
                                    "calculo", "cálculo", "contabilidad", "ingenieria",
                                    "ingeniería", "ceba"]):
                print(f"[DEMANDA] educacion superior solicitada por {numero}: '{texto}'", flush=True)
                await enviar_mensaje(numero,
                    "🙏 Por ahora ofrecemos *reforzamiento escolar* (primaria a preuniversitario). "
                    "Aún no contamos con profesores de nivel universitario/superior — "
                    "pero anoté tu interés para sumarlo pronto.\n\n"
                    "¿Te ayudamos con alguno de estos niveles?\n"
                    "1️⃣ Primaria\n2️⃣ Secundaria\n3️⃣ Preuniversitario" + NAV)
                return
            await enviar_mensaje(numero,
                "Elige *1* Primaria, *2* Secundaria o *3* Preuniversitario." + NAV)
            return
        datos["edu_nivel"] = mapa[texto]
        await _edu_siguiente_paso(numero, sesion)

    elif estado == S_EDU_MATERIA:
        if not texto or len((texto or "").strip()) < 2:
            await enviar_mensaje(numero, "Cuéntame brevemente la materia o tema." + NAV)
            return
        datos["edu_materia"] = texto.strip()
        await _edu_siguiente_paso(numero, sesion)

    elif estado == S_EDU_MODALIDAD:
        if texto == "1":
            datos["edu_modalidad"] = "presencial"
            await _edu_siguiente_paso(numero, sesion)
        elif texto == "2":
            datos["edu_modalidad"] = "virtual"
            await _edu_siguiente_paso(numero, sesion)
        else:
            await enviar_mensaje(numero, "Elige *1* Presencial o *2* Virtual (Zoom)." + NAV)

    elif estado == S_EDU_DIRECCION:
        if tipo == "location" and isinstance(contenido, dict):
            direccion = await direccion_desde_gps(contenido.get("latitude"), contenido.get("longitude"))
        elif lat and lng:
            direccion = await direccion_desde_gps(lat, lng)
        else:
            if not (texto or "").strip() or len((texto or "").strip()) < 3:
                await enviar_mensaje(numero,
                    "Por favor escribe la dirección o comparte tu ubicación 📌." + NAV)
                return
            direccion = await limpiar_direccion(texto)
        datos["edu_direccion"] = direccion
        await _edu_siguiente_paso(numero, sesion)

    elif estado == S_EDU_CONFIRMAR:
        if texto == "1":
            registrar_servicio("EDUCACION", datos, numero)
            await notificar_profesores(sesion, numero)
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
        elif texto == "2":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                "❌ Solicitud cancelada.\n\nEscribe *menu* para volver al inicio.")
        else:
            await enviar_mensaje(numero, "Responde *1* para confirmar o *2* para cancelar." + NAV)

    # ══ CONSULTA OPCION ═══════════════════════════════════════════════════════
    elif estado == S_CONSULTA_OPCION:
        if texto == "1":
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero, MSG_BIENVENIDA)
        elif texto == "2":
            await notificar_operador_consulta(numero, datos.get("ultima_consulta",""), datos.get("ultima_respuesta",""))
            sesiones[numero] = {"estado": S_MENU, "datos": {}}
            await enviar_mensaje(numero,
                "👤 *¡Listo!* Un asesor te *llamará en breve* a este mismo número. 📞\n\n"
                "No necesitas hacer nada más, nosotros te contactamos.\n\n"
                "Escribe *menu* si deseas algo más mientras tanto.")
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
        await _trans_tras_nombre(numero, sesion)

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
            await _trans_post_recojo(numero, sesion)
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
            await _trans_post_recojo(numero, sesion)
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
                    await _trans_post_recojo(numero, sesion)
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
            registrar_servicio("TAXI", datos, numero)
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
            registrar_servicio("COLECTIVO", datos, numero)
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
                # Barranca mal indexado → aceptar texto libre
                direccion = await limpiar_direccion(texto)
                datos["enc_origen"] = direccion
                sesion["estado"] = S_ENCOMIENDA_DESTINO
                await enviar_mensaje(numero,
                    f"✅ Recojo: *{direccion}*\n\n"
                    "🏁 *¿A qué dirección lo enviamos?*\n\n"
                    "• 📌 Comparte ubicación del destino\n"
                    "• ✍️ O escribe la dirección")
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
                direccion = await limpiar_direccion(texto)
                datos["enc_destino_temp"] = direccion
                sesion["estado"] = S_ENCOMIENDA_CONFIRM_DEST
                await enviar_mensaje(numero,
                    f"📍 Destino: *{direccion}*\n\n"
                    "¿Es correcto?\n"
                    "1️⃣ Sí\n"
                    "2️⃣ No, escribir otra dirección")
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
                direccion = await limpiar_direccion(texto)
                datos["enc_destino_temp"] = direccion
                sesion["estado"] = S_ENCOMIENDA_CONFIRM_DEST
                await enviar_mensaje(numero,
                    f"📍 Destino: *{direccion}*\n\n"
                    "¿Es correcto?\n1️⃣ Sí\n2️⃣ No, escribir otra dirección")
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
            registrar_servicio("ENCOMIENDA", datos, numero)
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
                direccion = await limpiar_direccion(texto)
                datos["recojo_temp"] = direccion
                datos["_esperando_confirm_recojo"] = True
                await enviar_mensaje(numero,
                    f"📍 *{direccion}*\n\n"
                    "¿Es correcto?\n1️⃣ Sí\n2️⃣ No, escribir otra")
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
            registrar_servicio("TURISMO", datos, numero)
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

            # Persistir el estado tras cada mensaje (sobrevive reinicios/deploys)
            guardar_estado()

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
                    f"— Equipo El Cuervo 🚖")
            return {"ok": True, "ticket": t}
    raise HTTPException(status_code=404, detail="Ticket no encontrado")

def _pagina_resultado(titulo, mensaje, color):
    from fastapi.responses import HTMLResponse
    return HTMLResponse(f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1"><title>El Cuervo</title></head>
    <body style="margin:0;background:#0a0b10;color:#e9e9ef;font-family:-apple-system,Segoe UI,Roboto,sans-serif;
    display:flex;align-items:center;justify-content:center;min-height:100vh">
      <div style="background:#13141b;border:1px solid #23242e;border-radius:18px;padding:40px 46px;text-align:center;max-width:440px">
        <div style="font-size:54px;margin-bottom:10px">{color}</div>
        <h1 style="color:#e8b04b;margin:0 0 8px;font-size:24px">{titulo}</h1>
        <p style="color:#cfd0db;font-size:16px;line-height:1.5">{mensaje}</p>
        <p style="color:#6a6b76;font-size:13px;margin-top:22px">El Cuervo 🦅 · Panel de validación</p>
        <p id="cd" style="color:#6a6b76;font-size:12px;margin-top:6px">Esta ventana se cerrará en 3 s…</p>
      </div>
      <script>
        var s=3, el=document.getElementById('cd');
        var t=setInterval(function(){{
          s--;
          if(s>0){{ el.textContent='Esta ventana se cerrará en '+s+' s…'; }}
          else {{ clearInterval(t); window.close(); setTimeout(function(){{ el.textContent='Ya puedes cerrar esta pestaña.'; }},400); }}
        }},1000);
      </script>
    </body></html>""")


@app.get("/proveedor/validar")
async def proveedor_validar(clave: str = "", id: str = ""):
    if clave != ADMIN_KEY:
        return _pagina_resultado("Acceso denegado", "Clave incorrecta.", "🔒")
    reg = actualizar_estado_proveedor(id, "EN_VALIDACION")
    if not reg:
        return _pagina_resultado("No encontrado", f"No se encontró el registro {id}.", "⚠️")
    try:
        await enviar_mensaje(reg.get("telefono", ""),
            f"🔍 *Hola {reg.get('nombre','')},*\n\n"
            "Recibimos tu registro en *El Cuervo* 🦅 y estamos *verificando tus datos*. "
            "Te confirmaremos apenas termine la validación.\n\n"
            "_Gracias por tu paciencia._")
    except Exception:
        pass
    return _pagina_resultado("En validación",
        f"<b>{reg.get('nombre','')}</b> ({reg.get('tipo','')}) quedó <b>EN VALIDACIÓN</b>. "
        "Todavía NO está activo en el bot. Se le avisó que estás verificando sus datos.", "🔍")


@app.get("/proveedor/aprobar")
async def proveedor_aprobar(clave: str = "", id: str = ""):
    if clave != ADMIN_KEY:
        return _pagina_resultado("Acceso denegado", "Clave incorrecta.", "🔒")
    reg = actualizar_estado_proveedor(id, "APROBADO")
    if not reg:
        return _pagina_resultado("No encontrado", f"No se encontró el registro {id}.", "⚠️")
    try:
        await enviar_mensaje(reg.get("telefono", ""),
            f"🎉 *¡Felicidades, {reg.get('nombre','')}!*\n\n"
            "Tu registro en *El Cuervo* 🦅 fue *APROBADO*. "
            "Ya eres parte de la red y empezarás a recibir solicitudes de clientes.\n\n"
            "_Gracias por sumarte. ¡A trabajar juntos!_")
    except Exception:
        pass
    return _pagina_resultado("Proveedor aprobado",
        f"<b>{reg.get('nombre','')}</b> ({reg.get('tipo','')}) ya está <b>ACTIVO</b> en El Cuervo. "
        "Se le notificó por WhatsApp.", "✅")


@app.get("/proveedor/rechazar")
async def proveedor_rechazar(clave: str = "", id: str = "", motivo: str = "otro"):
    if clave != ADMIN_KEY:
        return _pagina_resultado("Acceso denegado", "Clave incorrecta.", "🔒")
    reg = actualizar_estado_proveedor(id, "RECHAZADO")
    if not reg:
        return _pagina_resultado("No encontrado", f"No se encontró el registro {id}.", "⚠️")
    motivo_txt = MOTIVOS_RECHAZO.get(motivo, MOTIVOS_RECHAZO["otro"])
    try:
        await enviar_mensaje(reg.get("telefono", ""),
            f"Hola {reg.get('nombre','')}, gracias por tu interés en *El Cuervo* 🦅\n\n"
            f"Por ahora *no pudimos aprobar tu registro* porque {motivo_txt}.\n\n"
            "Puedes volver a postular más adelante corrigiendo este punto. "
            "Agradecemos tu comprensión.")
    except Exception:
        pass
    return _pagina_resultado("Registro rechazado",
        f"<b>{reg.get('nombre','')}</b> ({reg.get('tipo','')}) fue <b>RECHAZADO</b>.<br>"
        f"Motivo enviado: <i>{motivo_txt}</i>", "❌")


@app.get("/admin/limpiar")
async def admin_limpiar(clave: str = "", que: str = "", confirmar: str = ""):
    """Limpia datos en disco para empezar de cero. NO toca conductores ni profesores (están en código).
    Uso: /admin/limpiar?clave=ADMIN_KEY&que=todo&confirmar=SI
    que = proveedores | servicios | todo"""
    if clave != ADMIN_KEY:
        return _pagina_resultado("Acceso denegado", "Clave incorrecta.", "🔒")

    objetivos = {
        "proveedores": [PROVEEDORES_FILE],
        "servicios": [SERVICIOS_FILE],
        "todo": [PROVEEDORES_FILE, SERVICIOS_FILE],
    }
    if que not in objetivos:
        return _pagina_resultado("Falta indicar qué limpiar",
            "Agrega <b>&amp;que=proveedores</b>, <b>&amp;que=servicios</b> o <b>&amp;que=todo</b> a la URL.", "⚠️")

    if confirmar != "SI":
        # contar lo que se borraría
        resumen = []
        for f in objetivos[que]:
            n = 0
            try:
                if os.path.exists(f):
                    with open(f, "r", encoding="utf-8") as fh:
                        n = len(json.load(fh) or [])
            except Exception:
                n = 0
            resumen.append(f"{os.path.basename(f)}: {n} registro(s)")
        base = os.getenv("PUBLIC_URL", "https://barranca-movil-bot.onrender.com").rstrip("/")
        url_conf = f"{base}/admin/limpiar?clave={ADMIN_KEY}&que={que}&confirmar=SI"
        from fastapi.responses import HTMLResponse
        return HTMLResponse(f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1"><title>El Cuervo</title></head>
        <body style="margin:0;background:#0a0b10;color:#e9e9ef;font-family:-apple-system,Segoe UI,Roboto,sans-serif;
        display:flex;align-items:center;justify-content:center;min-height:100vh">
          <div style="background:#13141b;border:1px solid #5a2a2a;border-radius:18px;padding:38px 44px;text-align:center;max-width:480px">
            <div style="font-size:50px">⚠️</div>
            <h1 style="color:#ff9a9a;margin:6px 0 10px;font-size:22px">Confirmar limpieza</h1>
            <p style="color:#cfd0db;font-size:15px">Vas a borrar (<b>{que}</b>):</p>
            <p style="color:#e8b04b;font-size:14px">{'<br>'.join(resumen)}</p>
            <p style="color:#9a9ba6;font-size:13px">Los <b>conductores</b> y <b>profesores</b> NO se tocan.<br>Esta acción no se puede deshacer.</p>
            <a href="{url_conf}" style="display:inline-block;background:#c0392b;color:#fff;text-decoration:none;
               padding:13px 32px;border-radius:9px;font-weight:bold;margin-top:14px">Sí, borrar ahora</a>
            <p style="color:#6a6b76;font-size:12px;margin-top:20px">El Cuervo 🦅</p>
          </div></body></html>""")

    # confirmado: vaciar archivos
    borrados = []
    for f in objetivos[que]:
        try:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump([], fh)
            borrados.append(os.path.basename(f))
            print(f"[LIMPIEZA] {f} vaciado", flush=True)
        except Exception as e:
            print(f"[LIMPIEZA ERROR] {f}: {e}", flush=True)
    return _pagina_resultado("Limpieza completada",
        f"Se limpiaron: <b>{', '.join(borrados)}</b>.<br>"
        "Conductores y profesores intactos. Ya puedes empezar de cero. 🦅", "🧹")


@app.get("/proveedores")
async def get_proveedores(clave: str = ""):
    """Lista los proveedores/abonados registrados. Requiere ?clave=ADMIN_KEY."""
    if clave != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Clave incorrecta")
    try:
        if not os.path.exists(PROVEEDORES_FILE):
            return {"total": 0, "proveedores": []}
        with open(PROVEEDORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or []
        # más recientes primero
        data_ord = list(reversed(data))
        return {
            "total": len(data),
            "pendientes": sum(1 for p in data if p.get("estado") in ("PENDIENTE_VALIDACION", "EN_VALIDACION")),
            "por_tipo": {t: sum(1 for p in data if p.get("tipo") == t)
                         for t in sorted({p.get("tipo", "") for p in data})},
            "proveedores": data_ord,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo registros: {e}")

DASHBOARD_HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Dashboard El Cuervo</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,"Segoe UI",Roboto,sans-serif;}
  body{background:#f4f5f9;color:#1f2330;display:flex;min-height:100vh;}
  /* Sidebar */
  .side{width:248px;background:#0e0f15;color:#cfd0db;flex-shrink:0;padding:22px 16px;position:sticky;top:0;height:100vh;overflow:auto;}
  .side .logo{display:flex;align-items:center;gap:10px;margin-bottom:26px;}
  .side .logo .em{width:40px;height:40px;border-radius:10px;background:#15161d;border:1px solid #e8b04b;display:flex;align-items:center;justify-content:center;font-size:20px;}
  .side .logo b{font-size:17px;letter-spacing:1px;color:#fff;}
  .side .logo small{display:block;font-size:9px;color:#e8b04b;letter-spacing:2px;}
  .side .sec{font-size:10px;color:#5d5f6e;text-transform:uppercase;letter-spacing:1px;margin:18px 8px 8px;}
  .side a{display:flex;align-items:center;gap:11px;padding:11px 12px;border-radius:9px;color:#b9bac6;text-decoration:none;font-size:14px;cursor:pointer;}
  .side a:hover{background:#191a22;color:#fff;}
  .side a.act{background:linear-gradient(90deg,#1d2740,#161824);color:#fff;}
  .side a .ic{width:18px;text-align:center;opacity:.9;}
  .side a .rec{margin-left:auto;background:#2a1e12;color:#e8b04b;border:1px solid #5a4423;font-size:9px;font-weight:700;letter-spacing:.4px;padding:2px 7px;border-radius:20px;text-transform:uppercase;}
  /* Main */
  .main{flex:1;padding:24px 28px;overflow:auto;}
  .head{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:22px;}
  .head h1{font-size:24px;font-weight:800;}
  .head p{font-size:13px;color:#7b7e8d;}
  .head .tools{display:flex;gap:10px;align-items:center;}
  .chip{background:#fff;border:1px solid #e3e5ee;border-radius:10px;padding:9px 14px;font-size:13px;color:#444;display:flex;align-items:center;gap:7px;}
  .chip.dark{background:#0e0f15;color:#fff;border:none;cursor:pointer;}
  .live{font-size:12px;color:#27a06b;display:flex;align-items:center;gap:6px;}
  .ldot{width:8px;height:8px;border-radius:50%;background:#27a06b;}
  /* KPIs */
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:18px;}
  .kpi{background:#fff;border:1px solid #eceef4;border-radius:16px;padding:16px;display:flex;gap:13px;align-items:center;box-shadow:0 1px 3px rgba(20,20,40,.04);}
  .kpi .ico{width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;}
  .kpi .l{font-size:12px;color:#8a8d9c;}
  .kpi .v{font-size:26px;font-weight:800;line-height:1.1;}
  .kpi .s{font-size:11px;color:#27a06b;margin-top:2px;}
  .i1{background:#eef0ff;color:#5b6cff;} .i2{background:#e7f8ef;color:#22b07d;}
  .i3{background:#eaf3ff;color:#3b8ff0;} .i4{background:#fff0e6;color:#ff8a3c;}
  .i5{background:#f0eaff;color:#8b5bff;} .i6{background:#e7f9f5;color:#13b8a6;}
  /* Cards grid */
  .row{display:grid;gap:16px;margin-bottom:16px;}
  .r3{grid-template-columns:1.3fr 1fr 1.1fr;}
  .r2{grid-template-columns:1fr 1.2fr;}
  @media(max-width:1100px){.r3,.r2{grid-template-columns:1fr;}}
  .card{background:#fff;border:1px solid #eceef4;border-radius:16px;padding:18px;box-shadow:0 1px 3px rgba(20,20,40,.04);}
  .card h3{font-size:15px;font-weight:700;margin-bottom:3px;}
  .card .sub{font-size:11px;color:#9a9db0;margin-bottom:14px;}
  .chartbox{position:relative;height:240px;}
  .chartbox.sm{height:210px;}
  table{width:100%;border-collapse:collapse;font-size:13px;}
  th{text-align:left;color:#9a9db0;font-weight:600;font-size:11px;text-transform:uppercase;padding:8px 6px;border-bottom:1px solid #eceef4;}
  td{padding:10px 6px;border-bottom:1px solid #f2f3f8;}
  tr:last-child td{border-bottom:none;}
  .badge{padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600;}
  .bp{background:#fff0e6;color:#e07b2e;} .bo{background:#e7f8ef;color:#22b07d;}
  .bv{background:#fff5d6;color:#c89400;}
  .pill{display:inline-block;background:#f0f1f6;color:#555;padding:2px 8px;border-radius:6px;font-size:11px;margin:2px 3px 2px 0;}
  .empty{color:#a9abb8;font-size:13px;text-align:center;padding:16px;}
  .foot{text-align:center;color:#aaadbb;font-size:12px;margin-top:14px;}
  .err{background:#fde8e8;border:1px solid #f5c2c2;color:#c0392b;padding:14px;border-radius:10px;text-align:center;}
</style>
</head>
<body>
  <div class="side">
    <div class="logo"><div class="em">&#129413;</div><div><b>EL CUERVO</b><small>RED DE SERVICIOS</small></div></div>
    <div class="sec">Módulo de análisis</div>
    <a class="act"><span class="ic">&#9632;</span> Resumen general</a>
    <a><span class="ic">&#128661;</span> Transporte<span class="rec">Reclutando</span></a>
    <a><span class="ic">&#128218;</span> Educación<span class="rec">Reclutando</span></a>
    <a><span class="ic">&#128737;</span> Seguridad<span class="rec">Reclutando</span></a>
    <a><span class="ic">&#128295;</span> Servicios Técnicos<span class="rec">Reclutando</span></a>
    <a><span class="ic">&#127869;</span> Gastronomía<span class="rec">Reclutando</span></a>
    <div class="sec">Red</div>
    <a><span class="ic">&#129309;</span> Proveedores</a>
    <a><span class="ic">&#127903;</span> Tickets</a>
    <div class="sec">Estado</div>
    <div style="padding:12px;background:#13141b;border-radius:10px;font-size:12px;color:#8a8c98;">
      <div style="color:#27c08a;">&#9679; Bot en línea</div>
      <div style="margin-top:6px;">Actualizado:<br><span id="upd2" style="color:#cfd0db;">—</span></div>
    </div>
  </div>

  <div class="main">
    <div class="head">
      <div><h1>Dashboard Integral de Servicios</h1><p>Monitoreo operativo de El Cuervo · Barranca</p></div>
      <div class="tools">
        <span class="chip" id="fecha">Hoy: —</span>
        <span class="live"><span class="ldot"></span> En vivo</span>
        <span class="chip dark" onclick="load()">&#8635; Actualizar</span>
      </div>
    </div>
    <div id="root"><p class="empty">Cargando datos…</p></div>
    <div class="foot">El Cuervo &#169; 2026 · actualización automática cada 15 s</div>
  </div>

<script>
const clave = new URLSearchParams(location.search).get('clave') || '';
const $ = s => document.querySelector(s);
let charts = {};
const PAL = ['#5b6cff','#22b07d','#ff8a3c','#8b5bff','#13b8a6','#f0567a','#3b8ff0','#c89400'];

function kpi(ico,cls,val,lab,sub){
  return `<div class="kpi"><div class="ico ${cls}">${ico}</div><div><div class="l">${lab}</div><div class="v">${val}</div>${sub?`<div class="s">${sub}</div>`:''}</div></div>`;
}
function destroyCharts(){ Object.values(charts).forEach(c=>{try{c.destroy()}catch(e){}}); charts={}; }

function render(d){
  destroyCharts();
  const k=d.kpis;
  let html = `<div class="kpis">
    ${kpi('&#128203;','i1',k.solicitudes_hoy,'Solicitudes hoy')}
    ${kpi('&#9989;','i2',k.servicios_completados,'Servicios completados')}
    ${kpi('&#128661;','i4',k.conductores_activos+'/'+k.conductores_total,'Conductores activos', k.conductores_en_ruta+' en ruta')}
    ${kpi('&#128218;','i3',k.profesores_total,'Profesores')}
    ${kpi('&#127970;','i5',k.proveedores_total,'Proveedores', k.proveedores_pendientes+' por validar')}
    ${kpi('&#128202;','i6',k.tasa_atencion+'%','Tasa de atención')}
  </div>`;

  html += `<div class="row r3">
    <div class="card"><h3>Tendencia de solicitudes</h3><div class="sub">Últimos 7 días</div><div class="chartbox"><canvas id="cTend"></canvas></div></div>
    <div class="card"><h3>Solicitudes por categoría</h3><div class="sub">Distribución</div><div class="chartbox"><canvas id="cCat"></canvas></div></div>
    <div class="card"><h3>Estado de servicios</h3><div class="sub">Total ${k.servicios_total}</div><div class="chartbox"><canvas id="cEst"></canvas></div></div>
  </div>`;

  html += `<div class="row r2">
    <div class="card"><h3>Ranking de proveedores</h3><div class="sub">Por servicios atendidos</div><div id="rank"></div></div>
    <div class="card"><h3>Resumen por categoría</h3><div class="sub">Solicitudes vs atendidos</div><div id="tcat"></div></div>
  </div>`;

  html += `<div class="row r2">
    <div class="card"><h3>Proveedores registrados</h3><div class="sub">${k.proveedores_pendientes} por validar</div><div id="prov"></div></div>
    <div class="card"><h3>Conductores</h3><div class="sub">${k.conductores_activos} activos</div><div id="cond"></div></div>
    <div class="card"><h3>Servicios Técnicos</h3><div class="sub">Técnicos registrados</div><div id="tec"></div></div>
  </div>`;

  $('#root').innerHTML = html;
  $('#upd2').textContent = d.actualizado; $('#fecha').textContent = 'Hoy: '+d.actualizado.split(' ')[0];

  // Ranking
  let rk = d.ranking_proveedores.length? '<table><tr><th>#</th><th>Proveedor</th><th>Atendidos</th></tr>' : '';
  d.ranking_proveedores.forEach((r,i)=>{ rk+=`<tr><td>${i+1}</td><td>${r.proveedor}</td><td><b>${r.atendidos}</b></td></tr>`; });
  rk += d.ranking_proveedores.length? '</table>' : '<p class="empty">Aún sin servicios atendidos</p>';
  $('#rank').innerHTML = rk;

  // Tabla categoría
  let tc = d.tabla_categoria.length? '<table><tr><th>Categoría</th><th>Solicitudes</th><th>Atendidos</th></tr>' : '';
  d.tabla_categoria.forEach(r=>{ tc+=`<tr><td>${r.categoria}</td><td>${r.solicitudes}</td><td>${r.atendidos}</td></tr>`; });
  tc += d.tabla_categoria.length? '</table>' : '<p class="empty">Sin servicios registrados aún</p>';
  $('#tcat').innerHTML = tc;

  // Proveedores
  let pv = d.proveedores.length? '<table><tr><th>Nombre</th><th>Tipo</th><th>Estado</th></tr>' : '';
  d.proveedores.slice(0,8).forEach(p=>{ let b; if(p.estado==='APROBADO'){b='<span class="badge bo">Activo</span>';} else if(p.estado==='EN_VALIDACION'){b='<span class="badge bv">En validación</span>';} else if(p.estado==='RECHAZADO'){b='<span class="badge bp">Rechazado</span>';} else {b='<span class="badge bp">Por validar</span>';}
    pv+=`<tr><td>${p.nombre||'—'}</td><td>${(p.tipo||'').split('(')[0].trim()}</td><td>${b}</td></tr>`; });
  pv += d.proveedores.length? '</table>' : '<p class="empty">Sin registros aún</p>';
  $('#prov').innerHTML = pv;

  // Conductores
  let cd='<table><tr><th>Conductor</th><th>Placa</th><th>Estado</th></tr>';
  d.conductores.forEach(c=>{ let e=c.en_viaje?'<span class="badge bv">En viaje</span>':(c.activo?'<span class="badge bo">Activo</span>':'<span class="badge" style="background:#eef0f4;color:#9a9db0">Pausado</span>');
    cd+=`<tr><td>${c.nombre}</td><td>${c.placa}</td><td>${e}</td></tr>`; });
  cd+='</table>'; $('#cond').innerHTML=cd;

  // Servicios Técnicos (proveedores tipo técnico / especialista)
  const tecs = d.proveedores.filter(p=>/t[eé]cnico|especialista/i.test(p.tipo||''));
  let tt = tecs.length? '<table><tr><th>Nombre</th><th>Oficio</th><th>Estado</th></tr>' : '';
  tecs.forEach(p=>{ let b; if(p.estado==='APROBADO'){b='<span class="badge bo">Activo</span>';} else if(p.estado==='EN_VALIDACION'){b='<span class="badge bv">En validación</span>';} else if(p.estado==='RECHAZADO'){b='<span class="badge bp">Rechazado</span>';} else {b='<span class="badge bp">Por validar</span>';}
    tt+=`<tr><td>${p.nombre||'—'}</td><td>${(p.detalle||p.oficio||'—')}</td><td>${b}</td></tr>`; });
  tt += tecs.length? '</table>' : '<p class="empty">Aún sin técnicos registrados. Invítalos a unirse 🦅</p>';
  $('#tec').innerHTML = tt;

  // Gráficos al final, protegidos (si el CDN de Chart.js no carga, las tablas igual se ven)
  if(typeof Chart==='undefined'){ return; }
  try{
    charts.tend = new Chart($('#cTend'),{type:'line',data:{labels:d.tendencia_7dias.map(x=>x.dia),
      datasets:[{data:d.tendencia_7dias.map(x=>x.total),borderColor:'#5b6cff',backgroundColor:'rgba(91,108,255,.12)',fill:true,tension:.35,pointBackgroundColor:'#5b6cff'}]},
      options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{precision:0}}},maintainAspectRatio:false}});
    const cat=Object.entries(d.servicios_por_categoria);
    charts.cat = new Chart($('#cCat'),{type:'doughnut',data:{labels:cat.map(x=>x[0]),
      datasets:[{data:cat.map(x=>x[1]),backgroundColor:PAL}]},
      options:{plugins:{legend:{position:'right',labels:{boxWidth:12,font:{size:11}}}},cutout:'62%',maintainAspectRatio:false}});
    const est=d.estado_servicios;
    charts.est = new Chart($('#cEst'),{type:'doughnut',data:{labels:['Pendientes','Atendidos'],
      datasets:[{data:[est.solicitado,est.atendido],backgroundColor:['#ff8a3c','#22b07d']}]},
      options:{plugins:{legend:{position:'bottom',labels:{boxWidth:12,font:{size:11}}}},cutout:'62%',maintainAspectRatio:false}});
  }catch(e){ console.error('charts',e); }
}

async function load(){
  try{
    const r=await fetch('/api/dashboard?clave='+encodeURIComponent(clave));
    if(!r.ok){ $('#root').innerHTML='<div class="err">Acceso denegado o error ('+r.status+'). Verifica la clave en la URL.</div>'; return; }
    render(await r.json());
  }catch(e){ $('#root').innerHTML='<div class="err">No se pudo cargar: '+e+'</div>'; }
}
load(); setInterval(load,15000);
</script>
</body>
</html>'''


@app.get("/dashboard")
async def dashboard_page(clave: str = ""):
    from fastapi.responses import HTMLResponse
    if clave != ADMIN_KEY:
        return HTMLResponse('<body style="background:#0a0b10;color:#ff9a9a;font-family:sans-serif;text-align:center;padding:60px"><h2>Acceso denegado</h2><p>Agrega ?clave=TU_CLAVE a la URL.</p></body>', status_code=403)
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/api/dashboard")
async def api_dashboard(clave: str = ""):
    """Datos en vivo para el dashboard. Requiere ?clave=ADMIN_KEY."""
    if clave != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Clave incorrecta")

    # Proveedores (desde disco)
    proveedores = []
    try:
        if os.path.exists(PROVEEDORES_FILE):
            with open(PROVEEDORES_FILE, "r", encoding="utf-8") as f:
                proveedores = json.load(f) or []
    except Exception:
        proveedores = []
    prov_por_tipo = {}
    for p in proveedores:
        t = p.get("tipo", "Otro")
        prov_por_tipo[t] = prov_por_tipo.get(t, 0) + 1

    # Conductores — estado REAL desde Google Sheets (misma fuente que el reparto y tu hoja de control)
    activos_sheet = set()
    sheet_ok = bool(os.getenv("SHEETS_WEBHOOK_URL", "").strip())
    if sheet_ok:
        try:
            for c in (await obtener_conductores_activos_desde_sheets()):
                tel = str(c.get("telefono", "")).strip().replace("+", "")
                if tel and not tel.startswith("51"):
                    tel = "51" + tel
                if tel:
                    activos_sheet.add(tel)
        except Exception as e:
            print(f"[DASHBOARD] no se pudo leer conductores de Sheets: {e}", flush=True)
            sheet_ok = False

    conductores = []
    activos = 0
    for num, info in CONDUCTORES.items():
        estado_act = (num in activos_sheet) if sheet_ok else conductores_estado.get(num, False)
        if estado_act:
            activos += 1
        conductores.append({
            "nombre": info.get("nombre", ""),
            "placa": info.get("placa", ""),
            "telefono": num,
            "activo": bool(estado_act),
            "en_viaje": num in viajes_activos,
        })

    # Profesores
    profesores = [{
        "nombre": info.get("nombre", ""),
        "niveles": info.get("niveles", []),
        "modalidad": info.get("modalidad", []),
        "telefono": num,
    } for num, info in PROFESORES.items()]

    # Tickets
    tk_nuevos = sum(1 for t in tickets if t.get("estado") == "nuevo")
    tk_proceso = sum(1 for t in tickets if t.get("estado") == "en_proceso")
    tk_resueltos = sum(1 for t in tickets if t.get("estado") == "resuelto")

    # Sesiones activas ahora
    sesiones_activas = sum(1 for s in sesiones.values() if s.get("estado") not in (S_MENU, None))

    # Servicios (desde disco) — analítica para el dashboard integral
    servicios = []
    try:
        if os.path.exists(SERVICIOS_FILE):
            with open(SERVICIOS_FILE, "r", encoding="utf-8") as f:
                servicios = json.load(f) or []
    except Exception:
        servicios = []

    hoy = datetime.now().strftime("%Y-%m-%d")
    serv_total = len(servicios)
    serv_hoy = sum(1 for s in servicios if s.get("dia") == hoy)
    completados = sum(1 for s in servicios if s.get("estado") == "atendido")
    pendientes_serv = sum(1 for s in servicios if s.get("estado") == "solicitado")
    tasa_atencion = round(completados / serv_total * 100, 1) if serv_total else 0.0
    ingresos = round(sum(s.get("monto", 0) or 0 for s in servicios if s.get("estado") == "atendido"), 2)

    # por categoría
    serv_por_categoria = {}
    for s in servicios:
        c = s.get("categoria", "Otro")
        serv_por_categoria[c] = serv_por_categoria.get(c, 0) + 1

    # tendencia últimos 7 días
    tendencia = []
    for i in range(6, -1, -1):
        dia = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        etiqueta = (datetime.now() - timedelta(days=i)).strftime("%d/%m")
        tendencia.append({"dia": etiqueta, "total": sum(1 for s in servicios if s.get("dia") == dia)})

    # tabla por categoría: solicitudes vs atendidos
    tabla_categoria = []
    for c in sorted(serv_por_categoria.keys()):
        sols = serv_por_categoria[c]
        atn = sum(1 for s in servicios if s.get("categoria") == c and s.get("estado") == "atendido")
        tabla_categoria.append({"categoria": c, "solicitudes": sols, "atendidos": atn})

    # ranking de proveedores (por servicios atendidos)
    rank = {}
    for s in servicios:
        if s.get("estado") == "atendido" and s.get("proveedor"):
            rank[s["proveedor"]] = rank.get(s["proveedor"], 0) + 1
    ranking = sorted([{"proveedor": k, "atendidos": v} for k, v in rank.items()],
                     key=lambda x: x["atendidos"], reverse=True)[:5]

    return {
        "kpis": {
            "solicitudes_hoy": serv_hoy,
            "servicios_completados": completados,
            "servicios_total": serv_total,
            "servicios_pendientes": pendientes_serv,
            "tasa_atencion": tasa_atencion,
            "ingresos": ingresos,
            "proveedores_total": len(proveedores),
            "proveedores_pendientes": sum(1 for p in proveedores if p.get("estado") in ("PENDIENTE_VALIDACION", "EN_VALIDACION")),
            "negocios_afiliados": sum(1 for p in proveedores if "gastron" in p.get("tipo", "").lower()),
            "conductores_total": len(CONDUCTORES),
            "conductores_activos": activos,
            "conductores_en_ruta": len(viajes_activos),
            "profesores_total": len(PROFESORES),
            "tickets_total": len(tickets),
            "tickets_nuevos": tk_nuevos,
            "solicitudes_en_curso": len(servicios_pendientes),
            "clases_en_curso": len(clases_pendientes),
            "sesiones_activas": sesiones_activas,
        },
        "servicios_por_categoria": serv_por_categoria,
        "tendencia_7dias": tendencia,
        "estado_servicios": {"solicitado": pendientes_serv, "atendido": completados},
        "tabla_categoria": tabla_categoria,
        "ranking_proveedores": ranking,
        "proveedores_por_tipo": prov_por_tipo,
        "proveedores": list(reversed(proveedores))[:50],
        "conductores": conductores,
        "profesores": profesores,
        "tickets": {
            "nuevos": tk_nuevos, "en_proceso": tk_proceso, "resueltos": tk_resueltos,
            "lista": sorted(tickets, key=lambda x: x.get("timestamp", 0), reverse=True)[:20],
        },
        "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

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


@app.get("/admin/test-solicitud")
async def admin_test_solicitud(clave: str = "", to: str = ""):
    """
    Prueba la plantilla de despacho nueva_solicitud_servicio.
    Uso: /admin/test-solicitud?clave=TU_CLAVE&to=51992995140
    Revisa logs: [TEMPLATE] nueva_solicitud_servicio_v2 enviado = aprobada.
    [TEMPLATE ERROR] status=400 = aún no aprobada / nombre o idioma no coincide.
    """
    if clave != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Clave inválida")
    if not to:
        raise HTTPException(status_code=400, detail="Falta parámetro 'to' (ej. ?to=51992995140)")

    ok = await enviar_template_solicitud(
        to, "TAXI", "Cliente Prueba | +51999999999",
        "Recojo: Plaza de Armas | Destino: Hospital | S/10 | Efectivo", "51999999999"
    )
    return {
        "ok": ok,
        "to": to,
        "nota": "Revisa los logs de Render. [TEMPLATE]=aprobada y enviada. [TEMPLATE ERROR] status=400=falta aprobar en Meta."
    }


@app.get("/cotizacion/{folio}/aprobar")
async def cal_aprobar(folio: str, clave: str = ""):
    from fastapi.responses import HTMLResponse
    if clave != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="No autorizado")
    reg = CAL_APROBACION.get(folio)
    if not reg:
        return HTMLResponse("<h2>Cotización no encontrada o ya expirada.</h2>", status_code=404)
    if reg["estado"] == "APROBADA":
        return HTMLResponse("<h2>✅ Esta cotización ya fue aprobada y enviada al cliente.</h2>")
    await cal_enviar_aprobada_al_cliente(reg)
    return HTMLResponse(
        f"<div style='font-family:Arial;max-width:480px;margin:40px auto;text-align:center'>"
        f"<h2 style='color:#1faa59'>✅ Cotización {folio} aprobada</h2>"
        f"<p>El PDF fue enviado al cliente ({reg['numero']}) por WhatsApp, junto con los datos de pago.</p>"
        f"<p style='color:#999;font-size:13px'>INCAMORE S.A.C</p></div>")


@app.get("/cotizacion/{folio}/corregir")
async def cal_corregir(folio: str, clave: str = "", aplicar: str = "",
                       espesor: str = "", color: str = "", largo: str = "",
                       cantidad: str = "", tipo: str = ""):
    from fastapi.responses import HTMLResponse
    if clave != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="No autorizado")
    reg = CAL_APROBACION.get(folio)
    if not reg:
        return HTMLResponse("<h2>Cotización no encontrada o ya expirada.</h2>", status_code=404)
    d = reg["datos"]

    if aplicar == "1":
        try:
            if espesor in ("0.30", "0.40"): d["espesor"] = espesor
            if color.strip(): d["color"] = color.strip().lower()
            if largo.strip(): d["largo"] = float(largo)
            if cantidad.strip(): d["cantidad"] = int(cantidad)
            if tipo in ("boleta", "factura"): d["tipo"] = tipo
        except Exception as e:
            return HTMLResponse(f"<h2>Dato inválido: {e}</h2>", status_code=400)
        cot = cal_construir_cotizacion(d)
        cot["folio"] = folio  # conservar el folio original
        ruta = cal_generar_pdf(cot)
        reg.update({"datos": dict(d), "cot": cot, "ruta": ruta})
        await cal_enviar_aprobada_al_cliente(reg)
        return HTMLResponse(
            f"<div style='font-family:Arial;max-width:480px;margin:40px auto;text-align:center'>"
            f"<h2 style='color:#1faa59'>✅ Cotización {folio} corregida y enviada</h2>"
            f"<p>El PDF corregido fue enviado al cliente ({reg['numero']}).</p></div>")

    val = lambda x: x if x is not None else ""
    sel = lambda a, b: "selected" if a == b else ""
    accs = ", ".join(f"{k}:{v}" for k, v in d.get("accesorios", {}).items()) or "—"
    return HTMLResponse(f"""
    <div style="font-family:Arial;max-width:520px;margin:30px auto;color:#222">
      <h2 style="color:#A6452F">✏️ Corregir cotización {folio}</h2>
      <p style="color:#666">Cliente: {reg['cot']['cliente']} ({reg['numero']}) · Accesorios: {accs}</p>
      <form method="get" action="/cotizacion/{folio}/corregir">
        <input type="hidden" name="clave" value="{ADMIN_KEY}">
        <input type="hidden" name="aplicar" value="1">
        <p>Comprobante:
          <select name="tipo">
            <option value="boleta" {sel('boleta', d.get('tipo'))}>Boleta</option>
            <option value="factura" {sel('factura', d.get('tipo'))}>Factura</option>
          </select></p>
        <p>Espesor:
          <select name="espesor">
            <option value="0.30" {sel('0.30', d.get('espesor'))}>0.30 mm</option>
            <option value="0.40" {sel('0.40', d.get('espesor'))}>0.40 mm</option>
          </select></p>
        <p>Color: <input name="color" value="{val(d.get('color'))}"></p>
        <p>Largo (m): <input name="largo" value="{val(d.get('largo'))}"></p>
        <p>Cantidad: <input name="cantidad" value="{val(d.get('cantidad'))}"></p>
        <button type="submit" style="background:#1faa59;color:#fff;border:0;padding:12px 22px;
          border-radius:8px;font-weight:bold;cursor:pointer">Guardar y enviar al cliente</button>
      </form>
      <p style="color:#999;font-size:12px;margin-top:18px">INCAMORE S.A.C — los accesorios se ajustan desde el chat.</p>
    </div>""")


@app.get("/cotizacion/{folio}")
async def servir_cotizacion(folio: str):
    from fastapi.responses import FileResponse
    import re as _re
    if not _re.fullmatch(r"[A-Za-z0-9\-]+", folio or ""):
        raise HTTPException(status_code=400, detail="folio inválido")
    ruta = os.path.join(DATA_DIR, "cotizaciones", f"{folio}.pdf")
    if not os.path.isfile(ruta):
        raise HTTPException(status_code=404, detail="cotización no encontrada")
    return FileResponse(ruta, media_type="application/pdf", filename=f"{folio}.pdf")


@app.get("/")
async def root():
    return {"status": "El Cuervo Bot v1.0 activo 🦅 — red de servicios locales en Barranca"}
