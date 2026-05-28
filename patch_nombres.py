from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_nombres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Agregar helper para nombres si no existe
if "def normalizar_nombre_persona" not in text:
    marker = "def extraer_nombre_dni(texto: str):"
    helper = '''def normalizar_nombre_persona(nombre: str) -> str:
    """Capitaliza nombres de forma simple y segura."""
    nombre = " ".join((nombre or "").strip().split())
    if not nombre:
        return ""

    minusculas = {"de", "del", "la", "las", "los", "y"}
    partes = []
    for i, p in enumerate(nombre.lower().split()):
        if i > 0 and p in minusculas:
            partes.append(p)
        else:
            partes.append(p.capitalize())

    return " ".join(partes)

'''
    if marker not in text:
        raise SystemExit("ERROR: No encontré extraer_nombre_dni")
    text = text.replace(marker, helper + marker, 1)

# 2) Hacer que extraer_nombre_dni devuelva nombre capitalizado
text = text.replace(
    'return raw.strip(" ,.-"), ""',
    'return normalizar_nombre_persona(raw.strip(" ,.-")), ""'
)

text = text.replace(
    'return nombre, dni',
    'return normalizar_nombre_persona(nombre), dni'
)

# 3) Capitalizar nombre temporal del pasajero principal en turismo
text = text.replace(
    'datos["_turismo_nombre_temp"] = datos.get("nombre", "")',
    'datos["_turismo_nombre_temp"] = normalizar_nombre_persona(datos.get("nombre", ""))'
)

# 4) Capitalizar nombre principal en resumen de turismo sin alterar el dato original
text = text.replace(
    'f"👤 {datos[\\'nombre\\']} | DNI: {datos.get(\\'turismo_dni_principal\\',\\'—\\')}\\n"',
    'f"👤 {normalizar_nombre_persona(datos[\\'nombre\\'])} | DNI: {datos.get(\\'turismo_dni_principal\\',\\'—\\')}\\n"'
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
for term in ["normalizar_nombre_persona", "return normalizar_nombre_persona(nombre), dni"]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
