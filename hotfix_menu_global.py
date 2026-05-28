from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_hotfix_menu_global_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

if "HOTFIX_MENU_GLOBAL" in text:
    print("AVISO: El hotfix global de menu ya existe.")
else:
    targets = [
        '    estado = sesion["estado"]\n',
        '    estado = sesion.get("estado", S_MENU)\n',
        '    estado = sesion.get("estado")\n',
    ]

    marker = None
    for t in targets:
        if t in text:
            marker = t
            break

    if not marker:
        raise SystemExit("ERROR: No encontré la línea donde se define estado")

    bloque = marker + '''
    # HOTFIX_MENU_GLOBAL: salida universal para no dejar usuarios atrapados en un flujo.
    if texto in ("menu", "menú", "hola", "inicio", "salir", "0"):
        sesiones[numero] = {"estado": S_MENU, "datos": {}}
        await enviar_mensaje(numero, MSG_BIENVENIDA)
        return

'''

    text = text.replace(marker, bloque, 1)

    BOT.write_text(text, encoding="utf-8")
    print(f"OK: bot.py actualizado. Backup creado: {backup}")

try:
    py_compile.compile(str(BOT), doraise=True)
    print("OK: bot.py compila correctamente.")
except Exception as e:
    shutil.copy2(backup, BOT)
    raise SystemExit(f"ERROR: bot.py no compila. Restaurado backup. {e}")

updated = BOT.read_text(encoding="utf-8")
print("HOTFIX_MENU_GLOBAL:", "OK" if "HOTFIX_MENU_GLOBAL" in updated else "NO ENCONTRADO")
