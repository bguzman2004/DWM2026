"""Reglas del pedido de El Mariachi y formato de sus mensajes en la cola STOMP.

Lo usan productor.py y consumidor.py: así el menú, el 2x1 y el formato de cada mensaje
quedan en un solo lugar y se pueden probar sin un broker.
"""
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

DESTINO = "/queue/mariachi.pedidos"
FORMATOS = ("texto", "fijo", "xml", "json")

PLATILLOS = {
    1: {"nombre": "Tacos al Pastor", "categoria": "Tacos", "precio": 2500},
    2: {"nombre": "Burrito Especial", "categoria": "Burritos", "precio": 4500},
    3: {"nombre": "Nachos Supreme", "categoria": "Nachos", "precio": 3500},
    4: {"nombre": "Quesadilla Mixta", "categoria": "Otros", "precio": 3200},
}

PROMO_2X1 = {1}
MAX_CANTIDAD = 20
MAX_ITEMS = 9

# Registro de ancho fijo: ID[6] CLIENTE[20] MONTO[10] ITEMS[1] y 4 caracteres por item (PLATILLO[2] CANTIDAD[2])
ANCHO_ID, ANCHO_CLIENTE, ANCHO_MONTO = 6, 20, 10
CABECERA_FIJA = ANCHO_ID + ANCHO_CLIENTE + ANCHO_MONTO + 1
MAX_CLIENTE = 60  # en JSON y XML
MONTO_MAXIMO = Decimal("9999999.99")  # lo más que cabe en 10 caracteres con 2 decimales
LARGO_MAXIMO = 2000  # caracteres por mensaje

MIME = {
    "texto": "text/plain; charset=utf-8",
    "fijo": "text/plain; charset=utf-8",
    "xml": "application/xml; charset=utf-8",
    "json": "application/json; charset=utf-8",
}


def consola_utf8():
    # Para que las tildes no den error cuando la salida se redirige a un archivo en Windows
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def validar_items(items):
    if not items:
        raise ValueError("El pedido debe tener al menos un platillo")
    if len(items) > MAX_ITEMS:
        raise ValueError(f"El pedido admite hasta {MAX_ITEMS} platillos distintos")
    vistos = set()
    for platillo, cantidad in items:
        if platillo not in PLATILLOS:
            raise ValueError(f"Platillo {platillo} no existe en el menu")
        if platillo in vistos:
            raise ValueError(f"Platillo {platillo} repetido: sume las cantidades en una sola linea")
        if not 1 <= cantidad <= MAX_CANTIDAD:
            raise ValueError(f"La cantidad de {PLATILLOS[platillo]['nombre']} debe estar entre 1 y {MAX_CANTIDAD}")
        vistos.add(platillo)


def unidades_cobradas(platillo, cantidad):
    if platillo in PROMO_2X1:
        return cantidad - cantidad // 2
    return cantidad


def calcular_total(items):
    validar_items(items)
    total = sum(PLATILLOS[p]["precio"] * unidades_cobradas(p, c) for p, c in items)
    return Decimal(total).quantize(Decimal("0.01"))


def pesos(monto):
    return "$" + f"{int(Decimal(monto)):,}".replace(",", ".")


def a_ascii(texto):
    """Pasa tildes y ñ a letras sin tilde (Matías Cañete -> Matias Canete)."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    if not sin_tildes.isascii():
        raise ValueError("En formato fijo el cliente solo puede tener letras, numeros y tildes")
    return sin_tildes


def validar_id(valor):
    texto = str(valor).strip()
    if not (texto.isascii() and texto.isdigit()) or len(texto) > ANCHO_ID:
        raise ValueError(f"El id debe tener entre 1 y {ANCHO_ID} digitos")
    return texto


def validar_cliente(valor, ancho):
    if not isinstance(valor, str):
        raise ValueError("El cliente debe ser texto")
    limpio = valor.strip()
    if not limpio:
        raise ValueError("El cliente no puede estar vacio")
    if len(limpio) > ancho:
        raise ValueError(f"El cliente admite hasta {ancho} caracteres (tiene {len(limpio)})")
    if any(unicodedata.category(c).startswith("C") for c in limpio):
        raise ValueError("El cliente no puede tener saltos de linea ni caracteres de control")
    return limpio


def validar_monto(valor):
    try:
        monto = Decimal(str(valor).strip())
    except InvalidOperation:
        raise ValueError(f"Monto no valido: {valor}") from None
    if not monto.is_finite():
        raise ValueError("El monto debe ser un numero finito")
    if monto < 0 or monto > MONTO_MAXIMO:
        raise ValueError(f"El monto debe estar entre 0 y {MONTO_MAXIMO}")
    if monto != monto.quantize(Decimal("0.01")):
        raise ValueError("El monto admite hasta 2 decimales")
    return abs(monto)


def construir_mensaje(formato: str, pedido: dict, texto: str) -> tuple[str, str]:
    """Devuelve (cuerpo, tipo MIME) del mensaje en el formato pedido."""
    if formato not in FORMATOS:
        raise ValueError(f"Formato desconocido: {formato}")
    if formato == "texto":
        mensaje = (texto or "").strip()
        if not mensaje:
            raise ValueError("El mensaje de texto no puede estar vacio")
        if len(mensaje) > LARGO_MAXIMO:
            raise ValueError(f"El mensaje admite hasta {LARGO_MAXIMO} caracteres")
        return mensaje, MIME["texto"]

    items = pedido["items"]
    validar_items(items)
    identificador = validar_id(pedido["id"])
    monto = validar_monto(pedido["monto"])
    if formato == "fijo":
        cliente = a_ascii(validar_cliente(pedido["cliente"], ANCHO_CLIENTE))
        detalle = "".join(f"{platillo:02d}{cantidad:02d}" for platillo, cantidad in items)
        registro = (f"{identificador.zfill(ANCHO_ID)}{cliente:<{ANCHO_CLIENTE}}"
                    f"{monto:010.2f}{len(items)}{detalle}")
        return registro, MIME["fijo"]
    datos = {
        "id": identificador,
        "cliente": validar_cliente(pedido["cliente"], MAX_CLIENTE),
        "items": [{"platillo": platillo, "cantidad": cantidad} for platillo, cantidad in items],
        "monto": str(pedido["monto"]),
    }
    if formato == "json":
        return json.dumps(datos, ensure_ascii=False), MIME["json"]
    raiz = ET.Element("pedido")
    for clave in ("id", "cliente", "monto"):
        ET.SubElement(raiz, clave).text = datos[clave]
    lista = ET.SubElement(raiz, "items")
    for item in datos["items"]:
        nodo = ET.SubElement(lista, "item")
        ET.SubElement(nodo, "platillo").text = str(item["platillo"])
        ET.SubElement(nodo, "cantidad").text = str(item["cantidad"])
    return ET.tostring(raiz, encoding="unicode"), MIME["xml"]


def _entero(valor, campo):
    if isinstance(valor, int) and not isinstance(valor, bool):
        return valor
    if isinstance(valor, str) and valor.strip().isascii() and valor.strip().isdigit():
        return int(valor.strip())
    raise ValueError(f"El {campo} debe ser un numero entero")


def a_pedido(identificador, cliente, items, monto):
    lineas = [(_entero(platillo, "platillo"), _entero(cantidad, "cantidad")) for platillo, cantidad in items]
    return {
        "id": validar_id(identificador),
        "cliente": validar_cliente(cliente, MAX_CLIENTE),
        "items": lineas,
        "monto": validar_monto(monto),
    }


def interpretar(cuerpo: str, headers: dict):
    """Lee un mensaje según su header x-formato (o su content-type) y devuelve (formato, contenido)."""
    if len(cuerpo) > LARGO_MAXIMO:
        raise ValueError(f"Mensaje demasiado largo (maximo {LARGO_MAXIMO} caracteres)")
    formato = headers.get("x-formato", "").lower()
    tipo_mime = headers.get("content-type", "").lower()
    if not formato:
        if "application/json" in tipo_mime:
            formato = "json"
        elif "application/xml" in tipo_mime or "text/xml" in tipo_mime:
            formato = "xml"
        else:
            formato = "texto"
    if formato == "texto":
        return formato, cuerpo
    if formato == "fijo":
        return formato, _desde_fijo(cuerpo)
    if formato == "json":
        return formato, _desde_json(cuerpo)
    if formato == "xml":
        return formato, _desde_xml(cuerpo)
    raise ValueError(f"Formato no soportado: {formato}")


def _desde_fijo(cuerpo):
    if not cuerpo.isascii():
        raise ValueError("Registro de ancho fijo no valido: solo admite caracteres ASCII")
    if len(cuerpo) < CABECERA_FIJA + 4 or not cuerpo[CABECERA_FIJA - 1].isdigit():
        raise ValueError(f"Registro de ancho fijo no valido: falta la cabecera de {CABECERA_FIJA} caracteres")
    cantidad_items = int(cuerpo[CABECERA_FIJA - 1])
    esperado = CABECERA_FIJA + 4 * cantidad_items
    if len(cuerpo) != esperado:
        raise ValueError(f"Registro de ancho fijo no valido: {len(cuerpo)} caracteres, se esperan {esperado}")
    identificador = cuerpo[0:6]
    cliente = cuerpo[6:26].rstrip()
    monto = cuerpo[26:36]
    detalle = cuerpo[CABECERA_FIJA:]
    if not (
        identificador.isdigit()
        and monto[:7].isdigit()
        and monto[7] == "."
        and monto[8:].isdigit()
        and detalle.isdigit()
    ):
        raise ValueError("Campos numericos de ancho fijo no validos")
    items = [(detalle[i : i + 2], detalle[i + 2 : i + 4]) for i in range(0, len(detalle), 4)]
    return a_pedido(identificador, cliente, items, monto)


def _desde_json(cuerpo):
    try:
        datos = json.loads(cuerpo)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"JSON no valido: {getattr(exc, 'msg', exc)}") from None
    if not isinstance(datos, dict):
        raise ValueError("El JSON debe ser un objeto con id, cliente, items y monto")
    faltan = [campo for campo in ("id", "cliente", "items", "monto") if campo not in datos]
    if faltan:
        raise ValueError("Faltan campos: " + ", ".join(faltan))
    if not isinstance(datos["items"], list):
        raise ValueError("items debe ser una lista")
    items = []
    for item in datos["items"]:
        if not isinstance(item, dict) or "platillo" not in item or "cantidad" not in item:
            raise ValueError("Cada item debe tener platillo y cantidad")
        items.append((item["platillo"], item["cantidad"]))
    return a_pedido(datos["id"], datos["cliente"], items, datos["monto"])


def _desde_xml(cuerpo):
    # Sin DOCTYPE ni ENTITY: evita los ataques de expansion de entidades
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", cuerpo, re.IGNORECASE):
        raise ValueError("El XML no puede tener DOCTYPE ni ENTITY")
    try:
        raiz = ET.fromstring(cuerpo)
    except ET.ParseError as exc:
        raise ValueError(f"XML no valido: {exc}") from None
    if raiz.tag != "pedido":
        raise ValueError("El nodo raiz de XML debe ser <pedido>")
    campos = {campo: raiz.findtext(campo) for campo in ("id", "cliente", "monto")}
    faltan = [campo for campo, valor in campos.items() if valor is None]
    if faltan:
        raise ValueError("Faltan campos: " + ", ".join(faltan))
    items = [(nodo.findtext("platillo"), nodo.findtext("cantidad")) for nodo in raiz.iter("item")]
    return a_pedido(campos["id"], campos["cliente"], items, campos["monto"])


def revisar_pedido(pedido):
    total = calcular_total(pedido["items"])
    if pedido["monto"] != total:
        raise ValueError(f"Monto {pesos(pedido['monto'])} no coincide con el menu: el total es {pesos(total)}")
    return total


def comanda(formato, pedido, total):
    lineas = [f"[COMANDA] pedido MRC-{pedido['id'].zfill(ANCHO_ID)} · {pedido['cliente']} · formato={formato}"]
    for platillo, cantidad in pedido["items"]:
        promo = " (2x1)" if platillo in PROMO_2X1 and cantidad >= 2 else ""
        lineas.append(f"  {cantidad} x {PLATILLOS[platillo]['nombre']}{promo}")
    lineas.append(f"  Total: {pesos(total)}")
    return "\n".join(lineas)
