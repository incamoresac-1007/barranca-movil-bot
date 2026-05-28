from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_promo_profesional_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Reemplazar función de detección promo con más palabras reales de Facebook
start_fn = text.find("def es_comando_promo")
start_msg = text.find("MSG_PROMO_LANZAMIENTO", start_fn)

if start_fn == -1 or start_msg == -1:
    raise SystemExit("ERROR: No encontré función/mensaje de promo")

new_fn = '''def es_comando_promo(texto: str) -> bool:
    t = _normalizar_geo(texto or "")
    claves = [
        "promo", "promocion", "promoción",
        "viaje gratis", "primer viaje gratis",
        "primer viaje urbano gratis",
        "gratis", "descuento",
        "facebook", "face", "fb",
        "publicacion", "publicación",
        "anuncio", "lanzamiento",
        "vi la publicacion", "vi la publicación",
        "quiero mi viaje gratis"
    ]
    return any(c in t for c in claves)


'''
text = text[:start_fn] + new_fn + text[start_msg:]

# 2) Reemplazar mensaje de promo por versión bonita y sin \\n visibles
start = text.find("MSG_PROMO_LANZAMIENTO = (")
if start == -1:
    raise SystemExit("ERROR: No encontré MSG_PROMO_LANZAMIENTO")

end = text.find("\n)\n", start)
if end == -1:
    raise SystemExit("ERROR: No encontré cierre de MSG_PROMO_LANZAMIENTO")
end = end + len("\n)\n")

new_msg = '''MSG_PROMO_LANZAMIENTO = (
    "🎉 *¡Bienvenido a Barranca Móvil!* 🚖\\n\\n"
    "🎁 *Promo de lanzamiento:*\\n"
    "*Tu primer viaje urbano gratis*\\n\\n"
    "👤 Válido para *usuarios nuevos*\\n"
    "🎟️ Solo para los *10 primeros cupos*\\n\\n"
    "📍 Para verificar disponibilidad, envíanos tu *nombre* y tu *zona de recojo*.\\n"
    "_Ejemplo: Ana Torres - Urb. Los Jardines_\\n\\n"
    "⚠️ *Importante:*\\n"
    "• Aplica solo para el *primer viaje urbano dentro de Barranca*.\\n"
    "• No aplica para distritos, anexos, Huacho, Lima, turismo ni encomiendas.\\n"
    "• Sujeto a cupos promocionales y disponibilidad de conductor.\\n\\n"
    "¿Qué deseas hacer?\\n\\n"
    "1️⃣ Solicitar taxi urbano\\n"
    "2️⃣ Colectivo compartido con recojo a domicilio\\n"
    "0️⃣ Salir"
)
'''

text = text[:start] + new_msg + text[end:]

# 3) Mejorar bloque que responde promo y registrar consulta en Google Sheets como alerta
old = '''        if es_comando_promo(texto):
            datos["origen_promo"] = "PROMO_PRIMER_VIAJE_URBANO"
            sesion["estado"] = S_MENU
            await enviar_mensaje(numero, MSG_PROMO_LANZAMIENTO)
            return
'''

new = '''        if es_comando_promo(texto):
            datos["origen_promo"] = "PROMO_PRIMER_VIAJE_URBANO"
            sesion["estado"] = S_MENU

            # Registrar interés de promo en Google Sheets como alerta operativa.
            # Luego se reemplazará por la hoja PROMOCIONES con contador real.
            try:
                asyncio.create_task(sheets_evento("add_alerta", {
                    "id_servicio": f"PROMO-{str(numero)[-4:]}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "tipo_alerta": "PROMO_VALIDACION",
                    "prioridad": "MEDIA",
                    "descripcion": f"Cliente +{numero} consultó la promoción de primer viaje urbano gratis. Validar si aún hay cupo disponible.",
                    "requiere_accion": "SI",
                    "estado_alerta": "ABIERTA",
                    "responsable": "Operador"
                }))
            except Exception as e:
                print(f"[PROMO ALERTA ERROR] {e}", flush=True)

            await enviar_mensaje(numero, MSG_PROMO_LANZAMIENTO)
            return
'''

if old not in text:
    raise SystemExit("ERROR: No encontré bloque exacto de promo en S_MENU")

text = text.replace(old, new, 1)

# 4) Agregar una línea breve de promo en bienvenida, sin saturar
old_bienvenida = '''0️⃣ Salir

O escribe tu consulta libremente 💬'''
new_bienvenida = '''0️⃣ Salir

🎉 Promo: *primer viaje urbano gratis* para usuarios nuevos.
Escribe *promo* para validar disponibilidad.

O escribe tu consulta libremente 💬'''

if old_bienvenida in text and "Escribe *promo* para validar disponibilidad" not in text:
    text = text.replace(old_bienvenida, new_bienvenida, 1)

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
    "¡Bienvenido a Barranca Móvil!",
    "Promo de lanzamiento",
    "PROMO_VALIDACION",
    "Escribe *promo* para validar disponibilidad",
    "quiero mi viaje gratis"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
