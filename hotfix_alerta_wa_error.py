from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_alerta_wa_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)

start = text.find("async def enviar_mensaje(")
if start == -1:
    raise SystemExit("ERROR: No encontré async def enviar_mensaje")

end = text.find("\nasync def reenviar_imagen", start)
if end == -1:
    raise SystemExit("ERROR: No encontré async def reenviar_imagen para cerrar el bloque")

new_block = r'''async def enviar_mensaje(to: str, texto: str):
    """
    Envía mensaje por WhatsApp Cloud API.
    Además registra errores críticos para no dejar al bot fallando en silencio.
    """
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": texto}
    }

    destino_tipo = "CONDUCTOR" if "CONDUCTORES" in globals() and to in CONDUCTORES else "CLIENTE"
    if "OPERADOR_WA" in globals() and OPERADOR_WA and to == OPERADOR_WA:
        destino_tipo = "OPERADOR"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=payload)

        if r.status_code >= 400:
            error_txt = r.text[:500]
            print(
                f"[WA ERROR] status={r.status_code} destino={destino_tipo} to={to} error={error_txt}",
                flush=True
            )

            # Registrar alerta operativa en Google Sheets.
            # No usamos WhatsApp para avisar porque justamente WhatsApp puede estar fallando.
            try:
                prioridad = "CRITICA" if r.status_code in (401, 403) else "ALTA"
                descripcion = (
                    f"Error WhatsApp API al enviar mensaje. "
                    f"Status={r.status_code}. Destino={destino_tipo}. To={to}. "
                    f"Respuesta={error_txt}"
                )

                if "sheets_evento" in globals():
                    asyncio.create_task(sheets_evento("add_alerta", {
                        "id_servicio": f"WA-ERROR-{int(time.time())}",
                        "tipo_alerta": "WHATSAPP_API_ERROR",
                        "prioridad": prioridad,
                        "descripcion": descripcion,
                        "requiere_accion": "SI",
                        "estado_alerta": "ABIERTA",
                        "responsable": "Operador"
                    }))
            except Exception as e:
                print(f"[WA ALERT ERROR] No se pudo registrar alerta: {e}", flush=True)

            return False

        print(f"[WA] {r.status_code} destino={destino_tipo} to={to}", flush=True)
        return True

    except Exception as e:
        print(f"[WA EXCEPTION] destino={destino_tipo} to={to} error={e}", flush=True)

        try:
            if "sheets_evento" in globals():
                asyncio.create_task(sheets_evento("add_alerta", {
                    "id_servicio": f"WA-EXCEPTION-{int(time.time())}",
                    "tipo_alerta": "WHATSAPP_SEND_EXCEPTION",
                    "prioridad": "CRITICA",
                    "descripcion": f"Excepción enviando WhatsApp. Destino={destino_tipo}. To={to}. Error={e}",
                    "requiere_accion": "SI",
                    "estado_alerta": "ABIERTA",
                    "responsable": "Operador"
                }))
        except Exception as e2:
            print(f"[WA ALERT ERROR] No se pudo registrar excepción en Sheets: {e2}", flush=True)

        return False

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
    "WHATSAPP_API_ERROR",
    "destino=CONDUCTOR",
    "WA EXCEPTION",
    "return False"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
