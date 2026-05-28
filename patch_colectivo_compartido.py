from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_colectivo_compartido_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Cambiar textos generales: menú, ayuda y tarifas
reemplazos_simples = {
    "2️⃣ Colectivo puerta a puerta 🚌": "2️⃣ Colectivo compartido con recojo a domicilio 🚌",
    "🚌 *Colectivo Puerta a Puerta:*": "🚌 *Colectivo compartido con recojo a domicilio:*",
    "✅ *Precio incluye recojo en tu domicilio*": "✅ *Incluye solicitud de recojo en domicilio*",
    "_(2+ asientos: descuento en recojo S/0.50 c/u)_": "_Salida sujeta a cupos disponibles o confirmación del conductor._",
    "Precios por pasajero, incluye recojo en tu domicilio": "Precio por pasajero. Recojo a domicilio sujeto a cupos disponibles o confirmación del conductor",
}

for old, new in reemplazos_simples.items():
    text = text.replace(old, new)

# 2) Mejorar entrada al flujo colectivo después del nombre
old = '''        elif servicio == "COLECTIVO":
            sesion["estado"] = S_COLECTIVO_RUTA
            rutas_txt = "\\n".join([f"{k}️⃣ {v['emoji']} {v['nombre']} — S/{v['tarifa']:.2f}"
                                    for k,v in COLECTIVO_RUTAS.items()])
            await enviar_mensaje(numero,
                f"👍 Hola *{datos['nombre']}*! 🚌\\n\\n"
                f"*¿A dónde vas?*\\n\\n"
                f"{rutas_txt}\\n\\n"
                f"_(Precios por pasajero, incluye recojo en tu domicilio)_")
'''

new = '''        elif servicio == "COLECTIVO":
            sesion["estado"] = S_COLECTIVO_RUTA
            rutas_txt = "\\n".join([f"{k}️⃣ {v['emoji']} {v['nombre']} — S/{v['tarifa']:.2f}"
                                    for k,v in COLECTIVO_RUTAS.items()])
            await enviar_mensaje(numero,
                f"👍 Hola *{datos['nombre']}*! 🚌\\n\\n"
                "🚌 *Colectivo compartido con recojo a domicilio*\\n"
                "_Reservas tu cupo por WhatsApp y te avisamos cuando haya salida disponible._\\n\\n"
                "*¿A dónde vas?*\\n\\n"
                f"{rutas_txt}\\n\\n"
                "📌 _Precio por pasajero. El recojo a domicilio está sujeto a cupos disponibles o confirmación del conductor._")
'''

if old in text:
    text = text.replace(old, new, 1)
else:
    print("AVISO: No encontré bloque exacto de entrada a colectivo; se aplicaron reemplazos generales.", flush=True)

# 3) Mejorar mensaje al elegir ruta
old = '''        await enviar_mensaje(numero,
            f"{ruta['emoji']} *{ruta['nombre']}* — S/{ruta['tarifa']:.2f} por pasajero\\n\\n"
            f"🕐 *¿Cuándo necesitas el colectivo?*\\n\\n"
            f"1️⃣ Ahora mismo 🚀\\n"
            f"2️⃣ Indicar hora 🕐\\n\\n"
            f"_(El conductor puede completar el cupo en el paradero)_")
'''

new = '''        await enviar_mensaje(numero,
            f"{ruta['emoji']} *{ruta['nombre']}* — S/{ruta['tarifa']:.2f} por pasajero\\n\\n"
            "📌 *Importante:* este es un servicio compartido.\\n"
            "La salida depende de cupos disponibles o confirmación del conductor.\\n"
            "Si deseas salida inmediata con pocos pasajeros, el conductor puede coordinar una tarifa especial.\\n\\n"
            f"🕐 *¿Cuándo necesitas el colectivo?*\\n\\n"
            f"1️⃣ Ahora mismo 🚀\\n"
            f"2️⃣ Indicar hora 🕐\\n\\n"
            "0️⃣ Cancelar\\n"
            "*menu* Ir al inicio")
'''

if old in text:
    text = text.replace(old, new, 1)
else:
    print("AVISO: No encontré bloque exacto de elección de ruta.", flush=True)

# 4) Mejorar confirmación del colectivo antes de confirmar
old = '''        await enviar_mensaje(numero,
            f"🚌 *Confirma tu colectivo:*\\n\\n"
            f"👤 {datos['nombre']}\\n"
            f"{datos['colectivo_emoji']} Ruta: {datos['colectivo_ruta']}\\n"
            f"🕐 Horario: {datos['colectivo_horario']}\\n"
            f"👥 Asientos: {datos['colectivo_asientos']}\\n"
            f"📍 Recojo: {datos['colectivo_recojo']}\\n"
            f"💰 Total: S/{datos['colectivo_total']:.2f}\\n"
            f"💳 {datos['colectivo_pago']}\\n\\n"
            "1️⃣ *CONFIRMAR* ✅\\n2️⃣ *CANCELAR* ❌" + NAV)
'''

new = '''        await enviar_mensaje(numero,
            f"🚌 *Confirma tu cupo de colectivo compartido:*\\n\\n"
            f"👤 {datos['nombre']}\\n"
            f"{datos['colectivo_emoji']} Ruta: {datos['colectivo_ruta']}\\n"
            f"🕐 Horario solicitado: {datos['colectivo_horario']}\\n"
            f"👥 Cupos solicitados: {datos['colectivo_asientos']}\\n"
            f"📍 Recojo solicitado: {datos['colectivo_recojo']}\\n"
            f"💰 Referencial: S/{datos['colectivo_total']:.2f}\\n"
            f"💳 {datos['colectivo_pago']}\\n\\n"
            "📌 *Importante:* la salida se confirma cuando haya cupos disponibles o cuando un conductor acepte la ruta.\\n"
            "Si deseas salida inmediata, el conductor podrá coordinar una tarifa especial.\\n\\n"
            "1️⃣ *REGISTRAR CUPO* ✅\\n2️⃣ *CANCELAR* ❌" + NAV)
'''

if old in text:
    text = text.replace(old, new, 1)
else:
    print("AVISO: No encontré bloque exacto de confirmación de colectivo.", flush=True)

# 5) Mejorar mensaje final al pasajero después de confirmar
old = '''            await enviar_mensaje(numero,
                f"🎉 *¡Colectivo reservado!*\\n\\n"
                f"Salida programada: *{datos.get('colectivo_horario')}*\\n"
                f"Estamos buscando conductor. Te contactarán pronto.\\n\\n"
                f"📌 *Recuerda:* el colectivo sale cuando se completan "
                f"los {COLECTIVO_MAX_ASIENTOS} asientos.\\n\\n"
                f"━━━━━━━━━━━━━━━━\\n1️⃣ Nuevo servicio\\n0️⃣ Salir")
'''

new = '''            await enviar_mensaje(numero,
                f"✅ *Cupo registrado* 🚌\\n\\n"
                f"Ruta: *{datos.get('colectivo_ruta')}*\\n"
                f"Horario solicitado: *{datos.get('colectivo_horario')}*\\n"
                f"Recojo solicitado: *{datos.get('colectivo_recojo')}*\\n\\n"
                "Estamos agrupando pasajeros para esta ruta.\\n"
                "Te avisaremos cuando un conductor confirme la salida.\\n\\n"
                "📌 *Recuerda:* el colectivo compartido sale cuando hay cupos disponibles "
                "o cuando el conductor confirma disponibilidad.\\n"
                "Si deseas salida inmediata, puede aplicar tarifa especial.\\n\\n"
                f"━━━━━━━━━━━━━━━━\\n1️⃣ Nuevo servicio\\n0️⃣ Salir")
'''

if old in text:
    text = text.replace(old, new, 1)
else:
    print("AVISO: No encontré bloque exacto de mensaje final colectivo.", flush=True)

# 6) Mejorar mensaje a conductores en notificar_conductores para COLECTIVO
old = '''    elif tipo == "COLECTIVO":
        msg = (f"🚌 *NUEVO COLECTIVO*\\n\\n"
               f"👤 {d.get('nombre')} | 📱 +{numero_cliente}\\n"
               f"{d.get('colectivo_emoji','')} {d.get('colectivo_ruta')}\\n"
               f"🕐 {d.get('colectivo_horario')}\\n"
               f"👥 {d.get('colectivo_asientos')} asiento(s) confirmados\\n"
               f"📍 Recojo: {d.get('colectivo_recojo')}\\n"
               f"💰 S/{d.get('colectivo_total')} | 💳 {d.get('colectivo_pago')}\\n\\n"
               f"💡 Puedes completar el cupo en el paradero\\n\\n"
               f"Responde: *ACEPTO {numero_cliente}*")
'''

new = '''    elif tipo == "COLECTIVO":
        d["observacion_sheets"] = "Colectivo compartido con recojo a domicilio. Salida sujeta a cupos disponibles o confirmación del conductor."
        msg = (f"🚌 *NUEVO COLECTIVO COMPARTIDO*\\n\\n"
               f"👤 Cliente: {d.get('nombre')} | 📱 +{numero_cliente}\\n"
               f"{d.get('colectivo_emoji','')} Ruta: {d.get('colectivo_ruta')}\\n"
               f"🕐 Horario solicitado: {d.get('colectivo_horario')}\\n"
               f"👥 Cupos solicitados: {d.get('colectivo_asientos')}\\n"
               f"📍 Recojo solicitado: {d.get('colectivo_recojo')}\\n"
               f"💰 Referencial: S/{d.get('colectivo_total')} | 💳 {d.get('colectivo_pago')}\\n\\n"
               f"📌 Servicio sujeto a cupos disponibles o confirmación del conductor.\\n"
               f"Puedes recogerlo, completar cupos en el paradero o coordinar tarifa especial si desea salida inmediata.\\n\\n"
               f"Responde: *ACEPTO {numero_cliente}*")
'''

if old in text:
    text = text.replace(old, new, 1)
else:
    print("AVISO: No encontré bloque exacto de notificación a conductores para colectivo.", flush=True)

# 7) Corregir typo detectado en turismo: 'E jemplo'
text = text.replace("E jemplo: Ana Torres", "Ejemplo: Ana Torres")

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
    "Colectivo compartido con recojo a domicilio",
    "Cupo registrado",
    "REGISTRAR CUPO",
    "NUEVO COLECTIVO COMPARTIDO",
    "sujeto a cupos disponibles"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
