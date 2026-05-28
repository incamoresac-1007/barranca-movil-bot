from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_promo_segura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

start = text.find("MSG_PROMO_LANZAMIENTO = (")
if start == -1:
    raise SystemExit("ERROR: No encontré MSG_PROMO_LANZAMIENTO")

end = text.find("\n)\n", start)
if end == -1:
    raise SystemExit("ERROR: No encontré cierre de MSG_PROMO_LANZAMIENTO")

end = end + len("\n)\n")

new_msg = '''MSG_PROMO_LANZAMIENTO = (
    "🎉 *Promoción de lanzamiento Barranca Móvil*\\\\n\\\\n"
    "🚖 *Primer viaje urbano gratis*\\\\n"
    "✅ Cupos limitados para usuarios nuevos.\\\\n\\\\n"
    "📌 Para evitar duplicados y respetar los 10 cupos disponibles, "
    "validaremos la promoción antes de aplicarla.\\\\n\\\\n"
    "Por favor escribe tu *nombre y zona de recojo* para verificar disponibilidad del cupo.\\\\n\\\\n"
    "⚠️ *Condiciones:*\\\\n"
    "• Aplica solo para primer viaje urbano dentro de Barranca.\\\\n"
    "• No aplica para distritos, anexos, Huacho, Lima, turismo ni encomiendas.\\\\n"
    "• Sujeto a disponibilidad de conductor y cupos promocionales.\\\\n\\\\n"
    "1️⃣ Solicitar taxi urbano\\\\n"
    "2️⃣ Colectivo compartido con recojo a domicilio\\\\n"
    "0️⃣ Salir"
)
'''

text = text[:start] + new_msg + text[end:]

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
for term in ["validaremos la promoción", "respetar los 10 cupos", "MSG_PROMO_LANZAMIENTO"]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
