from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_limpiar_promo_menu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

old_block = '''🎉 Promo: *primer viaje urbano gratis* para usuarios nuevos.
Escribe *promo* para validar disponibilidad.

🎉 Promo: *primer servicio urbano gratis hasta S/7*.
Escribe *promo* para validar disponibilidad.'''

new_block = '''🎉 Promo: *primer servicio urbano gratis hasta S/7*.
Escribe *promo* para validar disponibilidad.'''

if old_block in text:
    text = text.replace(old_block, new_block, 1)
else:
    # Limpieza alternativa por si hay variaciones de saltos
    text = text.replace(
        '''🎉 Promo: *primer viaje urbano gratis* para usuarios nuevos.
Escribe *promo* para validar disponibilidad.

''',
        "",
        1
    )

# Asegurar que no quede la frase antigua en bienvenida
text = text.replace(
    "🎉 Promo: *primer viaje urbano gratis* para usuarios nuevos.\n"
    "Escribe *promo* para validar disponibilidad.\n\n",
    ""
)

if text == original:
    print("AVISO: No se aplicaron cambios nuevos. Puede que ya esté limpio.")
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
print("primer viaje urbano gratis:", "AUN EXISTE" if "primer viaje urbano gratis" in updated else "OK eliminado")
print("primer servicio urbano gratis hasta S/7:", "OK" if "primer servicio urbano gratis hasta S/7" in updated else "NO ENCONTRADO")
