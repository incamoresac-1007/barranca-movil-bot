from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_simplificar_encomienda_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

old = '''    elif estado == S_ENCOMIENDA_BULTOS:
        paquetes_map = {"1": 1, "2": 2, "3": 3, "4": 4}
        if texto not in paquetes_map:
            await enviar_mensaje(numero, "Responde del *1* al *4*.")
            return
        datos["enc_paquetes"] = paquetes_map[texto]
        sesion["estado"] = S_ENCOMIENDA_TAMANO
        await enviar_mensaje(numero,
            f"✅ *{datos['enc_paquetes']} paquete(s)*\\n\\n"
            "📐 *¿Cuál es el paquete más grande?*\\n\\n"
            "1️⃣ Sobre / Documento — S/3\\n"
            "2️⃣ Paquete pequeño _(hasta 2kg)_ — S/5\\n"
            "3️⃣ Paquete mediano _(2-10kg)_ — S/8\\n"
            "4️⃣ Paquete grande _(10-30kg)_ — S/12\\n"
            "5️⃣ Carga pesada _(+30kg)_ — A coordinar")
'''

new = '''    elif estado == S_ENCOMIENDA_BULTOS:
        paquetes_map = {"1": 1, "2": 2, "3": 3, "4": 4}
        if texto not in paquetes_map:
            await enviar_mensaje(numero, "Responde del *1* al *4*.")
            return

        datos["enc_paquetes"] = paquetes_map[texto]
        datos["enc_tamano"] = "A coordinar"
        datos["enc_equiv_pasajeros"] = 2 if datos["enc_paquetes"] <= 2 else 3
        datos["enc_requiere_confirmacion"] = True
        datos["enc_tarifa_base"] = None

        paquetes_txt = "1 bulto/paquete" if datos["enc_paquetes"] == 1 else f"{datos['enc_paquetes']} bultos/paquetes"

        sesion["estado"] = S_ENCOMIENDA_FOTO
        await enviar_mensaje(numero,
            f"✅ *{paquetes_txt}*\\n"
            "📦 Tamaño/precio: *a coordinar con el conductor*\\n\\n"
            "📸 *Envía una foto de tu encomienda*\\n"
            "_(Para que el conductor sepa qué va a transportar)_\\n\\n"
            "O escribe *omitir* si no tienes foto ahora.\\n\\n"
            "0️⃣ Volver atrás\\n"
            "*menu* Ir al inicio")
'''

if old not in text:
    raise SystemExit("ERROR: No encontré el bloque exacto de S_ENCOMIENDA_BULTOS")

text = text.replace(old, new, 1)

# Cambiar textos donde todavía dice "paquete(s)" en mensajes principales.
text = text.replace(
    'f"✅ *{auto_paquetes} paquete(s)*\\n\\n"',
    'f"✅ *{auto_paquetes} {\'bulto/paquete\' if int(auto_paquetes) == 1 else \'bultos/paquetes\'}*\\n\\n"'
)

text = text.replace(
    'f"Cantidad: {auto_paquetes} paquete(s)\\n"',
    'f"Cantidad: {_paquetes_txt(auto_paquetes)}\\n"'
)

text = text.replace(
    'f"🔢 {paquetes} paquete(s) | 📸 {foto_txt}\\n"',
    'f"🔢 {paquetes} {\'bulto/paquete\' if int(paquetes) == 1 else \'bultos/paquetes\'} | 📸 {foto_txt}\\n"'
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
    'datos["enc_tamano"] = "A coordinar"',
    "bultos/paquetes",
    "Tamaño/precio: *a coordinar con el conductor*"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
