from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_promo_aplicable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Agregar helpers de promo si no existen
if "PROMO_TOPE = 7.00" not in text:
    marker = "COLECTIVO_MAX_ASIENTOS = 4"
    helper = '''
PROMO_TOPE = 7.00
PROMO_CODIGO = "PROMO_PRIMER_SERVICIO_URBANO"


def texto_es_promo(texto: str) -> bool:
    t = (texto or "").lower().strip()
    claves = [
        "promo", "promocion", "promoción",
        "gratis", "servicio gratis", "viaje gratis",
        "primer servicio", "primer viaje",
        "facebook", "anuncio", "descuento"
    ]
    return any(c in t for c in claves)


def aplicar_promo_monto(datos: dict, monto: float, servicio: str) -> tuple[float, float, str]:
    """
    Aplica promo hasta S/7 si la sesión viene marcada con promo.
    Retorna: descuento, total_final, texto_promo
    """
    try:
        monto = float(monto or 0)
    except Exception:
        monto = 0.0

    if not datos.get("promo_activa"):
        return 0.0, monto, ""

    servicio = (servicio or "").upper()

    # Promo solo para servicios urbanos permitidos.
    if servicio not in ["TAXI", "COLECTIVO", "ENCOMIENDA"]:
        return 0.0, monto, ""

    descuento = min(PROMO_TOPE, monto)
    total_final = max(0.0, monto - descuento)

    datos["promo_codigo"] = PROMO_CODIGO
    datos["promo_descuento"] = descuento
    datos["promo_total_final"] = total_final

    if total_final <= 0:
        texto_promo = (
            f"\\n🎁 *Promo aplicada:* -S/{descuento:.2f}\\n"
            f"✅ *Total a pagar: S/0.00*\\n"
        )
    else:
        texto_promo = (
            f"\\n🎁 *Promo aplicada:* -S/{descuento:.2f}\\n"
            f"💰 *Total con promo: S/{total_final:.2f}*\\n"
        )

    return descuento, total_final, texto_promo

'''
    if marker not in text:
        raise SystemExit("ERROR: No encontré COLECTIVO_MAX_ASIENTOS")
    text = text.replace(marker, marker + "\n" + helper, 1)

# 2) Interceptar promo en S_MENU antes de opciones 1/2/3/4
old_menu = '''    elif estado == S_MENU:
        if texto == "1":'''

new_menu = '''    elif estado == S_MENU:
        if texto_es_promo(texto):
            datos["promo_activa"] = True
            datos["promo_codigo"] = PROMO_CODIGO
            await enviar_mensaje(numero,
                "🎉 *Promo de lanzamiento Barranca Móvil*\\n\\n"
                "🎁 *Tu primer servicio urbano puede ser GRATIS*\\n"
                "💰 Valor máximo promocional: *S/7*\\n"
                "🎟️ Solo para los *10 primeros usuarios nuevos*\\n\\n"
                "✅ Aplica para:\\n"
                "1️⃣ Taxi urbano dentro de Barranca\\n"
                "2️⃣ Primer cupo en colectivo compartido\\n"
                "3️⃣ Encomienda urbana pequeña\\n\\n"
                "⚠️ No aplica para Lima, Huacho, turismo, viajes largos, anexos lejanos, cargas pesadas o riesgosas.\\n\\n"
                "Elige el servicio que deseas solicitar:\\n"
                "1️⃣ Taxi urbano\\n"
                "2️⃣ Colectivo compartido\\n"
                "3️⃣ Encomienda urbana\\n"
                "0️⃣ Salir")
            return

        if texto == "1":'''

if old_menu not in text:
    raise SystemExit("ERROR: No encontré inicio de S_MENU")

text = text.replace(old_menu, new_menu, 1)

# 3) Mantener promo cuando el usuario elige taxi/colectivo/encomienda
text = text.replace(
    '''            datos["servicio"] = "TAXI"''',
    '''            datos["servicio"] = "TAXI"
            if datos.get("promo_codigo") == PROMO_CODIGO:
                datos["promo_activa"] = True''',
    1
)

text = text.replace(
    '''            datos["servicio"] = "COLECTIVO"''',
    '''            datos["servicio"] = "COLECTIVO"
            if datos.get("promo_codigo") == PROMO_CODIGO:
                datos["promo_activa"] = True''',
    1
)

text = text.replace(
    '''            datos["servicio"] = "ENCOMIENDA"''',
    '''            datos["servicio"] = "ENCOMIENDA"
            if datos.get("promo_codigo") == PROMO_CODIGO:
                datos["promo_activa"] = True''',
    1
)

# 4) Colectivo: mostrar promo aplicada en confirmación
old_confirm = '''        await enviar_mensaje(numero,
            f"🚌 *Confirma tu cupo de colectivo compartido:*\\n\\n"
            f"👤 {datos['nombre']}\\n"
            f"{datos['colectivo_emoji']} Ruta: {datos['colectivo_ruta']}\\n"
            f"🕐 Horario: {datos['colectivo_horario']}\\n"
            f"👥 Cupos solicitados: {datos['colectivo_asientos']}\\n"
            f"📍 Recojo solicitado: {datos['colectivo_recojo']}\\n"
            f"💰 Precio referencial: S/{datos['colectivo_total']:.2f}\\n"
            f"💳 {datos['colectivo_pago']}\\n\\n"
            "1️⃣ *REGISTRAR CUPO* ✅\\n2️⃣ *CANCELAR* ❌" + NAV)'''

new_confirm = '''        _, total_final_promo, texto_promo = aplicar_promo_monto(datos, datos['colectivo_total'], "COLECTIVO")
        datos["colectivo_total_final"] = total_final_promo

        await enviar_mensaje(numero,
            f"🚌 *Confirma tu cupo de colectivo compartido:*\\n\\n"
            f"👤 {datos['nombre']}\\n"
            f"{datos['colectivo_emoji']} Ruta: {datos['colectivo_ruta']}\\n"
            f"🕐 Horario: {datos['colectivo_horario']}\\n"
            f"👥 Cupos solicitados: {datos['colectivo_asientos']}\\n"
            f"📍 Recojo solicitado: {datos['colectivo_recojo']}\\n"
            f"💰 Precio referencial: S/{datos['colectivo_total']:.2f}\\n"
            f"{texto_promo}"
            f"💳 {datos['colectivo_pago']}\\n\\n"
            "📌 La salida se confirmará cuando se completen cupos o cuando un conductor acepte la ruta.\\n\\n"
            "1️⃣ *REGISTRAR CUPO* ✅\\n2️⃣ *CANCELAR* ❌" + NAV)'''

if old_confirm not in text:
    raise SystemExit("ERROR: No encontré bloque de confirmación de colectivo")

text = text.replace(old_confirm, new_confirm, 1)

# 5) Ajustar mensaje final de colectivo para mencionar promo si aplica
old_final = '''            await enviar_mensaje(numero,
                f"✅ *Cupo registrado* 🚌\\n\\n"
                f"Salida programada: *{datos.get('colectivo_horario')}*\\n"
                f"Estamos agrupando pasajeros para esta ruta. Te avisaremos cuando un conductor confirme la salida.\\n\\n"
                f"📌 *Recuerda:* el colectivo compartido sale cuando se completan "
                f"los {COLECTIVO_MAX_ASIENTOS} asientos.\\n\\n"
                f"━━━━━━━━━━━━━━━━\\n1️⃣ Nuevo servicio\\n0️⃣ Salir")'''

new_final = '''            promo_final = ""
            if datos.get("promo_descuento"):
                promo_final = f"\\n🎁 Promo aplicada: -S/{datos.get('promo_descuento', 0):.2f}\\nTotal final: S/{datos.get('promo_total_final', 0):.2f}\\n"

            await enviar_mensaje(numero,
                f"✅ *Cupo registrado* 🚌\\n\\n"
                f"Ruta: *{datos.get('colectivo_ruta')}*\\n"
                f"Horario solicitado: *{datos.get('colectivo_horario')}*\\n"
                f"{promo_final}\\n"
                f"Estamos agrupando pasajeros para esta ruta. Te avisaremos cuando un conductor confirme la salida.\\n\\n"
                f"📌 *Recuerda:* el colectivo compartido sale cuando se completan "
                f"los {COLECTIVO_MAX_ASIENTOS} asientos o cuando un conductor confirma disponibilidad.\\n\\n"
                f"━━━━━━━━━━━━━━━━\\n1️⃣ Nuevo servicio\\n0️⃣ Salir")'''

if old_final in text:
    text = text.replace(old_final, new_final, 1)
else:
    print("AVISO: No encontré mensaje final exacto de colectivo; se mantiene.", flush=True)

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
    "PROMO_TOPE = 7.00",
    "texto_es_promo",
    "aplicar_promo_monto",
    "Promo aplicada",
    "colectivo_total_final"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
