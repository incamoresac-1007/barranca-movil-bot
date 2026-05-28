from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_nombres_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

helper = '''
def normalizar_nombre_persona(nombre: str) -> str:
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

if "def normalizar_nombre_persona" not in text:
    if "def extraer_nombre_dni" in text:
        text = text.replace("def extraer_nombre_dni", helper + "def extraer_nombre_dni", 1)
    elif "async def procesar(" in text:
        text = text.replace("async def procesar(", helper + "\nasync def procesar(", 1)
    else:
        raise SystemExit("ERROR: No encontré dónde insertar normalizar_nombre_persona")

# Normalizar salida de extraer_nombre_dni
text = text.replace(
    'return raw.strip(" ,.-"), ""',
    'return normalizar_nombre_persona(raw.strip(" ,.-")), ""'
)

text = text.replace(
    'return nombre, dni',
    'return normalizar_nombre_persona(nombre), dni'
)

# Normalizar nombre principal cuando se usa en turismo
text = text.replace(
    'datos["_turismo_nombre_temp"] = datos.get("nombre", "")',
    'datos["_turismo_nombre_temp"] = normalizar_nombre_persona(datos.get("nombre", ""))'
)

# Normalizar nombre cuando se guarda como nombre general del cliente
reemplazos_nombre = {
    'datos["nombre"] = texto': 'datos["nombre"] = normalizar_nombre_persona(texto)',
    "datos['nombre'] = texto": "datos['nombre'] = normalizar_nombre_persona(texto)",
    'datos["nombre"] = txt_norm': 'datos["nombre"] = normalizar_nombre_persona(txt_norm)',
    "datos['nombre'] = txt_norm": "datos['nombre'] = normalizar_nombre_persona(txt_norm)",
}

for old, new in reemplazos_nombre.items():
    if old in text:
        text = text.replace(old, new)

# Normalizar cualquier pasajero agregado desde nombre temporal
text = text.replace(
    'lista.append({"nombre": nombre_temp, "dni": dni})',
    'lista.append({"nombre": normalizar_nombre_persona(nombre_temp), "dni": dni})'
)

text = text.replace(
    'lista.append({"nombre": nombre_detectado, "dni": dni_detectado})',
    'lista.append({"nombre": normalizar_nombre_persona(nombre_detectado), "dni": dni_detectado})'
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
for term in ["normalizar_nombre_persona", "normalizar_nombre_persona(texto)", "normalizar_nombre_persona(nombre)"]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
