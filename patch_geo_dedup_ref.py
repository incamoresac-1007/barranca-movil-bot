from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_geo_dedup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Insertar referencias locales antes de _limpiar_display_barranca
if "def _referencia_local_barranca" not in text:
    marker = "def _limpiar_display_barranca(nombre: str) -> str:"
    helper = '''def _referencia_local_barranca(nombre: str) -> str:
    n = _normalizar_geo(nombre)

    # Referencias locales conocidas de Barranca
    if "lino" in n:
        return "El Lino, referencia Calle Primavera, Barranca"

    if "pasaje espana" in n or "pje espana" in n or "psje espana" in n:
        return "Pasaje España, zona Pampa de Lara, Barranca"

    if "parque guadalupe" in n or "virgen de guadalupe" in n or "guadalupe" in n:
        return "Parque Virgen de Guadalupe, Barranca"

    if "pasaje pelota" in n or "pje pelota" in n or "psje pelota" in n:
        return "Pasaje Pelota, Barranca"

    return ""

'''
    if marker not in text:
        raise SystemExit("ERROR: No encontré _limpiar_display_barranca")
    text = text.replace(marker, helper + marker, 1)

# 2) Hacer que _limpiar_display_barranca use las referencias locales primero
old = '''    s = (nombre or "").strip()
    if not s:
        return "Barranca"
'''
new = '''    s = (nombre or "").strip()
    if not s:
        return "Barranca"

    ref_local = _referencia_local_barranca(s)
    if ref_local:
        return ref_local
'''
if old in text and new not in text:
    text = text.replace(old, new, 1)

# 3) Deduplicar resultados finales en buscar_lugares_barranca
old = '''    candidatos.sort(key=lambda x: x.get("distancia_barranca", 999))
    resultados = [{"nombre": c["nombre"], "place_id": c["place_id"]} for c in candidatos[:4]]
    print(f"[GEO BARRANCA] '{texto_original}' -> {len(resultados)} resultado(s)", flush=True)
    return resultados
'''
new = '''    candidatos.sort(key=lambda x: x.get("distancia_barranca", 999))

    resultados = []
    claves_nombre = set()

    for c in candidatos:
        nombre_limpio = _limpiar_display_barranca(c.get("nombre", ""))
        clave = _normalizar_geo(nombre_limpio)

        if not clave or clave in claves_nombre:
            continue

        claves_nombre.add(clave)
        resultados.append({
            "nombre": nombre_limpio,
            "place_id": c["place_id"],
        })

        if len(resultados) >= 4:
            break

    print(f"[GEO BARRANCA] '{texto_original}' -> {len(resultados)} resultado(s)", flush=True)
    return resultados
'''
if old not in text:
    raise SystemExit("ERROR: No encontré el bloque final de resultados para deduplicar.")

text = text.replace(old, new, 1)

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
    "def _referencia_local_barranca",
    "referencia Calle Primavera",
    "zona Pampa de Lara",
    "claves_nombre",
    "Pasaje Pelota, Barranca"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
