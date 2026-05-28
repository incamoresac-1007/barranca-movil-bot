from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_hotfix_es_comando_promo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)

# Insertar es_comando_promo si fue eliminado
if "def es_comando_promo" not in text:
    marker = "# ── Google Maps"
    helper = '''
def es_comando_promo(texto: str) -> bool:
    """Detecta consultas relacionadas a la promoción sin romper el menú principal."""
    try:
        t = _normalizar_geo(texto or "")
    except Exception:
        t = (texto or "").lower().strip()

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
    if marker not in text:
        raise SystemExit("ERROR: No encontré marcador Google Maps")
    text = text.replace(marker, helper + marker, 1)
else:
    print("es_comando_promo ya existe")

BOT.write_text(text, encoding="utf-8")
print(f"OK: bot.py actualizado. Backup creado: {backup}")

try:
    py_compile.compile(str(BOT), doraise=True)
    print("OK: bot.py compila correctamente.")
except Exception as e:
    shutil.copy2(backup, BOT)
    raise SystemExit(f"ERROR: bot.py no compila. Restaurado backup. {e}")

updated = BOT.read_text(encoding="utf-8")
print("es_comando_promo:", "OK" if "def es_comando_promo" in updated else "NO")
print("MSG_PROMO_LANZAMIENTO:", "OK" if "MSG_PROMO_LANZAMIENTO" in updated else "NO")
