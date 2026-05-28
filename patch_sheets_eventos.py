from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_sheets_eventos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Insertar motor general de eventos Sheets
if "async def sheets_evento" not in text:
    marker = "# ── Google Maps"
    helper = r'''

def generar_id_servicio(numero_cliente: str, tipo: str) -> str:
    sufijo = str(numero_cliente)[-4:]
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    prefijo = (tipo or "SRV")[:3].upper()
    return f"BM-{prefijo}-{sufijo}-{ts}"


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
            r = await client.post(webhook_url, json=payload)
            print(f"[SHEETS] {action}: {r.status_code} {r.text[:120]}", flush=True)
    except Exception as e:
        print(f"[SHEETS ERROR] {action}: {e}", flush=True)

'''
    if marker not in text:
        raise SystemExit("ERROR: No encontré marcador Google Maps para insertar sheets_evento")
    text = text.replace(marker, helper + "\n" + marker, 1)

# 2) Asegurar ID de servicio al iniciar notificación a conductores
old = '''    d = sesion["datos"]
'''
new = '''    d = sesion["datos"]
    if not d.get("id_servicio"):
        d["id_servicio"] = generar_id_servicio(numero_cliente, tipo)
    d["hora_confirmacion"] = datetime.now().strftime("%H:%M")
'''
if old not in text:
    raise SystemExit("ERROR: No encontré d = sesion[datos] en notificar_conductores")
text = text.replace(old, new, 1)

# 3) Registrar PENDIENTE_CONDUCTOR luego de enviar a conductores
old = '''    await asyncio.gather(*tareas)

    # Timeout 90s: si nadie acepta, avisar al cliente
'''
new = '''    await asyncio.gather(*tareas)

    asyncio.create_task(sheets_evento(
        "upsert_servicio",
        armar_sheets_servicio(numero_cliente, tipo, d, "PENDIENTE_CONDUCTOR")
    ))

    # Timeout 90s: si nadie acepta, avisar al cliente
'''
if old not in text:
    raise SystemExit("ERROR: No encontré bloque await asyncio.gather")
text = text.replace(old, new, 1)

# 4) Registrar SIN_CONDUCTOR en timeout
old = '''        if numero_cliente in servicios_pendientes:
            servicios_pendientes.pop(numero_cliente, None)
            await enviar_mensaje(numero_cliente,
'''
new = '''        if numero_cliente in servicios_pendientes:
            servicio_timeout = servicios_pendientes.get(numero_cliente, {})
            datos_timeout = servicio_timeout.get("datos", {})
            tipo_timeout = servicio_timeout.get("tipo", tipo)

            await sheets_evento(
                "upsert_servicio",
                armar_sheets_servicio(numero_cliente, tipo_timeout, datos_timeout, "SIN_CONDUCTOR")
            )

            servicios_pendientes.pop(numero_cliente, None)
            await enviar_mensaje(numero_cliente,
'''
if old not in text:
    raise SystemExit("ERROR: No encontré bloque timeout sin conductor")
text = text.replace(old, new, 1)

# 5) Registrar ASIGNADO cuando conductor acepta.
old = '''            tipo_servicio = servicio.get("tipo", "TAXI")

            # Avisar a los demás conductores
'''
new = '''            tipo_servicio = servicio.get("tipo", "TAXI")

            asyncio.create_task(sheets_evento(
                "upsert_servicio",
                armar_sheets_servicio(numero_cliente_full, tipo_servicio, servicio["datos"], "ASIGNADO", conductor)
            ))

            # Avisar a los demás conductores
'''
if old not in text:
    raise SystemExit("ERROR: No encontré bloque tipo_servicio aceptación explícita")
text = text.replace(old, new, 1)

# 6) Registrar ASIGNADO cuando conductor acepta automáticamente el único pendiente.
old = '''                tipo_servicio = servicio.get("tipo", "TAXI")

                for num_cond in CONDUCTORES.keys():
'''
new = '''                tipo_servicio = servicio.get("tipo", "TAXI")

                asyncio.create_task(sheets_evento(
                    "upsert_servicio",
                    armar_sheets_servicio(numero_cliente_full, tipo_servicio, servicio["datos"], "ASIGNADO", conductor)
                ))

                for num_cond in CONDUCTORES.keys():
'''
if old not in text:
    raise SystemExit("ERROR: No encontré bloque tipo_servicio aceptación automática")
text = text.replace(old, new, 1)

if text == original:
    print("AVISO: No se aplicaron cambios nuevos.")
else:
    BOT.write_text(text, encoding="utf-8")
    print(f"OK: bot.py actualizado. Backup creado: {backup}")

try:
    py_compile.compile(str(BOT), doraise=True)
    print("OK: bot.py compila correctamente.")
except Exception as e:
    shutil.copy2(backup, BOT)
    raise SystemExit(f"ERROR: bot.py no compila. Restaurado backup. {e}")

updated = BOT.read_text(encoding="utf-8")
for term in [
    "async def sheets_evento",
    "armar_sheets_servicio",
    "PENDIENTE_CONDUCTOR",
    "SIN_CONDUCTOR",
    "ASIGNADO",
    "generar_id_servicio"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
