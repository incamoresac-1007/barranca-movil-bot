from pathlib import Path
import py_compile
import shutil
from datetime import datetime

BOT = Path("bot.py")
if not BOT.exists():
    raise SystemExit("ERROR: No encuentro bot.py")

text = BOT.read_text(encoding="utf-8")
backup = Path(f"bot_backup_encomienda_inteligente_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(BOT, backup)
original = text

start = text.find('        # Auto-detectar cantidad, tamaño y cuidado desde la descripcion')
end = text.find('        if auto_paquetes and auto_tamano:', start)

if start == -1 or end == -1:
    raise SystemExit("ERROR: No encontré el bloque de detección inteligente de encomienda")

new_detect = '''        # Auto-detectar cantidad, tamaño, peso y cuidado desde la descripcion
        import re as _re
        desc_l = texto.lower()

        auto_paquetes = None
        auto_tamano = None
        peso_kg = None
        peso_unitario_kg = None
        peso_total_kg = None
        productos_detectados = []

        def _paquetes_txt(n):
            return "1 paquete" if int(n) == 1 else f"{int(n)} paquetes"

        # Detectar productos especiales / conocidos
        es_gas = any(w in desc_l for w in [
            "balon de gas", "balón de gas", "balon gas", "balón gas",
            "gas lleno", "balon lleno", "balón lleno"
        ])

        es_bebida = any(w in desc_l for w in [
            "cerveza", "cervezas", "botella", "botellas",
            "bebida", "bebidas", "liquido", "líquido"
        ])

        if es_gas:
            productos_detectados.append("Balón de gas lleno" if "lleno" in desc_l else "Balón de gas")

        if es_bebida:
            if "caja" in desc_l or "cajas" in desc_l:
                productos_detectados.append("Caja de cervezas/bebidas")
            else:
                productos_detectados.append("Bebidas / líquidos")

        # Cantidad explicita: "2 cajas", "3 bolsas", etc.
        m_n = _re.search(
            r'\\b(\\d+)\\s*(balon|balones|balón|balones|costal|costales|paquete|paquetes|caja|cajas|bolsa|bolsas|bolson|bolsones|bulto|bultos|maleta|maletas|saco|sacos|silla|sillas|mesa|mesas|mueble|muebles)\\b',
            desc_l
        )
        if m_n:
            n = int(m_n.group(1))
            auto_paquetes = min(n, 4) if n <= 3 else 4

        # Cantidad por objetos singulares: "un balón ... y una caja ..."
        objetos_singulares = _re.findall(
            r'\\b(?:un|una|1)\\s+(balon|balón|caja|bolsa|paquete|bulto|maleta|saco|silla|mesa|mueble|costal)\\b',
            desc_l
        )
        if auto_paquetes is None and len(objetos_singulares) >= 2:
            auto_paquetes = min(len(objetos_singulares), 4)
        elif auto_paquetes is None and len(objetos_singulares) == 1:
            auto_paquetes = 1

        # Singular generico: "una silla", "un televisor", etc.
        if auto_paquetes is None and _re.search(r'\\b(un|una)\\s+\\w+', desc_l):
            auto_paquetes = 1

        # Si no hay cantidad pero la descripcion parece un objeto unico, asumir 1 y confirmar
        if auto_paquetes is None and any(w in desc_l for w in [
            "silla", "mesa", "televisor", "tv", "monitor", "cpu", "impresora",
            "mueble", "colchon", "bicicleta", "caja", "maleta", "mochila",
            "costal", "bolsa", "paquete", "balon", "balón"
        ]):
            auto_paquetes = 1

        # Peso: 20 kg, 20 kilos, 20 kilogramos
        m_kg = _re.search(r'(\\d+(?:[\\.,]\\d+)?)\\s*(kg|kilo|kilos|kilogramo|kilogramos)\\b', desc_l)
        if m_kg:
            peso_kg = float(m_kg.group(1).replace(",", "."))

            # Si el usuario dice "cada uno", "cada caja", "por cada", etc.,
            # interpretar el peso como unitario y calcular total.
            if auto_paquetes and auto_paquetes > 1 and any(x in desc_l for x in [
                "cada uno", "cada una", "cada caja", "cada paquete", "cada bulto", "por cada"
            ]):
                peso_unitario_kg = peso_kg
                peso_total_kg = peso_unitario_kg * auto_paquetes
            else:
                peso_total_kg = peso_kg

        # Tamaño por riesgo: gas lleno no debe tratarse como paquete normal
        if es_gas:
            auto_tamano = ("Carga especial / a coordinar", 4, True)

        # Tamaño por peso total
        if peso_total_kg is not None and not auto_tamano:
            if peso_total_kg < 2:
                auto_tamano = ("Paquete pequeño", 1, False)
            elif peso_total_kg <= 10:
                auto_tamano = ("Paquete mediano", 2, True)
            elif peso_total_kg <= 30:
                auto_tamano = ("Paquete grande", 3, True)
            else:
                auto_tamano = ("Carga pesada", 4, True)

        # Tamaño por palabras clave si no hubo peso ni riesgo
        if not auto_tamano:
            if any(w in desc_l for w in ["documento", "documentos", "sobre", "carta", "hoja"]):
                auto_tamano = ("Sobre/Documento", 1, False)
            elif any(w in desc_l for w in ["pequeño", "pequeno", "chico", "liviano"]):
                auto_tamano = ("Paquete pequeño", 1, False)
            elif any(w in desc_l for w in ["silla", "mesa", "mueble", "colchon", "bicicleta", "televisor", "tv", "grande"]):
                auto_tamano = ("Paquete grande", 3, True)
            elif any(w in desc_l for w in ["costal", "maleta", "bolson", "saco", "mochila", "caja", "cerveza", "cervezas", "botella", "botellas", "bebida", "bebidas", "liquido", "líquido"]):
                auto_tamano = ("Paquete mediano", 2, True)

        cuidado_msgs = []

        if es_gas:
            cuidado_msgs.append("AVISO: Balón de gas/carga riesgosa. El conductor debe confirmar si puede trasladarlo por seguridad.")

        if es_bebida:
            cuidado_msgs.append("AVISO: Requiere cuidado: frágil/líquido. Si son bebidas alcohólicas, debe entregar y recibir una persona mayor de edad.")

        cuidado_extra = "\\n".join(cuidado_msgs)
        if cuidado_extra:
            cuidado_extra += "\\n"

        productos_bloque = ""
        if len(productos_detectados) > 1:
            productos_bloque = "Productos detectados:\\n" + "\\n".join(
                [f"{i+1}. {p}" for i, p in enumerate(productos_detectados)]
            ) + "\\n"
        elif len(productos_detectados) == 1:
            productos_bloque = f"Producto detectado: {productos_detectados[0]}\\n"

'''
text = text[:start] + new_detect + text[end:]

old_msg = '''            peso_linea = f"⚖️ Peso aproximado: {peso_kg:g} kg\\n" if peso_kg is not None else ""
            sesion["estado"] = S_ENCOMIENDA_CONFIRM_AUTO
            await enviar_mensaje(numero,
                f"📦 *Detecté tu encomienda:*\\n\\n"
                f"Producto: {texto}\\n"
                f"Cantidad: {auto_paquetes} paquete(s)\\n"
                f"Tamaño estimado: {nombre_tam}\\n"
                f"{peso_linea}"
                f"{cuidado_extra}\\n"
                "¿Está correcto?\\n\\n"
'''

new_msg = '''            if peso_unitario_kg is not None and peso_total_kg is not None:
                peso_linea = f"⚖️ Peso: {peso_unitario_kg:g} kg por paquete / total aprox: {peso_total_kg:g} kg\\n"
            elif peso_total_kg is not None:
                peso_linea = f"⚖️ Peso aproximado: {peso_total_kg:g} kg\\n"
            else:
                peso_linea = ""

            paquetes_linea = _paquetes_txt(auto_paquetes)

            sesion["estado"] = S_ENCOMIENDA_CONFIRM_AUTO
            await enviar_mensaje(numero,
                f"📦 *Detecté tu encomienda:*\\n\\n"
                f"{productos_bloque}"
                f"Descripción: {texto}\\n"
                f"Cantidad: {paquetes_linea}\\n"
                f"Tamaño estimado: {nombre_tam}\\n"
                f"{peso_linea}"
                f"{cuidado_extra}\\n"
                "¿Está correcto?\\n\\n"
'''

if old_msg not in text:
    raise SystemExit("ERROR: No encontré el bloque del mensaje de detección automática")

text = text.replace(old_msg, new_msg, 1)

old_foto = '''                f"✅ *{datos.get('enc_paquetes', 1)} paquete(s) — {datos.get('enc_tamano', 'Encomienda')}*\\n\\n"
'''

new_foto = '''                f"✅ *{datos.get('enc_paquetes', 1)} {'paquete' if int(datos.get('enc_paquetes', 1)) == 1 else 'paquetes'} — {datos.get('enc_tamano', 'Encomienda')}*\\n\\n"
'''

if old_foto in text:
    text = text.replace(old_foto, new_foto, 1)

old_resumen = '''            f"🔢 {paquetes} paquete(s) | 📸 {foto_txt}\\n"
'''

new_resumen = '''            f"🔢 {paquetes} {'paquete' if int(paquetes) == 1 else 'paquetes'} | 📸 {foto_txt}\\n"
'''

if old_resumen in text:
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
for term in [
    "Carga especial / a coordinar",
    "peso_unitario_kg",
    "productos_detectados",
    "Balón de gas/carga riesgosa",
    "_paquetes_txt"
]:
    print(f"{term}: {'OK' if term in updated else 'NO ENCONTRADO'}")
