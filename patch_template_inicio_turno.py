from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
text = BOT.read_text(encoding="utf-8")

backup = Path(f"bot_backup_template_inicio_turno_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)

func = r'''

async def enviar_template_inicio_turno(to: str):
    """
    Envía plantilla aprobada de WhatsApp para recordatorio de inicio de turno.
    Plantilla Meta: inicio_turno_conductor
    Idioma: Spanish (PER) => es_PE
    """
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": "inicio_turno_conductor",
            "language": {"code": "es_PE"}
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=payload)

        if r.status_code >= 400:
            print(f"[TEMPLATE ERROR] inicio_turno_conductor to={to} status={r.status_code} {r.text}", flush=True)
            return False

        print(f"[TEMPLATE] inicio_turno_conductor enviado to={to} status={r.status_code}", flush=True)
        return True

    except Exception as e:
        print(f"[TEMPLATE EXCEPTION] inicio_turno_conductor to={to} error={e}", flush=True)
        return False

'''

if "async def enviar_template_inicio_turno" in text:
    print("AVISO: la función enviar_template_inicio_turno ya existe. No se insertó otra vez.")
else:
    marker = "async def reenviar_imagen"
    pos = text.find(marker)
    if pos == -1:
        raise SystemExit("ERROR: No encontré async def reenviar_imagen para insertar antes.")
    text = text[:pos] + func + "\n" + text[pos:]

BOT.write_text(text, encoding="utf-8")

try:
    py_compile.compile(str(BOT), doraise=True)
    print(f"OK: bot.py compila. Backup creado: {backup}")
except Exception as e:
    shutil.copy2(backup, BOT)
    raise SystemExit(f"ERROR: bot.py no compila. Restaurado backup. {e}")

updated = BOT.read_text(encoding="utf-8")
print("enviar_template_inicio_turno:", "OK" if "async def enviar_template_inicio_turno" in updated else "NO")
print("inicio_turno_conductor:", "OK" if "inicio_turno_conductor" in updated else "NO")
print("es_PE:", "OK" if '"es_PE"' in updated else "NO")
