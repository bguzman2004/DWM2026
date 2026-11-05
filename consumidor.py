# Consumidor STOMP de la cocina de El Mariachi: escucha la cola, interpreta cada mensaje,
# imprime la comanda y lo confirma (ACK) o lo rechaza (NACK).
#
# La clave del broker va en la variable STOMP_CLAVE o en --clave.
#
# python consumidor.py
# python consumidor.py --max-mensajes 4 --espera 30    (para pruebas: termina solo)
import argparse
import os
import sys
import threading
import time

import stomp
from stomp.exception import StompException

from contrato import DESTINO, comanda, consola_utf8, interpretar, revisar_pedido


class Escuchador(stomp.ConnectionListener):
    def __init__(self, conexion, limite=0):
        self.conexion = conexion
        self.limite = limite
        self.procesados = 0
        self.ultimo = time.monotonic()  # cuando llego el ultimo mensaje
        self.terminado = threading.Event()

    def on_error(self, frame):
        print(f"ERROR del broker: {frame.body}", flush=True)

    def on_disconnected(self):
        print("Conexion STOMP cerrada", flush=True)
        self.terminado.set()

    def on_message(self, frame):
        ack_id = frame.headers.get("ack") or frame.headers.get("message-id")
        try:
            formato, contenido = interpretar(frame.body, frame.headers)
            if isinstance(contenido, str):
                print(f"\n[AVISO] formato={formato}\n{contenido}", flush=True)
            else:
                total = revisar_pedido(contenido)
                print("\n" + comanda(formato, contenido, total), flush=True)
        except Exception as exc:
            print(f"\n[MENSAJE NO VALIDO] {exc}", flush=True)
            self.conexion.nack(id=ack_id, requeue="false")
        else:
            self.conexion.ack(id=ack_id)
        finally:
            self.procesados += 1
            self.ultimo = time.monotonic()
            if self.limite and self.procesados >= self.limite:
                self.terminado.set()


def crear_parser():
    parser = argparse.ArgumentParser(description="Consumidor STOMP de la cocina de El Mariachi")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=61613)
    parser.add_argument("--usuario", default=os.getenv("STOMP_USUARIO", "demo"))
    parser.add_argument("--clave", default=os.getenv("STOMP_CLAVE"))
    parser.add_argument("--max-mensajes", type=int, default=0, help="Termina despues de N mensajes (0 = sin limite)")
    parser.add_argument("--espera", type=float, default=0, help="Termina si pasan S segundos sin mensajes (0 = sin limite)")
    return parser


def main(argv=None):
    consola_utf8()
    parser = crear_parser()
    args = parser.parse_args(argv)
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
            if args.espera and time.monotonic() - escuchador.ultimo > args.espera:
                print(f"Sin mensajes hace {args.espera:g} segundos, terminando.", flush=True)
                break
    except KeyboardInterrupt:
        print("\nDeteniendo consumidor...")
    except (StompException, OSError) as exc:
        print(f"No se pudo escuchar la cola: {exc}. "
              f"Esta andando el broker en {args.host}:{args.port}?", file=sys.stderr)
        return 1
    finally:
        if conexion.is_connected():
            conexion.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
