from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_nombre_apellido_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Cambiar preguntas iniciales por nombre + primer apellido
reemplazos = {
    'await enviar_mensaje(numero, "🙋 ¿Cuál es tu nombre?")':
        'await enviar_mensaje(numero, "🙋 Escribe tu nombre y primer apellido.\\nEjemplo: Ana Torres\\n\\nTambién puedes enviar un audio breve si prefieres.")',

    'await enviar_mensaje(numero, "🚌 ¡Genial! ¿Cuál es tu nombre?")':
        'await enviar_mensaje(numero, "🚌 ¡Genial! Escribe tu nombre y primer apellido.\\nEjemplo: Ana Torres\\n\\nTambién puedes enviar un audio breve si prefieres.")',

    'await enviar_mensaje(numero, "📦 ¡Perfecto! ¿Cuál es tu nombre?")':
        'await enviar_mensaje(numero, "📦 ¡Perfecto! Escribe tu nombre y primer apellido.\\nEjemplo: Ana Torres\\n\\nTambién puedes enviar un audio breve si prefieres.")',

    'await enviar_mensaje(numero, "🗺️ ¡Genial! ¿Cuál es tu nombre?")':
        'await enviar_mensaje(numero, "🗺️ ¡Genial! Escribe tu nombre y primer apellido.\\nEjemplo: Ana Torres\\n\\nTambién puedes enviar un audio breve si prefieres.")',
}

for old, new in reemplazos.items():
    if old in text:
        text = text.replace(old, new)

# 2) Validar nombre + apellido en S_NOMBRE
old = '''    elif estado == S_NOMBRE:
        if len(texto) < 2:
            await enviar_mensaje(numero, "Por favor escribe tu nombre.")
            return
        datos["nombre"] = normalizar_nombre_persona(texto).title()
'''

new = '''    elif estado == S_NOMBRE:
        nombre_normalizado = normalizar_nombre_persona(texto)
        partes_nombre = [p for p in nombre_normalizado.split() if p]

        if len(partes_nombre) < 2:
            await enviar_mensaje(numero,
                "Por favor escribe tu nombre y primer apellido.\\n"
                "Ejemplo: Ana Torres")
            return

        datos["nombre"] = nombre_normalizado
'''

if old not in text:
    raise SystemExit("ERROR: No encontré el bloque exacto de S_NOMBRE")

text = text.replace(old, new, 1)

# 3) Mejorar prompt de encomienda para sugerir audio donde sí aporta
old_enc = '''                f"👍 Hola *{datos['nombre']}*!\\n\\n"
                "📦 ¿Qué vas a enviar?\\n_(ej: ropa, documentos, paquete)_")'''

new_enc = '''                f"👍 Hola *{datos['nombre']}*!\\n\\n"
                "📦 ¿Qué vas a enviar?\\n"
                "Puedes escribirlo o enviar un audio breve.\\n"
                "_Ejemplo: una silla de oficina de 20 kilos_")'''

if old_enc in text:
    text = text.replace(old_enc, new_enc, 1)

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
for term in ["nombre y primer apellido", "partes_nombre", "Puedes escribirlo o enviar un audio breve"]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
