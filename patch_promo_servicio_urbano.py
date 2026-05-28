from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_promo_servicio_urbano_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Ampliar palabras clave de promo
start_fn = text.find("def es_comando_promo")
start_msg = text.find("MSG_PROMO_LANZAMIENTO", start_fn)

if start_fn == -1 or start_msg == -1:
    raise SystemExit("ERROR: No encontré función/mensaje de promo")

new_fn = '''def es_comando_promo(texto: str) -> bool:
    t = _normalizar_geo(texto or "")
    claves = [
        "promo", "promocion", "promoción",
        "servicio gratis", "primer servicio gratis",
        "primer servicio urbano gratis",
        "viaje gratis", "primer viaje gratis",
        "primer viaje urbano gratis",
        "envio gratis", "envío gratis",
        "encomienda gratis",
        "colectivo gratis", "cupo gratis",
        "gratis", "descuento",
        "facebook", "face", "fb",
        "publicacion", "publicación",
        "anuncio", "lanzamiento",
        "vi la publicacion", "vi la publicación",
        "quiero mi viaje gratis",
        "quiero mi servicio gratis"
    ]
    return any(c in t for c in claves)


'''
text = text[:start_fn] + new_fn + text[start_msg:]

# 2) Reemplazar mensaje de promo por versión nueva: servicio urbano hasta S/7
start = text.find("MSG_PROMO_LANZAMIENTO = (")
if start == -1:
    raise SystemExit("ERROR: No encontré MSG_PROMO_LANZAMIENTO")

end = text.find("\n)\n", start)
if end == -1:
    raise SystemExit("ERROR: No encontré cierre de MSG_PROMO_LANZAMIENTO")
end = end + len("\n)\n")

new_msg = '''MSG_PROMO_LANZAMIENTO = (
    "🎉 *¡Promo de lanzamiento Barranca Móvil!* 🚖📦🚌\\n\\n"
    "🎁 *Tu primer servicio urbano puede ser GRATIS*\\n"
    "✅ Valor máximo promocional: *S/7*\\n"
    "🎟️ Solo para los *10 primeros usuarios nuevos*\\n\\n"
    "📌 *Puedes usarlo en:*\\n"
    "🚖 Taxi urbano dentro de Barranca\\n"
    "🚌 Primer cupo en colectivo compartido\\n"
    "📦 Encomienda urbana pequeña\\n\\n"
    "📍 Para verificar disponibilidad, envíanos tu *nombre* y tu *zona de recojo*.\\n"
    "_Ejemplo: Ana Torres - Urb. Los Jardines_\\n\\n"
    "⚠️ *Importante:*\\n"
    "• Aplica solo dentro de la zona urbana de Barranca.\\n"
    "• No aplica para Lima, Huacho, turismo, viajes largos ni anexos lejanos.\\n"
    "• No aplica para cargas pesadas, cargas riesgosas ni encomiendas grandes.\\n"
    "• Sujeto a cupos promocionales y disponibilidad de conductor.\\n\\n"
    "¿Qué deseas hacer?\\n\\n"
    "1️⃣ Solicitar taxi urbano\\n"
    "2️⃣ Colectivo compartido con recojo a domicilio\\n"
    "3️⃣ Enviar encomienda urbana\\n"
    "0️⃣ Salir"
)
'''

text = text[:start] + new_msg + text[end:]

# 3) Actualizar bienvenida: línea breve de promo
old_options = [
    '🎉 Promo: *primer viaje urbano gratis* para usuarios nuevos.\\nEscribe *promo* para validar disponibilidad.',
    '🎉 Promo: *primer viaje urbano gratis* para usuarios nuevos.\\nEscribe *promo* para validar disponibilidad.\\n',
    '🎉 Promo: *primer servicio urbano gratis* para usuarios nuevos.\\nEscribe *promo* para validar disponibilidad.',
]

for old in old_options:
    text = text.replace(old, '🎉 Promo: *primer servicio urbano gratis hasta S/7*.\\nEscribe *promo* para validar disponibilidad.')

# Si no existe línea de promo en bienvenida, insertarla antes de "O escribe tu consulta"
if "primer servicio urbano gratis hasta S/7" not in text:
    text = text.replace(
        "O escribe tu consulta libremente 💬",
        "🎉 Promo: *primer servicio urbano gratis hasta S/7*.\\n"
        "Escribe *promo* para validar disponibilidad.\\n\\n"
        "O escribe tu consulta libremente 💬",
        1
    )

# 4) Actualizar descripción registrada en Google Sheets ALERTAS
text = text.replace(
    "consultó la promoción de primer viaje urbano gratis. Validar si aún hay cupo disponible.",
    "consultó la promoción de primer servicio urbano gratis hasta S/7. Validar si aún hay cupo disponible."
)

text = text.replace(
    "PROMO_PRIMER_VIAJE_URBANO",
    "PROMO_PRIMER_SERVICIO_URBANO"
)

# 5) Hacer que opción 3 de promo vaya a encomienda si el usuario responde 3 desde S_MENU
# Como S_MENU ya usa 3 para ENCOMIENDA, no hay que agregar lógica nueva.

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
    "primer servicio urbano gratis",
    "Valor máximo promocional",
    "Encomienda urbana pequeña",
    "PROMO_PRIMER_SERVICIO_URBANO",
    "servicio gratis"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
