from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_reserva_60min_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)

start = text.find("def aplicar_tarifa_minima_programada(")
if start == -1:
    raise SystemExit("ERROR: No encontré aplicar_tarifa_minima_programada")

end = text.find("\ndef ", start + 1)
if end == -1:
    raise SystemExit("ERROR: No pude encontrar el final de aplicar_tarifa_minima_programada")

new_block = r'''
def minutos_hasta_reserva_programada(texto_fecha: str):
    """
    Intenta calcular cuántos minutos faltan para una reserva escrita como:
    - hoy 4 .00 pm
    - hoy 4:00 pm
    - mañana 8 am
    - manana 8:30 am

    Si no puede entender la hora, devuelve None.
    """
    try:
        import re
        from datetime import datetime, timedelta

        txt = (texto_fecha or "").lower().strip()
        if not txt:
            return None

        txt = txt.replace("mañana", "manana")
        txt = re.sub(r"(\d{1,2})\s*[\.:]\s*(\d{2})", r"\1:\2", txt)

        m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", txt)
        if not m:
            return None

        hora = int(m.group(1))
        minuto = int(m.group(2) or 0)
        ampm = m.group(3)

        if ampm == "pm" and hora < 12:
            hora += 12
        elif ampm == "am" and hora == 12:
            hora = 0

        ahora = datetime.now()
        fecha = ahora.date()

        if "manana" in txt:
            fecha = fecha + timedelta(days=1)

        reserva = datetime.combine(fecha, datetime.min.time()).replace(hour=hora, minute=minuto)

        # Si dijo "hoy" y la hora ya pasó, no aplicar recargo.
        if reserva < ahora:
            return 0

        return int((reserva - ahora).total_seconds() // 60)

    except Exception:
        return None


def aplicar_tarifa_minima_programada(datos: dict):
    """
    Taxi programado:
    - Si falta 60 minutos o más: mínimo S/6.
    - Si falta menos de 60 minutos: tarifa normal.
    - Si no se puede interpretar la hora: tarifa normal.
    """
    if not isinstance(datos, dict):
        return

    servicio = str(datos.get("servicio", "") or datos.get("tipo_servicio", "")).upper()
    if servicio and servicio != "TAXI":
        return

    fecha_programada = (
        datos.get("fecha_programada")
        or datos.get("hora_programada")
        or datos.get("horario")
        or ""
    )

    minutos = minutos_hasta_reserva_programada(fecha_programada)

    # Regla comercial: solo recargo si es 60 min o más.
    if minutos is None or minutos < 60:
        datos.pop("tarifa_aviso", None)
        datos.pop("observacion_tarifa", None)
        return

    try:
        tarifa = float(datos.get("tarifa") or 0)
    except Exception:
        return

    if 0 < tarifa < TARIFA_MINIMA_TAXI_PROGRAMADO:
        diferencia = TARIFA_MINIMA_TAXI_PROGRAMADO - tarifa
        datos["tarifa_original"] = tarifa
        datos["tarifa"] = TARIFA_MINIMA_TAXI_PROGRAMADO
        datos["tarifa_aviso"] = (
            f"📌 Reserva con anticipación: tarifa base S/{tarifa:.2f} "
            f"+ S/{diferencia:.2f} por reserva programada = S/{TARIFA_MINIMA_TAXI_PROGRAMADO:.2f}\n"
        )
        datos["observacion_tarifa"] = "Tarifa mínima por reserva programada de 60 minutos o más"

'''

text = text[:start] + new_block + text[end:]

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
    "minutos_hasta_reserva_programada",
    "minutos < 60",
    "Reserva con anticipación",
    "60 minutos o más"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
