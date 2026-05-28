from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_promo_movilidad_texto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

reemplazos = {
    "primer servicio urbano gratis hasta S/7": "primer servicio de movilidad puede salirte GRATIS",
    "primer servicio urbano gratis": "primer servicio de movilidad puede salirte GRATIS",
    "primer servicio urbano puede ser GRATIS": "primer servicio de movilidad puede salirte GRATIS",
    "Tu primer servicio urbano puede ser GRATIS": "Tu primer servicio de movilidad puede salirte GRATIS",
    "Encomienda urbana pequeña": "No aplica para encomiendas",
    "3️⃣ Encomienda urbana": "3️⃣ Envío de encomienda",
    "📦 Encomienda urbana pequeña\\n": "",
    "📦 Encomienda urbana pequeña\n": "",
    "Aplica para taxi urbano, colectivo compartido y encomienda urbana pequeña": "Aplica para taxi urbano y colectivo compartido",
}

for old, new in reemplazos.items():
    text = text.replace(old, new)

# Insertar explicación clara si el mensaje de promo existe y aún no la tiene.
if "Si tu viaje cuesta S/7 o menos" not in text:
    text = text.replace(
        "🎟️ Solo para los *10 primeros usuarios nuevos*\\n\\n",
        "🎟️ Solo para los *10 primeros usuarios nuevos*\\n\\n"
        "📌 *¿Cómo funciona?*\\n"
        "Si tu viaje cuesta *S/7 o menos*, te sale *GRATIS*.\\n"
        "Si cuesta más de *S/7*, solo pagas la diferencia.\\n\\n",
        1
    )

# Asegurar exclusión de encomiendas en el mensaje visible.
if "No aplica para encomiendas" not in text:
    text = text.replace(
        "⚠️ No aplica para Lima, Huacho, turismo, viajes largos, anexos lejanos, cargas pesadas o riesgosas.",
        "⚠️ No aplica para encomiendas, Lima, Huacho, turismo, viajes largos, anexos lejanos ni servicios especiales.",
        1
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
    "primer servicio de movilidad",
    "Si tu viaje cuesta",
    "solo pagas la diferencia",
    "No aplica para encomiendas"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
