from pathlib import Path
import py_compile
import shutil
from datetime import datetime
import re

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_fix_promo_visual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Limpiar cualquier bloque de promo viejo dentro del mensaje de bienvenida
# Dejamos una sola línea corta y decente.
text = re.sub(
    r"\n*🎉 Promo: \*primer viaje urbano gratis\* para usuarios nuevos\.\n"
    r"Escribe \*promo\* para validar disponibilidad\.\n*",
    "\n",
    text
)

text = re.sub(
    r"\n*🎉 Promo: \*primer servicio urbano gratis hasta S/7\*\.\n"
    r"Escribe \*promo\* para validar disponibilidad\.\n*",
    "\n",
    text
)

# Insertar solo una línea corta antes de "O escribe tu consulta libremente"
linea_limpia = (
    "🎁 Promo de lanzamiento: *primer servicio urbano gratis hasta S/7*.\\n"
    "Escribe *promo* para ver condiciones.\\n\\n"
)

if "🎁 Promo de lanzamiento: *primer servicio urbano gratis hasta S/7*." not in text:
    text = text.replace(
        "O escribe tu consulta libremente 💬",
        linea_limpia + "O escribe tu consulta libremente 💬",
        1
    )

# 2) Reemplazar mensaje completo de promo por uno más bonito y corto
start = text.find("MSG_PROMO_LANZAMIENTO = (")
if start == -1:
    raise SystemExit("ERROR: No encontré MSG_PROMO_LANZAMIENTO")

end = text.find("\n)\n", start)
if end == -1:
    raise SystemExit("ERROR: No encontré cierre de MSG_PROMO_LANZAMIENTO")
end = end + len("\n)\n")

nuevo_msg = '''MSG_PROMO_LANZAMIENTO = (
    "🎉 *Promo de lanzamiento Barranca Móvil*\\n\\n"
    "🎁 *Tu primer servicio urbano puede ser GRATIS*\\n"
    "💰 Valor máximo promocional: *S/7*\\n"
    "🎟️ Solo para los *10 primeros usuarios nuevos*\\n\\n"
    "✅ *Aplica para:*\\n"
    "🚖 Taxi urbano dentro de Barranca\\n"
    "🚌 Primer cupo en colectivo compartido\\n"
    "📦 Encomienda urbana pequeña\\n\\n"
    "⚠️ *No aplica para:*\\n"
    "Lima, Huacho, turismo, viajes largos, anexos lejanos, cargas pesadas o riesgosas.\\n\\n"
    "📍 Para validar disponibilidad, escribe tu *nombre* y tu *zona de recojo*.\\n"
    "_Ejemplo: Ana Torres - Urb. Los Jardines_\\n\\n"
    "1️⃣ Solicitar taxi urbano\\n"
    "2️⃣ Colectivo compartido\\n"
    "3️⃣ Encomienda urbana\\n"
    "0️⃣ Salir"
)
'''

text = text[:start] + nuevo_msg + text[end:]

# 3) Asegurar que en S_MENU la promo responda antes de evaluar 1,2,3,4
# Si ya existe el bloque, no duplicar.
bloque_actual = '''        if es_comando_promo(texto):
            datos["origen_promo"] = "PROMO_PRIMER_SERVICIO_URBANO"'''

if bloque_actual not in text:
    marcador = '''    elif estado == S_MENU:
        if texto == "1":'''
    reemplazo = '''    elif estado == S_MENU:
        if es_comando_promo(texto):
            datos["origen_promo"] = "PROMO_PRIMER_SERVICIO_URBANO"
            await enviar_mensaje(numero, MSG_PROMO_LANZAMIENTO)
            return

        if texto == "1":'''
    if marcador not in text:
        raise SystemExit("ERROR: No encontré inicio limpio de S_MENU")
    text = text.replace(marcador, reemplazo, 1)

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
print("Linea promo corta:", "OK" if "Promo de lanzamiento: *primer servicio urbano gratis hasta S/7*" in updated else "NO")
print("Mensaje promo:", "OK" if "Promo de lanzamiento Barranca Móvil" in updated else "NO")
print("Duplicado viaje urbano:", "MAL" if "primer viaje urbano gratis para usuarios nuevos" in updated else "OK eliminado")
