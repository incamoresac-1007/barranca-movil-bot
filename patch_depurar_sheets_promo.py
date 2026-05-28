from pathlib import Path
import py_compile
import shutil
from datetime import datetime
import re

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_depurar_sheets_promo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Limpiar posible promo duplicada visible en bienvenida.
# Dejar solo: primer servicio urbano gratis hasta S/7.
text = text.replace(
    "🎉 Promo: *primer viaje urbano gratis* para usuarios nuevos.\\n"
    "Escribe *promo* para validar disponibilidad.\\n\\n",
    ""
)

text = text.replace(
    "🎉 Promo: *primer viaje urbano gratis* para usuarios nuevos.\n"
    "Escribe *promo* para validar disponibilidad.\n\n",
    ""
)

# Si por algún parche anterior quedaron dos promos juntas, colapsar a una sola.
patron_doble_promo = re.compile(
    r"🎉 Promo: \*primer viaje urbano gratis\* para usuarios nuevos\.(?:\\\\n|\\n|\n)"
    r"Escribe \*promo\* para validar disponibilidad\.(?:\\\\n|\\n|\n){2}"
    r"🎉 Promo: \*primer servicio urbano gratis hasta S/7\*\.(?:\\\\n|\\n|\n)"
    r"Escribe \*promo\* para validar disponibilidad\.",
    re.MULTILINE
)

text = patron_doble_promo.sub(
    "🎉 Promo: *primer servicio urbano gratis hasta S/7*.\\n"
    "Escribe *promo* para validar disponibilidad.",
    text
)

# 2) Mantener la frase antigua solo como palabra clave de entrada.
# No eliminar "primer viaje urbano gratis" de es_comando_promo porque sirve para usuarios que vieron la publicación anterior.

# 3) Depurar comentario viejo de colectivo.
text = text.replace(
    "COLECTIVO_RECOJO_EXTRA = 1.00  # +S/1 por recojo a domicilio (puerta a puerta siempre)",
    "COLECTIVO_RECOJO_EXTRA = 1.00  # +S/1 por solicitud de recojo a domicilio"
)

# 4) Reemplazar registrar_turismo_sheets por un adaptador al motor general sheets_evento().
# Así eliminamos duplicidad de llamadas directas a SHEETS_WEBHOOK_URL.
start = text.find("async def registrar_turismo_sheets")
if start == -1:
    raise SystemExit("ERROR: No encontré registrar_turismo_sheets")

end = text.find("# ── Google Maps", start)
if end == -1:
    raise SystemExit("ERROR: No encontré marcador Google Maps después de registrar_turismo_sheets")

new_func = '''async def registrar_turismo_sheets(datos_turismo: dict):
    """Compatibilidad: registra turismo usando el motor general sheets_evento()."""
    try:
        if not datos_turismo:
            return

        telefono = str(datos_turismo.get("telefono") or datos_turismo.get("pasajero_telefono") or "")
        if not datos_turismo.get("id_servicio"):
            datos_turismo["id_servicio"] = generar_id_servicio(telefono or "TUR", "TURISMO")

        pasajeros_extra = datos_turismo.get("turismo_pasajeros_extra", "")
        dni_principal = datos_turismo.get("turismo_dni_principal", "")

        data = {
            "id_servicio": datos_turismo.get("id_servicio"),
            "destino_turistico": datos_turismo.get("ruta_nombre") or datos_turismo.get("destino_turistico") or "",
            "modalidad": datos_turismo.get("modalidad", ""),
            "fecha_tour": datos_turismo.get("fecha", ""),
            "hora_recojo": datos_turismo.get("hora_recojo", ""),
            "cantidad_personas": datos_turismo.get("personas", ""),
            "tipo_grupo": datos_turismo.get("tipo_grupo", ""),
            "pasajeros_resumen": pasajeros_extra,
            "dni_completo": "SI" if dni_principal else "PENDIENTE",
            "precio_referencial": datos_turismo.get("ruta_precio_ref") or datos_turismo.get("precio_ref") or "",
            "nota_ruta": datos_turismo.get("nota_ruta", ""),
            "conductor": datos_turismo.get("conductor_nombre", ""),
            "placa": datos_turismo.get("conductor_placa", ""),
            "estado": datos_turismo.get("estado_sheets", "PENDIENTE_CONDUCTOR"),
            "observacion": datos_turismo.get("observacion_sheets", ""),
        }

        await sheets_evento("upsert_turismo", data)

    except Exception as e:
        print(f"[SHEETS TURISMO ERROR] {e}", flush=True)


'''

text = text[:start] + new_func + "\n" + text[end:]

# 5) Evitar varias líneas promo visibles si quedó repetida por accidente.
linea_promo = "🎉 Promo: *primer servicio urbano gratis hasta S/7*."
if text.count(linea_promo) > 1:
    primera = True
    nuevas = []
    for line in text.splitlines():
        if linea_promo in line:
            if primera:
                nuevas.append(line)
                primera = False
            else:
                continue
        else:
            nuevas.append(line)
    text = "\\n".join(nuevas) + "\\n"

if text == original:
    print("AVISO: No se aplicaron cambios nuevos.")
else:
    BOT.write_text(text, encoding="utf-8")
    print(f"OK: bot.py depurado. Backup creado: {backup}")

try:
    py_compile.compile(str(BOT), doraise=True)
    print("OK: bot.py compila correctamente.")
except Exception as e:
    shutil.copy2(backup, BOT)
    raise SystemExit(f"ERROR: bot.py no compila. Restaurado backup. {e}")

updated = BOT.read_text(encoding="utf-8")

print("Chequeo:")
print("promo visible nueva:", updated.count("primer servicio urbano gratis hasta S/7"))
print("promo vieja visible:", "primer viaje urbano gratis para usuarios nuevos" in updated)
print("keyword vieja conservada:", "primer viaje urbano gratis" in updated)
print("turismo usa sheets_evento:", "await sheets_evento(\"upsert_turismo\"" in updated)
print("webhook directo turismo viejo:", "Registro turismo:" in updated)
print("comentario puerta a puerta:", "puerta a puerta siempre" in updated)
