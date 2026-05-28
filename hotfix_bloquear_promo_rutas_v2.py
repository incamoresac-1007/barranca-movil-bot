from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_bloquear_promo_rutas_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

start = text.find("def aplicar_promo_monto(")
if start == -1:
    raise SystemExit("ERROR: No encontré def aplicar_promo_monto")

# Buscar el final de la función hasta antes de la siguiente definición de función.
end = text.find("\ndef ", start + 1)
if end == -1:
    raise SystemExit("ERROR: No pude encontrar el final de aplicar_promo_monto")

new_block = r'''
def promo_bloqueada_por_ruta(datos: dict, servicio: str) -> tuple[bool, str]:
    """
    Bloquea la promo en rutas largas o servicios fuera de movilidad local.
    Promo permitida: taxi urbano local y colectivo local.
    """
    servicio = (servicio or "").upper()

    textos = [
        datos.get("destino_texto", ""),
        datos.get("colectivo_ruta", ""),
        datos.get("ruta_nombre", ""),
        datos.get("destino", ""),
        datos.get("enc_destino", ""),
    ]

    combinado = " ".join(str(x or "") for x in textos).lower()

    bloqueados = [
        "huacho",
        "lima",
        "caral",
        "turismo",
        "vinto",
        "potao",
        "santa elena",
    ]

    if servicio == "ENCOMIENDA":
        return True, "La promo no aplica para encomiendas."

    if servicio == "TURISMO":
        return True, "La promo no aplica para turismo."

    for palabra in bloqueados:
        if palabra in combinado:
            return True, f"La promo no aplica para esta ruta: {palabra.title()}."

    return False, ""


def aplicar_promo_monto(datos: dict, monto, servicio: str):
    try:
        monto = float(monto)
    except Exception:
        return 0.0, monto, ""

    if not datos.get("promo_activa"):
        return 0.0, monto, ""

    servicio = (servicio or "").upper()

    if servicio not in ["TAXI", "COLECTIVO"]:
        return 0.0, monto, ""

    bloqueada, motivo = promo_bloqueada_por_ruta(datos, servicio)
    if bloqueada:
        datos["promo_bloqueada"] = True
        datos["promo_motivo_bloqueo"] = motivo
        return 0.0, monto, "\n⚠️ *Promo no aplicada:* " + motivo + "\n"

    descuento = min(PROMO_TOPE, monto)
    total_final = max(0.0, monto - descuento)

    datos["promo_codigo"] = PROMO_CODIGO
    datos["promo_descuento"] = descuento
    datos["promo_total_final"] = total_final

    if total_final <= 0:
        texto_promo = (
            f"\n🎁 *Promo aplicada:* -S/{descuento:.2f}\n"
            f"✅ *Total a pagar: S/0.00*\n"
        )
    else:
        texto_promo = (
            f"\n🎁 *Promo aplicada:* -S/{descuento:.2f}\n"
            f"💰 *Total con promo: S/{total_final:.2f}*\n"
        )

    return descuento, total_final, texto_promo

'''

text = text[:start] + new_block + text[end:]

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
    "promo_bloqueada_por_ruta",
    "La promo no aplica para esta ruta",
    "servicio not in [\"TAXI\", \"COLECTIVO\"]",
    "huacho",
    "lima"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
