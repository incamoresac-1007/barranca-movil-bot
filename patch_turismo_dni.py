from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_turismo_dni_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Helper para separar nombre + DNI cuando vienen juntos.
if "def extraer_nombre_dni" not in text:
    marker = "async def procesar("
    helper = '''
def extraer_nombre_dni(texto: str):
    """Separa nombre y DNI si el usuario escribe ambos juntos. Ej: 'Zoila Tello, 15862130'."""
    import re
    raw = (texto or "").strip()
    m = re.search(r"\\b(\\d{7,9})\\b", raw)
    if not m:
        return raw.strip(" ,.-"), ""

    dni = m.group(1)
    nombre = (raw[:m.start()] + " " + raw[m.end():]).strip(" ,.-")
    nombre = " ".join(nombre.split())

    return nombre, dni
'''
    if marker not in text:
        raise SystemExit("ERROR: No encontré async def procesar para insertar helper")
    text = text.replace(marker, helper + "\n" + marker, 1)

# 2) Reemplazar paso nombre para detectar "nombre + DNI".
old_nombre = '''        elif paso == "nombre":
            if len(txt_norm) < 3:
                await enviar_mensaje(numero, "✍️ Escribe el nombre completo del pasajero:")
                return
            datos["_turismo_nombre_temp"] = txt_norm
            datos["_turismo_paso"] = "dni"
            await enviar_mensaje(numero,
                f"👤 *{txt_norm}*\\n"
                f"🪪 *DNI del pasajero {idx+1}:*\\n_(8 dígitos)_")
            return
'''

new_nombre = '''        elif paso == "nombre":
            nombre_detectado, dni_detectado = extraer_nombre_dni(txt_norm)

            if len(nombre_detectado) < 3:
                await enviar_mensaje(numero, "✍️ Escribe el nombre completo del pasajero:")
                return

            datos["_turismo_nombre_temp"] = nombre_detectado

            # Si el usuario escribió nombre + DNI juntos, registrar ambos sin volver a pedir DNI.
            if dni_detectado:
                if not dni_detectado.isdigit() or not (7 <= len(dni_detectado) <= 9):
                    await enviar_mensaje(numero, "❌ DNI inválido. Debe tener 7 u 8 dígitos, solo números:")
                    return

                lista.append({"nombre": nombre_detectado, "dni": dni_detectado})
                datos["turismo_pasajeros_lista"] = lista
                siguiente = idx + 1

                if siguiente < personas:
                    datos["_turismo_pasajero_idx"] = siguiente
                    datos["_turismo_paso"] = "nombre"
                    await enviar_mensaje(numero,
                        f"✅ Pasajero {idx+1} registrado.\\n\\n"
                        f"👤 *Nombre del pasajero {siguiente+1}:*")
                    return
                else:
                    datos["turismo_dni_principal"] = lista[0]["dni"] if lista else "—"
                    datos["turismo_pasajeros_extra"] = "\\n".join(
                        [f"{n+2}. {p['nombre']} | DNI: {p['dni']}" for n, p in enumerate(lista[1:])]
                    ) if len(lista) > 1 else ""
            else:
                datos["_turismo_paso"] = "dni"
                await enviar_mensaje(numero,
                    f"👤 *{nombre_detectado}*\\n"
                    f"🪪 *DNI del pasajero {idx+1}:*\\n_(8 dígitos)_")
                return
'''

if old_nombre not in text:
    raise SystemExit("ERROR: No encontré el bloque exacto de paso == nombre")
text = text.replace(old_nombre, new_nombre, 1)

# 3) Mejorar formato cuando el DNI se ingresa separado.
old_extra = '''                datos["turismo_pasajeros_extra"] = " | ".join(
                    [f"{p['nombre']} / {p['dni']}" for p in lista[1:]]) if len(lista) > 1 else ""
'''

new_extra = '''                datos["turismo_pasajeros_extra"] = "\\n".join(
                    [f"{n+2}. {p['nombre']} | DNI: {p['dni']}" for n, p in enumerate(lista[1:])]
                ) if len(lista) > 1 else ""
'''

text = text.replace(old_extra, new_extra)

# 4) Mejorar resumen visual.
old_resumen = '''            + (f"👥 Otros: {datos['turismo_pasajeros_extra']}\\n" if datos.get('turismo_pasajeros_extra') else "")
'''

new_resumen = '''            + (f"👥 Pasajeros adicionales:\\n{datos['turismo_pasajeros_extra']}\\n" if datos.get('turismo_pasajeros_extra') else "")
'''

if old_resumen not in text:
    raise SystemExit("ERROR: No encontré bloque de resumen 'Otros'")
text = text.replace(old_resumen, new_resumen, 1)

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
for term in ["extraer_nombre_dni", "Pasajeros adicionales", "| DNI:", "nombre_detectado"]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
