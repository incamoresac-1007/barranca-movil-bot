from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_enc_dest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Corregir bloque S_ENCOMIENDA_DESTINATARIO
old = '''    elif estado == S_ENCOMIENDA_DESTINATARIO:
        if len(texto) < 3:
            await enviar_mensaje(numero, "Indica nombre y teléfono del destinatario.")
            return
        datos["enc_destinatario"] = texto
        sesion["estado"] = S_ENCOMIENDA_PAGO
        await enviar_mensaje(numero,
            f"✅ Destinatario: *{texto}*\\n\\n"
            f"💰 *Precio:* El conductor confirmará el precio al aceptar\\n"
            f"+ S/2 recargo por envío urgente\\n\\n"
            "💳 *¿Quién paga?*\\n"
            "1️⃣ Yo pago ahora (Efectivo)\\n"
            "2️⃣ Yo pago ahora (Yape)\\n"
            "3️⃣ Paga el destinatario al recibir 🚪" + NAV)
'''

new = '''    elif estado == S_ENCOMIENDA_DESTINATARIO:
        if len(texto) < 3:
            await enviar_mensaje(numero, "Indica nombre y DNI del destinatario.\\nEjemplo: Abel Salinas, 16874530")
            return

        nombre_dest, dni_dest = extraer_nombre_dni(texto)

        if len(nombre_dest) < 3:
            await enviar_mensaje(numero, "Indica el nombre del destinatario.\\nEjemplo: Abel Salinas, 16874530")
            return

        datos["enc_destinatario"] = normalizar_nombre_persona(nombre_dest)
        datos["enc_destinatario_dni"] = dni_dest

        sesion["estado"] = S_ENCOMIENDA_PAGO

        linea_dni = f"\\n🪪 DNI: *{dni_dest}*" if dni_dest else ""

        await enviar_mensaje(numero,
            f"✅ Destinatario: *{datos['enc_destinatario']}*{linea_dni}\\n\\n"
            f"💰 *Precio:* El conductor confirmará el precio al aceptar\\n"
            f"+ S/2 recargo por envío urgente\\n\\n"
            "💳 *¿Quién paga?*\\n"
            "1️⃣ Yo pago ahora (Efectivo)\\n"
            "2️⃣ Yo pago ahora (Yape)\\n"
            "3️⃣ Paga el destinatario al recibir 🚪" + NAV)
'''

if old not in text:
    raise SystemExit("ERROR: No encontré el bloque exacto de S_ENCOMIENDA_DESTINATARIO")

text = text.replace(old, new, 1)

# 2) Mejorar resumen final de encomienda: destinatario + DNI separado
old_res = '''            f"👤 Destinatario: {datos['enc_destinatario']}\\n"
'''

new_res = '''            f"👤 Destinatario: {datos['enc_destinatario']}\\n"
            + (f"🪪 DNI destinatario: {datos['enc_destinatario_dni']}\\n" if datos.get("enc_destinatario_dni") else "")
'''

if old_res in text:
    text = text.replace(old_res, new_res, 1)

# 3) Mejorar notificación a conductor si usa enc_destinatario
old_cond = '''               f"👤 Destinatario: {d.get('enc_destinatario')}\\n"
'''

new_cond = '''               f"👤 Destinatario: {d.get('enc_destinatario')}\\n"
               + (f"🪪 DNI destinatario: {d.get('enc_destinatario_dni')}\\n" if d.get("enc_destinatario_dni") else "")
'''

if old_cond in text:
    text = text.replace(old_cond, new_cond, 1)

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
for term in ["enc_destinatario_dni", "extraer_nombre_dni(texto)", "DNI destinatario"]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
