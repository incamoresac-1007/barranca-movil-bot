from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_enc_dest_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

old = '''    elif estado == S_ENCOMIENDA_DESTINATARIO:
        if len(texto) < 3:
            await enviar_mensaje(numero, "Indica nombre y teléfono del destinatario.")
            return
        datos["enc_destinatario"] = texto
        sesion["estado"] = S_ENCOMIENDA_PAGO
        recargo_urgencia = datos.get("enc_recargo", 0)
        # Tarifa siempre a coordinar — conductor la propone al ver el paquete
        datos["enc_tarifa_final"] = None
        if recargo_urgencia > 0:
            tarifa_txt = (f"El conductor confirmará el precio al aceptar\\n"
                          f"   + S/{recargo_urgencia:.0f} recargo por envío urgente")
        else:
            tarifa_txt = "El conductor confirmará el precio al aceptar"
        await enviar_mensaje(numero,
            f"✅ Destinatario: *{texto}*\\n\\n"
            f"💰 *Precio:* {tarifa_txt}\\n\\n"
            "💳 *¿Quién paga?*\\n"
            "1️⃣ Yo pago ahora (Efectivo)\\n"
            "2️⃣ Yo pago ahora (Yape)\\n"
            "3️⃣ Paga el destinatario al recibir 🚪" + NAV)
'''

new = '''    elif estado == S_ENCOMIENDA_DESTINATARIO:
        if len(texto) < 3:
            await enviar_mensaje(numero,
                "Indica nombre y DNI del destinatario.\\n"
                "Ejemplo: Abel Salinas, 16874530")
            return

        nombre_dest, dni_dest = extraer_nombre_dni(texto)

        if len(nombre_dest) < 3:
            await enviar_mensaje(numero,
                "Indica el nombre del destinatario.\\n"
                "Ejemplo: Abel Salinas, 16874530")
            return

        datos["enc_destinatario"] = normalizar_nombre_persona(nombre_dest)
        datos["enc_destinatario_dni"] = dni_dest

        sesion["estado"] = S_ENCOMIENDA_PAGO
        recargo_urgencia = datos.get("enc_recargo", 0)

        # Tarifa siempre a coordinar — conductor la propone al ver el paquete
        datos["enc_tarifa_final"] = None

        if recargo_urgencia > 0:
            tarifa_txt = (f"El conductor confirmará el precio al aceptar\\n"
                          f"   + S/{recargo_urgencia:.0f} recargo por envío urgente")
        else:
            tarifa_txt = "El conductor confirmará el precio al aceptar"

        linea_dni = f"\\n🪪 DNI: *{dni_dest}*" if dni_dest else ""

        await enviar_mensaje(numero,
            f"✅ Destinatario: *{datos['enc_destinatario']}*{linea_dni}\\n\\n"
            f"💰 *Precio:* {tarifa_txt}\\n\\n"
            "💳 *¿Quién paga?*\\n"
            "1️⃣ Yo pago ahora (Efectivo)\\n"
            "2️⃣ Yo pago ahora (Yape)\\n"
            "3️⃣ Paga el destinatario al recibir 🚪" + NAV)
'''

if old not in text:
    raise SystemExit("ERROR: No encontré el bloque exacto de S_ENCOMIENDA_DESTINATARIO")

text = text.replace(old, new, 1)

old_resumen = '''            f"👤 Destinatario: {datos['enc_destinatario']}\\n"
            f"💰 {tarifa_txt}\\n"
'''

new_resumen = '''            f"👤 Destinatario: {datos['enc_destinatario']}\\n"
            + (f"🪪 DNI destinatario: {datos['enc_destinatario_dni']}\\n" if datos.get("enc_destinatario_dni") else "")
            + f"💰 {tarifa_txt}\\n"
'''

if old_resumen not in text:
    raise SystemExit("ERROR: No encontré el bloque exacto del resumen de encomienda")

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
for term in ["enc_destinatario_dni", "extraer_nombre_dni(texto)", "DNI destinatario"]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
