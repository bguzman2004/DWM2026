# Productor STOMP de El Mariachi: arma un pedido (o un texto) y lo deja en la cola.
#
# La clave del broker va en la variable STOMP_CLAVE o en --clave.
#
# Texto libre
# python productor.py --formato texto --mensaje "Mesa 4 pide la cuenta"
# Texto de ancho fijo
# python productor.py --formato fijo --id 482913 --cliente "Camila Rojas" --item 1:2 --item 4:1
# XML
# python productor.py --formato xml --id 482913 --cliente "Camila Rojas" --item 1:2 --item 4:1
# JSON
# python productor.py --formato json --id 482913 --cliente "Camila Rojas" --item 1:2 --item 4:1
import argparse
import os
import sys

import stomp
from stomp.exception import StompException

from contrato import DESTINO, FORMATOS, calcular_total, consola_utf8, construir_mensaje, validar_monto

ITEMS_POR_DEFECTO = ["1:2", "4:1"]


def leer_item(texto):
    try:
        platillo, cantidad = texto.split(":")
        return int(platillo), int(cantidad)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Item no valido '{texto}': use PLATILLO:CANTIDAD, por ejemplo 1:2")


def crear_parser():
    parser = argparse.ArgumentParser(description="Productor STOMP de pedidos de El Mariachi")
    parser.add_argument("--formato", choices=FORMATOS, required=True)
    parser.add_argument("--mensaje", default="Hola desde El Mariachi")
    parser.add_argument("--id", default="482913", help="Numero de orden (MRC-######)")
    parser.add_argument("--cliente", default="Camila Rojas")
    parser.add_argument("--item", action="append", type=leer_item, help="PLATILLO:CANTIDAD, se puede repetir")
    parser.add_argument("--monto", default=None, help="Por defecto se calcula con el menu y el 2x1")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=61613)
    parser.add_argument("--usuario", default=os.getenv("STOMP_USUARIO", "demo"))
    parser.add_argument("--clave", default=os.getenv("STOMP_CLAVE"))
    return parser


def main(argv=None):
    consola_utf8()
    parser = crear_parser()
    args = parser.parse_args(argv)

    if not args.clave:
        parser.error("Defina la variable STOMP_CLAVE o use --clave")
    items = args.item or [leer_item(texto) for texto in ITEMS_POR_DEFECTO]
    try:
        monto = calcular_total(items) if args.monto is None else validar_monto(args.monto)
        pedido = {"id": args.id, "cliente": args.cliente, "items": items, "monto": str(monto)}
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
    except (StompException, OSError) as exc:
        print(f"No se pudo enviar el mensaje: {exc}. "
              f"Esta andando el broker en {args.host}:{args.port}?", file=sys.stderr)
        return 1
    finally:
        if conexion.is_connected():
            conexion.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
