from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_emergencia_promo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)

# 1) Arreglar MSG_BIENVENIDA: quitar \n literales visibles
old_bienvenida = '''🎉 Promo: *primer servicio urbano gratis hasta S/7*.\\nEscribe *promo* para validar disponibilidad.\\n\\nO escribe tu consulta libremente 💬"""'''

new_bienvenida = '''🎁 Promo de lanzamiento: *primer servicio urbano gratis hasta S/7*.
Escribe *promo* para ver condiciones.

O escribe tu consulta libremente 💬"""'''

if old_bienvenida in text:
    text = text.replace(old_bienvenida, new_bienvenida, 1)
else:
    print("AVISO: No encontré bienvenida exacta con slash-n. Continuo...", flush=True)

# 2) Definir MSG_PROMO_LANZAMIENTO si no existe
if "MSG_PROMO_LANZAMIENTO" not in text.split("MSG_TARIFAS")[0]:
    marker = "MSG_TARIFAS ="
    promo_msg = '''MSG_PROMO_LANZAMIENTO = """🎉 *Promo de lanzamiento Barranca Móvil*

🎁 *Tu primer servicio urbano puede ser GRATIS*
💰 Valor máximo promocional: *S/7*
🎟️ Solo para los *10 primeros usuarios nuevos*

✅ *Aplica para:*
🚖 Taxi urbano dentro de Barranca
🚌 Primer cupo en colectivo compartido
📦 Encomienda urbana pequeña

⚠️ *No aplica para:*
Lima, Huacho, turismo, viajes largos, anexos lejanos, cargas pesadas o riesgosas.

📍 Para validar disponibilidad, escribe tu *nombre* y tu *zona de recojo*.
_Ejemplo: Ana Torres - Urb. Los Jardines_

1️⃣ Solicitar taxi urbano
2️⃣ Colectivo compartido
3️⃣ Encomienda urbana
0️⃣ Salir"""

'''
    if marker not in text:
        raise SystemExit("ERROR: No encontré MSG_TARIFAS para insertar promo")
    text = text.replace(marker, promo_msg + marker, 1)
else:
    print("MSG_PROMO_LANZAMIENTO ya existe antes de MSG_TARIFAS", flush=True)

BOT.write_text(text, encoding="utf-8")
print(f"OK: bot.py actualizado. Backup creado: {backup}")

try:
    py_compile.compile(str(BOT), doraise=True)
    print("OK: bot.py compila correctamente.")
except Exception as e:
    shutil.copy2(backup, BOT)
    raise SystemExit(f"ERROR: bot.py no compila. Restaurado backup. {e}")

updated = BOT.read_text(encoding="utf-8")
print("MSG_PROMO_LANZAMIENTO:", "OK" if "MSG_PROMO_LANZAMIENTO" in updated else "NO")
print("slash-n visible en bienvenida:", "MAL" if "gratis hasta S/7*.\\nEscribe" in updated else "OK")
