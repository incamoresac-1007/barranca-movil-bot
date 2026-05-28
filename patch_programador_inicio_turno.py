from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
text = BOT.read_text(encoding="utf-8")

backup = Path(f"bot_backup_programador_inicio_turno_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)

programador = r'''

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
    Programador diario:
    - 07:00 a 07:10 Lima: envía plantilla de inicio de turno.
    - 08:00 a 08:10 Lima: alerta si no hay conductores activos.
    Ejecuta una sola vez por día cada acción.
    """
    try:
        from zoneinfo import ZoneInfo
        tz_lima = ZoneInfo("America/Lima")
    except Exception:
        tz_lima = None

    enviados_recordatorio = set()
    alertas_0800 = set()

    print("[BOT] Programador inicio turno iniciado - 07:00 Lima / alerta 08:00 Lima", flush=True)

    while True:
        try:
            ahora = datetime.now(tz_lima) if tz_lima else datetime.now()
            dia = ahora.strftime("%Y-%m-%d")

            if ahora.hour == 7 and 0 <= ahora.minute <= 10 and dia not in enviados_recordatorio:
                enviados_recordatorio.add(dia)
                await enviar_recordatorio_inicio_turno_masivo()

            if ahora.hour == 8 and 0 <= ahora.minute <= 10 and dia not in alertas_0800:
                alertas_0800.add(dia)
                await verificar_activos_y_alertar_operador()

        except Exception as e:
            print(f"[BOT ERROR] programador_inicio_turno_conductores: {e}", flush=True)

        await asyncio.sleep(60)

'''

if "async def programador_inicio_turno_conductores" not in text:
    marker = "async def buscar_lugares_peru"
    pos = text.find(marker)
    if pos == -1:
        raise SystemExit("ERROR: No encontré async def buscar_lugares_peru para insertar programador.")
    text = text[:pos] + programador + "\n" + text[pos:]
else:
    print("AVISO: programador_inicio_turno_conductores ya existe. No se insertó otra vez.")

# Insertar arranque del programador en startup, después del limpiador de sesiones.
startup_call = "asyncio.create_task(programador_inicio_turno_conductores())"
startup_print = 'print("[BOT] Programador inicio turno activo - 07:00 Lima / alerta 08:00 Lima", flush=True)'

if startup_call not in text:
    lines = text.splitlines()
    inserted = False
    new_lines = []

    for line in lines:
        new_lines.append(line)

        if "Limpiador de sesiones iniciado" in line:
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(indent + startup_call)
            new_lines.append(indent + startup_print)
            inserted = True

    if not inserted:
        raise SystemExit("ERROR: No encontré la línea 'Limpiador de sesiones iniciado' para enganchar el programador.")

    text = "\n".join(new_lines) + "\n"
else:
    print("AVISO: el startup del programador ya estaba agregado.")

BOT.write_text(text, encoding="utf-8")

try:
    py_compile.compile(str(BOT), doraise=True)
    print(f"OK: bot.py compila. Backup creado: {backup}")
except Exception as e:
    shutil.copy2(backup, BOT)
    raise SystemExit(f"ERROR: bot.py no compila. Restaurado backup. {e}")

updated = BOT.read_text(encoding="utf-8")
for term in [
    "programador_inicio_turno_conductores",
    "enviar_recordatorio_inicio_turno_masivo",
    "verificar_activos_y_alertar_operador",
    "inicio_turno_conductor",
    "Programador inicio turno activo"
]:
    print(f"{term}: {'OK' if term in updated else 'NO'}")
