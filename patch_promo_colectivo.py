from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_promo_colectivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Pulir textos de colectivo
text = text.replace(
    "💰 Referencial: S/{datos['colectivo_total']:.2f}\\n",
    "💰 Precio referencial: S/{datos['colectivo_total']:.2f}\\n"
)

text = text.replace(
    "📌 *Importante:* la salida se confirma cuando haya cupos disponibles o cuando un conductor acepte la ruta.\\n"
    "Si deseas salida inmediata, el conductor podrá coordinar una tarifa especial.\\n\\n",
    "📌 *Importante:* la salida se confirmará cuando se completen cupos o cuando un conductor acepte la ruta.\\n"
    "Si deseas salida inmediata, el conductor podrá coordinar una tarifa especial.\\n\\n"
)

# 2) Insertar helper de promo si no existe
if "def es_comando_promo" not in text:
    marker = "def generar_id_servicio(numero_cliente: str, tipo: str) -> str:"
    helper = r'''
def es_comando_promo(texto: str) -> bool:
    t = _normalizar_geo(texto or "")
    claves = [
        "promo", "promocion", "promoción",
        "viaje gratis", "primer viaje gratis",
        "primer viaje urbano gratis",
        "gratis", "descuento"
    ]
    return any(c in t for c in claves)


MSG_PROMO_LANZAMIENTO = (
    "🎉 *Promoción de lanzamiento Barranca Móvil*\\n\\n"
    "🚖 *Tu primer viaje urbano GRATIS*\\n"
    "✅ Solo para los *primeros 10 usuarios nuevos*.\\n\\n"
    "📌 *Aplica para:*\\n"
    "• Primer viaje urbano dentro de Barranca.\\n"
    "• Servicio sujeto a disponibilidad de conductor.\\n\\n"
    "⚠️ *No aplica para:*\\n"
    "• Distritos o anexos.\\n"
    "• Huacho o Lima.\\n"
    "• Rutas turísticas.\\n"
    "• Encomiendas.\\n\\n"
    "¿Qué deseas hacer?\\n\\n"
    "1️⃣ Solicitar taxi urbano\\n"
    "2️⃣ Ver otros servicios\\n"
    "0️⃣ Salir"
)

'''
    if marker not in text:
        raise SystemExit("ERROR: No encontré marcador para insertar promo")
    text = text.replace(marker, helper + "\n" + marker, 1)

# 3) Interceptar promo en menú principal
old = '''    elif estado == S_MENU:
        if texto == "1":
'''
new = '''    elif estado == S_MENU:
        if es_comando_promo(texto):
            datos["origen_promo"] = "PROMO_PRIMER_VIAJE_URBANO"
            sesion["estado"] = S_MENU
            await enviar_mensaje(numero, MSG_PROMO_LANZAMIENTO)
            return

        if texto == "1":
'''

if old not in text:
    raise SystemExit("ERROR: No encontré bloque S_MENU para insertar promo")

text = text.replace(old, new, 1)

# 4) Manejar respuesta después del mensaje de promo:
# Si escribe 2, mostrar menú normal. Si escribe 1, inicia taxi.
# Esto se logra ampliando S_MENU: el texto 1 ya inicia taxi.
# Para "2" ya inicia colectivo normalmente; por eso dejamos la promo clara:
# "Ver otros servicios" queda cubierto si escribe menu, pero agregamos texto en MSG si hace falta.
text = text.replace(
    "2️⃣ Ver otros servicios\\n",
    "2️⃣ Colectivo compartido con recojo a domicilio\\n"
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
    "es_comando_promo",
    "MSG_PROMO_LANZAMIENTO",
    "Tu primer viaje urbano GRATIS",
    "Precio referencial",
    "la salida se confirmará"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
