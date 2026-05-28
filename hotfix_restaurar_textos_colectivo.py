from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_restore_textos_colectivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Menú principal: cambiar nombre engañoso
text = text.replace(
    "2️⃣ Colectivo puerta a puerta 🚌",
    "2️⃣ Colectivo compartido con recojo a domicilio 🚌"
)

# 2) Insertar promo simple en bienvenida, sin lógica extra
promo_line = (
    "🎁 Promo de lanzamiento: *primer servicio urbano gratis hasta S/7*.\\n"
    "Escribe *promo* para consultar condiciones.\\n\\n"
)

if "primer servicio urbano gratis hasta S/7" not in text:
    text = text.replace(
        "O escribe tu consulta libremente 💬",
        promo_line + "O escribe tu consulta libremente 💬",
        1
    )

# 3) Si la IA responde promo, al menos que no quede muda: usar consulta libre normal.
# No agregamos MSG_PROMO ni lógica nueva para no romper producción.

# 4) Tarifas / ayuda: reemplazos seguros
text = text.replace(
    "🚌 *Colectivo Puerta a Puerta:*",
    "🚌 *Colectivo compartido con recojo a domicilio:*"
)

text = text.replace(
    "✅ *Precio incluye recojo en tu domicilio*",
    "✅ *Incluye solicitud de recojo a domicilio*"
)

text = text.replace(
    "_(2+ asientos: descuento en recojo S/0.50 c/u)_",
    "_Salida sujeta a cupos disponibles o confirmación del conductor._"
)

# 5) Inicio del flujo colectivo después del nombre
text = text.replace(
    "f\"_(Precios por pasajero, incluye recojo en tu domicilio)_\")",
    "f\"_(Precio por pasajero. Recojo a domicilio sujeto a cupos disponibles o confirmación del conductor)_\" + NAV)"
)

# 6) Si elige ruta, aclarar cupos y dar salida
old_ruta = '''        await enviar_mensaje(numero,
            f"{ruta['emoji']} *{ruta['nombre']}* — S/{ruta['tarifa']:.2f} por pasajero\\n\\n"
            f"🕐 *¿Cuándo necesitas el colectivo?*\\n\\n"
            f"1️⃣ Ahora mismo 🚀\\n"
            f"2️⃣ Indicar hora 🕐\\n\\n"
            f"_(El conductor puede completar el cupo en el paradero)_")
'''

new_ruta = '''        await enviar_mensaje(numero,
            f"{ruta['emoji']} *{ruta['nombre']}* — S/{ruta['tarifa']:.2f} por pasajero\\n\\n"
            "📌 *Importante:* este servicio es compartido.\\n"
            "La salida depende de cupos disponibles o confirmación del conductor.\\n\\n"
            f"🕐 *¿Cuándo necesitas el colectivo?*\\n\\n"
            f"1️⃣ Ahora mismo 🚀\\n"
            f"2️⃣ Indicar hora 🕐" + NAV)
'''

if old_ruta in text:
    text = text.replace(old_ruta, new_ruta, 1)

# 7) Confirmación final: no decir reservado, decir cupo
text = text.replace(
    "🚌 *Confirma tu colectivo:*",
    "🚌 *Confirma tu cupo de colectivo compartido:*"
)

text = text.replace(
    "👥 Asientos:",
    "👥 Cupos solicitados:"
)

text = text.replace(
    "📍 Recojo:",
    "📍 Recojo solicitado:"
)

text = text.replace(
    "💰 Total:",
    "💰 Precio referencial:"
)

text = text.replace(
    "1️⃣ *CONFIRMAR* ✅",
    "1️⃣ *REGISTRAR CUPO* ✅"
)

text = text.replace(
    "🎉 *¡Colectivo reservado!*",
    "✅ *Cupo registrado* 🚌"
)

text = text.replace(
    "Estamos buscando conductor. Te contactarán pronto.",
    "Estamos agrupando pasajeros para esta ruta. Te avisaremos cuando un conductor confirme la salida."
)

text = text.replace(
    "📌 *Recuerda:* el colectivo sale cuando se completan ",
    "📌 *Recuerda:* el colectivo compartido sale cuando se completan "
)

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
    "Colectivo compartido con recojo a domicilio",
    "primer servicio urbano gratis hasta S/7",
    "sujeto a cupos disponibles",
    "Confirma tu cupo de colectivo compartido",
    "REGISTRAR CUPO"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
