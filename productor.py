import argparse
import json
import os
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

import stomp

DESTINO = "/queue/mariachi.pedidos"

PLATILLOS = {
    1: {"nombre": "Tacos al Pastor", "categoria": "Tacos", "precio": 2500},
    2: {"nombre": "Burrito Especial", "categoria": "Burritos", "precio": 4500},
    3: {"nombre": "Nachos Supreme", "categoria": "Nachos", "precio": 3500},
    4: {"nombre": "Quesadilla Mixta", "categoria": "Otros", "precio": 3200},
}

PROMO_2X1 = {1}
MAX_CANTIDAD = 20
MAX_ITEMS = 9


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
ITEMS_POR_DEFECTO = ["1:2", "4:1"]


def leer_item(texto):
    try:
        platillo, cantidad = texto.split(":")
        return int(platillo), int(cantidad)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Item no valido '{texto}': use PLATILLO:CANTIDAD, por ejemplo 1:2")


def construir_mensaje(formato: str, pedido: dict, texto: str) -> tuple[str, str]:
    if formato == "texto":
        return texto, "text/plain; charset=utf-8"
    items = pedido["items"]
    validar_items(items)
    if formato == "fijo":
        identificador = str(pedido["id"])
        cliente = str(pedido["cliente"])
        monto = Decimal(pedido["monto"])
        monto_campo = f"{monto:010.2f}"
        if not (identificador.isascii() and identificador.isdigit() and len(identificador) <= 6):
            raise ValueError("En formato fijo, --id debe tener hasta 6 digitos ASCII")
        if len(cliente) > 20 or not cliente.isascii():
            raise ValueError("En formato fijo, --cliente admite hasta 20 caracteres ASCII (sin tildes ni ñ)")
        if monto < 0 or len(monto_campo) != 10:
            raise ValueError("En formato fijo, --monto debe estar entre 0 y 9999999.99")
        detalle = "".join(f"{platillo:02d}{cantidad:02d}" for platillo, cantidad in items)
        return f"{identificador.zfill(6)}{cliente:<20}{monto_campo}{len(items)}{detalle}", "text/plain; charset=utf-8"
    datos = {
        "id": str(pedido["id"]),
        "cliente": pedido["cliente"],
        "items": [{"platillo": platillo, "cantidad": cantidad} for platillo, cantidad in items],
        "monto": str(pedido["monto"]),
    }
    if formato == "json":
        return json.dumps(datos, ensure_ascii=False), "application/json; charset=utf-8"
    if formato == "xml":
        raiz = ET.Element("pedido")
        for clave in ("id", "cliente", "monto"):
            ET.SubElement(raiz, clave).text = datos[clave]
        lista = ET.SubElement(raiz, "items")
        for item in datos["items"]:
            nodo = ET.SubElement(lista, "item")
            ET.SubElement(nodo, "platillo").text = str(item["platillo"])
            ET.SubElement(nodo, "cantidad").text = str(item["cantidad"])
        return ET.tostring(raiz, encoding="unicode"), "application/xml; charset=utf-8"
    raise ValueError(f"Formato desconocido: {formato}")


def main():
    parser = argparse.ArgumentParser(description="Productor STOMP de pedidos de El Mariachi")
    parser.add_argument("--formato", choices=["texto", "fijo", "xml", "json"], required=True)
    parser.add_argument("--mensaje", default="Hola desde El Mariachi")
    parser.add_argument("--id", default="482913", help="Numero de orden (MRC-######)")
    parser.add_argument("--cliente", default="Camila Rojas")
    parser.add_argument("--item", action="append", type=leer_item, help="PLATILLO:CANTIDAD, se puede repetir")
    parser.add_argument("--monto", default=None, help="Por defecto se calcula con el menu y el 2x1")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=61613)
    parser.add_argument("--usuario", default=os.getenv("STOMP_USUARIO", "demo"))
    parser.add_argument("--clave", default=os.getenv("STOMP_CLAVE"))
    args = parser.parse_args()

    if not args.clave:
        parser.error("Defina la variable STOMP_CLAVE o use --clave")
    items = args.item or [leer_item(texto) for texto in ITEMS_POR_DEFECTO]
    try:
        monto = calcular_total(items) if args.monto is None else Decimal(args.monto)
        if not monto.is_finite():
            raise ValueError("El monto debe ser un numero finito")
    except InvalidOperation:
        parser.error(f"Monto no valido: {args.monto}")
    except ValueError as exc:
        parser.error(str(exc))
    pedido = {"id": args.id, "cliente": args.cliente, "items": items, "monto": str(monto)}
    try:
        cuerpo, mime = construir_mensaje(args.formato, pedido, args.mensaje)
    except ValueError as exc:
        parser.error(str(exc))

    conexion = stomp.Connection12([(args.host, args.port)], vhost="/")
    try:
        conexion.connect(args.usuario, args.clave, wait=True)
        conexion.send(
            destination=DESTINO,
            body=cuerpo,
            headers={
                "content-type": mime,
                "x-formato": args.formato,
                "persistent": "true",
            },
        )
        print(f"Mensaje enviado a {DESTINO} (formato={args.formato}):\n{cuerpo}")
    finally:
        if conexion.is_connected():
            conexion.disconnect()


if __name__ == "__main__":
    main()
