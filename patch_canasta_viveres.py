from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_canasta_viveres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

# 1) Agregar canasta/canastas/viveres/víveres a detección de cantidad explícita
text = text.replace(
    r'(balon|balones|balón|balones|costal|costales|paquete|paquetes|caja|cajas|bolsa|bolsas|bolson|bolsones|bulto|bultos|maleta|maletas|saco|sacos|silla|sillas|mesa|mesas|mueble|muebles)',
    r'(balon|balones|balón|balones|canasta|canastas|costal|costales|paquete|paquetes|caja|cajas|bolsa|bolsas|bolson|bolsones|bulto|bultos|maleta|maletas|saco|sacos|silla|sillas|mesa|mesas|mueble|muebles)'
)

# 2) Agregar canasta a objetos singulares: "una canasta ... y una caja ..."
text = text.replace(
    r'(balon|balón|caja|bolsa|paquete|bulto|maleta|saco|silla|mesa|mueble|costal)',
    r'(balon|balón|canasta|caja|bolsa|paquete|bulto|maleta|saco|silla|mesa|mueble|costal)'
)

# 3) Agregar canasta/viveres al listado de objetos conocidos
text = text.replace(
    '"costal", "bolsa", "paquete", "balon", "balón"',
    '"costal", "bolsa", "paquete", "canasta", "canastas", "viveres", "víveres", "balon", "balón"'
)

# 4) Detectar producto canasta/víveres para mostrarlo en el mensaje
old = '''        if es_bebida:
            if "caja" in desc_l or "cajas" in desc_l:
                productos_detectados.append("Caja de cervezas/bebidas")
            else:
                productos_detectados.append("Bebidas / líquidos")
'''

new = '''        if any(w in desc_l for w in ["canasta", "canastas", "viveres", "víveres"]):
            productos_detectados.append("Canasta de víveres")

        if es_bebida:
            if "caja" in desc_l or "cajas" in desc_l:
                productos_detectados.append("Caja de cervezas/bebidas")
            else:
                productos_detectados.append("Bebidas / líquidos")
'''

if old not in text:
    raise SystemExit("ERROR: No encontré bloque de productos_detectados para bebidas")

text = text.replace(old, new, 1)

# 5) Si hay varios productos detectados pero la cantidad quedó 1, corregirla.
old2 = '''        if auto_paquetes and auto_tamano:
            nombre_tam, equiv_pas, req_conf = auto_tamano
'''

new2 = '''        if auto_paquetes and len(productos_detectados) > auto_paquetes:
            auto_paquetes = min(len(productos_detectados), 4)

        if auto_paquetes and auto_tamano:
            nombre_tam, equiv_pas, req_conf = auto_tamano
'''

if old2 not in text:
    raise SystemExit("ERROR: No encontré bloque if auto_paquetes and auto_tamano")

text = text.replace(old2, new2, 1)

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
for term in ["Canasta de víveres", "canasta", "productos_detectados", "len(productos_detectados) > auto_paquetes"]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
