from pathlib import Path
import py_compile
import shutil
from datetime import datetime
import re

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_tarifa_minima_programado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Agregar configuración y función de tarifa mínima programada
if "TARIFA_MINIMA_TAXI_PROGRAMADO" not in text:
    marker = "COLECTIVO_MAX_ASIENTOS = 4"
    helper = r'''
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
        datos["tarifa_aviso"] = (
            f"📌 Tarifa mínima por servicio programado: S/{TARIFA_MINIMA_TAXI_PROGRAMADO:.2f}\n"
        )
        datos["observacion_tarifa"] = "Tarifa mínima por servicio programado"

'''
    if marker not in text:
        raise SystemExit("ERROR: No encontré COLECTIVO_MAX_ASIENTOS = 4")
    text = text.replace(marker, marker + "\n" + helper, 1)

# 2) Cada vez que se asigne datos["tarifa"], aplicar la regla
pattern = re.compile(r'(?m)^(\s*)datos\[(["\'])tarifa\2\]\s*=\s*(.+)$')
matches = list(pattern.finditer(text))

if not matches:
    raise SystemExit("ERROR: No encontré asignaciones a datos['tarifa'] o datos[\"tarifa\"]")

def repl(m):
    indent = m.group(1)
    line = m.group(0)
    # Evitar duplicar si ya se agregó justo después
    after = text[m.end():m.end()+120]
    if "aplicar_tarifa_minima_programada(datos)" in after.splitlines()[0:2]:
        return line
    return line + "\n" + indent + "aplicar_tarifa_minima_programada(datos)"

text = pattern.sub(repl, text)

# 3) Mostrar aviso en confirmación de taxi si existe tarifa_aviso
text = text.replace(
    "f\"🏁 {datos['destino_texto']}\\n💰 S/{datos['tarifa']}\\n💳 {datos['pago']}\\n\\n\"",
    "f\"🏁 {datos['destino_texto']}\\n💰 S/{datos['tarifa']}\\n\""
    "f\"{datos.get('tarifa_aviso','')}\""
    "f\"💳 {datos['pago']}\\n\\n\""
)

text = text.replace(
    'f"🏁 {datos[\'destino_texto\']}\\n💰 S/{datos[\'tarifa\']}\\n💳 {datos[\'pago\']}\\n\\n"',
    'f"🏁 {datos[\'destino_texto\']}\\n💰 S/{datos[\'tarifa\']}\\n"'
    'f"{datos.get(\'tarifa_aviso\',\'\')}"'
    'f"💳 {datos[\'pago\']}\\n\\n"'
)

if text == original:
    print("AVISO: No se aplicaron cambios.")
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
    "TARIFA_MINIMA_TAXI_PROGRAMADO",
    "aplicar_tarifa_minima_programada",
    "Tarifa mínima por servicio programado"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
