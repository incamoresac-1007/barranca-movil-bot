from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_asignacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Guardar pendientes solo con conductores activos y estado operativo
old_pendiente = '''    # Guardar servicio como pendiente
    servicios_pendientes[numero_cliente] = {
        "tipo": tipo,
        "datos": d.copy(),
        "conductores_notificados": list(CONDUCTORES.keys())
    }

    # Enviar solo a conductores ACTIVOS (no pausados)
    conductores_disponibles = [n for n in CONDUCTORES.keys() if conductores_estado.get(n, True)]
    if not conductores_disponibles:
        await enviar_mensaje(numero_cliente,
            "😔 No hay conductores disponibles ahora.\\n\\nIntenta en unos minutos o escribe *menu*.")
        servicios_pendientes.pop(numero_cliente, None)
        return
'''

new_pendiente = '''    # Enviar solo a conductores ACTIVOS (no pausados)
    conductores_disponibles = [n for n in CONDUCTORES.keys() if conductores_estado.get(n, True)]
    if not conductores_disponibles:
        await enviar_mensaje(numero_cliente,
            "😔 No hay conductores disponibles ahora.\\n\\nIntenta en unos minutos o escribe *menu*.")
        servicios_pendientes.pop(numero_cliente, None)
        return

    # Guardar servicio como pendiente operativo
    servicios_pendientes[numero_cliente] = {
        "tipo": tipo,
        "estado": "PENDIENTE_CONDUCTOR",
        "datos": d.copy(),
        "creado_en": time.time(),
        "conductores_notificados": list(conductores_disponibles)
    }
'''

if old_pendiente not in text:
    raise SystemExit("ERROR: No encontré bloque de servicios_pendientes")

text = text.replace(old_pendiente, new_pendiente, 1)

# 2) Evitar que un conductor no notificado acepte el servicio
old_validacion = '''            if numero_cliente_full in servicios_tomados:
                await enviar_mensaje(numero, "❌ Este servicio ya fue tomado por otro conductor.")
                return

            # Marcar como tomado
'''

new_validacion = '''            if numero_cliente_full in servicios_tomados:
                await enviar_mensaje(numero, "❌ Este servicio ya fue tomado por otro conductor.")
                return

            if numero not in servicios_pendientes[numero_cliente_full].get("conductores_notificados", []):
                await enviar_mensaje(numero, "❌ No puedes tomar este servicio porque no estás en la lista de conductores disponibles para esta solicitud.")
                return

            # Marcar como tomado
'''

if old_validacion not in text:
    raise SystemExit("ERROR: No encontré bloque de validación ACEPTO")

text = text.replace(old_validacion, new_validacion, 1)

# 3) Mejorar mensaje al conductor para servicios que no son taxi
old_msg_conductor = '''                await enviar_mensaje(numero,
                    f"✅ *¡Servicio asignado!*\\n\\n"
                    f"📱 Cliente: +{numero_cliente_full}\\n"
                    f"👤 {servicio['datos'].get('nombre', 'N/A')}\\n"
                    f"📍 {servicio['datos'].get('recojo_texto') or servicio['datos'].get('colectivo_recojo') or servicio['datos'].get('enc_origen', 'N/A')}\\n"
                    f"🏁 {servicio['datos'].get('destino_texto') or servicio['datos'].get('colectivo_ruta') or servicio['datos'].get('enc_destino', 'N/A')}\\n\\n"
                    f"Contáctalo directamente para coordinar.")
'''

new_msg_conductor = '''                await enviar_mensaje(numero,
                    f"✅ *Servicio asignado para ti*\\n\\n"
                    f"🧾 Tipo: *{tipo_servicio}*\\n"
                    f"👤 Cliente: {servicio['datos'].get('nombre', 'N/A')}\\n"
                    f"📱 Teléfono: +{numero_cliente_full}\\n"
                    f"📍 Recojo: {servicio['datos'].get('recojo_texto') or servicio['datos'].get('colectivo_recojo') or servicio['datos'].get('enc_origen', 'N/A')}\\n"
                    f"🏁 Destino/Ruta: {servicio['datos'].get('destino_texto') or servicio['datos'].get('colectivo_ruta') or servicio['datos'].get('enc_destino', 'N/A')}\\n"
                    f"💳 Pago: {servicio['datos'].get('pago') or servicio['datos'].get('colectivo_pago') or 'A coordinar'}\\n\\n"
                    f"Coordina directamente con el cliente.\\n"
                    f"Cuando termines escribe: *FIN*")
'''

if old_msg_conductor not in text:
    raise SystemExit("ERROR: No encontré mensaje conductor no taxi")

text = text.replace(old_msg_conductor, new_msg_conductor, 1)

# 4) Mejorar mensaje al pasajero para servicios que no son taxi
old_msg_cliente = '''                await enviar_mensaje(numero_cliente_full,
                    f"🚖 *¡Conductor en camino!*\\n\\n"
                    f"👤 {conductor['nombre']}\\n"
                    f"🚗 Placa: {conductor['placa']}\\n"
                    f"📱 Contacto: +{numero}\\n\\n"
                    f"El conductor te contactará en breve.\\n"
                    f"Escribe *menu* para otra solicitud.")
'''

new_msg_cliente = '''                await enviar_mensaje(numero_cliente_full,
                    f"✅ *Conductor asignado*\\n\\n"
                    f"👤 Conductor: *{conductor['nombre']}*\\n"
                    f"🚗 Placa: *{conductor['placa']}*\\n"
                    f"📱 Contacto: +{numero}\\n\\n"
                    f"🧾 Servicio: *{tipo_servicio}*\\n"
                    f"📍 Recojo: {servicio['datos'].get('recojo_texto') or servicio['datos'].get('colectivo_recojo') or servicio['datos'].get('enc_origen', 'N/A')}\\n"
                    f"🏁 Destino/Ruta: {servicio['datos'].get('destino_texto') or servicio['datos'].get('colectivo_ruta') or servicio['datos'].get('enc_destino', 'N/A')}\\n\\n"
                    f"El conductor te contactará en breve.\\n"
                    f"Escribe *menu* para otra solicitud.")
'''

if old_msg_cliente not in text:
    raise SystemExit("ERROR: No encontré mensaje cliente no taxi")

text = text.replace(old_msg_cliente, new_msg_cliente, 1)

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
    '"estado": "PENDIENTE_CONDUCTOR"',
    '"creado_en": time.time()',
    "No puedes tomar este servicio",
    "Servicio asignado para ti",
    "Conductor asignado"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
