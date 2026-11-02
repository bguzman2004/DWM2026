import argparse
import json
import os
import threading
import time
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


def a_pedido(identificador, cliente, items, monto):
    try:
        lineas = [(int(platillo), int(cantidad)) for platillo, cantidad in items]
        valor = Decimal(str(monto))
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError("Pedido con campos numericos no validos")
    if not valor.is_finite():
        raise ValueError("El monto debe ser un numero finito")
    return {"id": str(identificador), "cliente": str(cliente), "items": lineas, "monto": valor}


def interpretar(cuerpo: str, headers: dict):
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
        if len(cuerpo) < 41 or not cuerpo[36].isdigit():
            raise ValueError("Registro de ancho fijo no valido: falta la cabecera de 37 caracteres")
        cantidad_items = int(cuerpo[36])
        esperado = 37 + 4 * cantidad_items
        if len(cuerpo) != esperado:
            raise ValueError(f"Registro de ancho fijo no valido: {len(cuerpo)} caracteres, se esperan {esperado}")
        identificador = cuerpo[0:6]
        cliente = cuerpo[6:26].rstrip()
        monto = cuerpo[26:36]
        detalle = cuerpo[37:]
        if not (
            identificador.isascii()
            and identificador.isdigit()
            and monto[:7].isdigit()
            and monto[7] == "."
            and monto[8:].isdigit()
            and detalle.isascii()
            and detalle.isdigit()
        ):
            raise ValueError("Campos numericos de ancho fijo no validos")
        items = [(detalle[i : i + 2], detalle[i + 2 : i + 4]) for i in range(0, len(detalle), 4)]
        return formato, a_pedido(identificador, cliente, items, monto)
    if formato == "json":
        datos = json.loads(cuerpo)
        items = [(item["platillo"], item["cantidad"]) for item in datos["items"]]
        return formato, a_pedido(datos["id"], datos["cliente"], items, datos["monto"])
    if formato == "xml":
        raiz = ET.fromstring(cuerpo)
        if raiz.tag != "pedido":
            raise ValueError("El nodo raiz de XML debe ser <pedido>")
        items = [(nodo.findtext("platillo"), nodo.findtext("cantidad")) for nodo in raiz.iter("item")]
        return formato, a_pedido(raiz.findtext("id"), raiz.findtext("cliente"), items, raiz.findtext("monto"))
    raise ValueError(f"Formato no soportado: {formato}")


def revisar_pedido(pedido):
    total = calcular_total(pedido["items"])
    if pedido["monto"] != total:
        raise ValueError(f"Monto {pesos(pedido['monto'])} no coincide con el menu: el total es {pesos(total)}")
    return total


def comanda(formato, pedido, total):
    lineas = [f"[COMANDA] pedido MRC-{pedido['id']} · {pedido['cliente']} · formato={formato}"]
    for platillo, cantidad in pedido["items"]:
        promo = " (2x1)" if platillo in PROMO_2X1 and cantidad >= 2 else ""
        lineas.append(f"  {cantidad} x {PLATILLOS[platillo]['nombre']}{promo}")
    lineas.append(f"  Total: {pesos(total)}")
    return "\n".join(lineas)


class Escuchador(stomp.ConnectionListener):
    def __init__(self, conexion, limite=0):
        self.conexion = conexion
        self.limite = limite
        self.procesados = 0
        self.terminado = threading.Event()

    def on_error(self, frame):
        print(f"ERROR del broker: {frame.body}", flush=True)

    def on_disconnected(self):
        print("Conexion STOMP cerrada", flush=True)
        self.terminado.set()

    def on_message(self, frame):
        ack_id = frame.headers["ack"]
        try:
            formato, contenido = interpretar(frame.body, frame.headers)
            if isinstance(contenido, str):
                print(f"\n[AVISO] formato={formato}\n{contenido}", flush=True)
            else:
                total = revisar_pedido(contenido)
                print("\n" + comanda(formato, contenido, total), flush=True)
            self.conexion.ack(id=ack_id)
        except Exception as exc:
            print(f"\n[MENSAJE NO VALIDO] {exc}", flush=True)
            self.conexion.nack(id=ack_id, requeue="false")
        self.procesados += 1
        if self.limite and self.procesados >= self.limite:
            self.terminado.set()


def main():
    parser = argparse.ArgumentParser(description="Consumidor STOMP de la cocina de El Mariachi")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=61613)
    parser.add_argument("--usuario", default=os.getenv("STOMP_USUARIO", "demo"))
    parser.add_argument("--clave", default=os.getenv("STOMP_CLAVE"))
    parser.add_argument("--max-mensajes", type=int, default=0, help="Termina despues de N mensajes (0 = sin limite)")
    args = parser.parse_args()
    if not args.clave:
        parser.error("Defina la variable STOMP_CLAVE o use --clave")

    conexion = stomp.Connection12([(args.host, args.port)], vhost="/")
    escuchador = Escuchador(conexion, args.max_mensajes)
    conexion.set_listener("pedidos", escuchador)
    try:
        conexion.connect(args.usuario, args.clave, wait=True)
        conexion.subscribe(
            destination=DESTINO, id="cocina-mariachi",
            ack="client-individual", headers={"prefetch-count": "1"},
        )
        print(f"Cocina escuchando {DESTINO}. Presiona Ctrl+C para salir.", flush=True)
        while conexion.is_connected() and not escuchador.terminado.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nDeteniendo consumidor...")
    finally:
        if conexion.is_connected():
            conexion.disconnect()


if __name__ == "__main__":
    main()
