"""Broker STOMP mínimo para probar sin instalar ActiveMQ.

Solo sirve para pruebas locales: entiende lo que usan productor.py y consumidor.py
(CONNECT, SEND, SUBSCRIBE con ack client-individual, ACK, NACK y DISCONNECT), acepta
cualquier usuario y no guarda nada en disco.

    python broker_prueba.py            # escucha en 127.0.0.1:61613 (el puerto de STOMP)
"""
import argparse
import itertools
import re
import socketserver
import threading
from collections import deque

NUL = b"\x00"
ESCAPES = {"r": "\r", "n": "\n", "c": ":", "\\": "\\"}


def _desescapar(valor):
    return re.sub(r"\\(.)", lambda m: ESCAPES.get(m.group(1), m.group(0)), valor)


def _escapar(valor):
    return valor.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n").replace(":", "\\c")


class Conexion(socketserver.StreamRequestHandler):
    """Un cliente conectado: lee sus marcos (frames) y se los pasa al broker."""

    def setup(self):
        super().setup()
        self.suscripciones = {}
        self.envio = threading.Lock()

    def handle(self):
        broker = self.server.broker
        try:
            while True:
                marco = self.leer_marco()
                if marco is None or not broker.atender(self, *marco):
                    break
        except (OSError, ValueError):
            pass
        finally:
            broker.cerrar(self)

    def leer_marco(self):
        linea = b"\n"
        while linea in (b"\n", b"\r\n"):  # los saltos de línea sueltos son heart-beats
            linea = self.rfile.readline()
            if not linea:
                return None
        comando = linea.decode("utf-8").strip()
        headers = {}
        while True:
            linea = self.rfile.readline()
            if not linea:
                return None
            linea = linea.decode("utf-8").rstrip("\r\n")
            if not linea:
                break
            clave, _, valor = linea.partition(":")
            if comando not in ("CONNECT", "STOMP"):
                clave, valor = _desescapar(clave), _desescapar(valor)
            headers.setdefault(clave, valor)
        if "content-length" in headers:
            cuerpo = self.rfile.read(int(headers["content-length"]))
            self.rfile.read(1)  # el NUL del final
        else:
            cuerpo = bytearray()
            while True:
                byte = self.rfile.read(1)
                if not byte:
                    return None
                if byte == NUL:
                    break
                cuerpo += byte
        return comando, headers, bytes(cuerpo).decode("utf-8")

    def enviar(self, comando, headers=None, cuerpo=""):
        lineas = [comando] + [f"{_escapar(k)}:{_escapar(str(v))}" for k, v in (headers or {}).items()]
        datos = ("\n".join(lineas) + "\n\n" + cuerpo).encode("utf-8") + NUL
        with self.envio:
            try:
                self.wfile.write(datos)
                self.wfile.flush()
            except OSError:
                pass


class BrokerPrueba:
    def __init__(self, host="127.0.0.1", puerto=0):
        self.colas = {}  # destino -> mensajes esperando a un consumidor
        self.suscripciones = []
        self.recibidos = []  # todo lo que llegó por SEND
        self.confirmados = []  # mensajes con ACK
        self.rechazados = []  # mensajes con NACK (como una cola de mensajes muertos)
        self._ids = itertools.count(1)
        self._lock = threading.RLock()
        self._servidor = socketserver.ThreadingTCPServer((host, puerto), Conexion)
        self._servidor.daemon_threads = True
        self._servidor.broker = self
        self.puerto = self._servidor.server_address[1]

    def iniciar(self):
        threading.Thread(target=self._servidor.serve_forever, daemon=True).start()
        return self

    def detener(self):
        self._servidor.shutdown()
        self._servidor.server_close()

    def __enter__(self):
        return self.iniciar()

    def __exit__(self, *args):
        self.detener()

    def atender(self, con, comando, headers, cuerpo):
        """Procesa un marco. Devuelve False si hay que cerrar la conexión."""
        seguir = True
        if comando in ("CONNECT", "STOMP"):
            con.enviar("CONNECTED", {"version": "1.2", "heart-beat": "0,0", "server": "BrokerPrueba"})
        elif comando == "SEND":
            self._recibir(headers, cuerpo)
        elif comando == "SUBSCRIBE":
            self._suscribir(con, headers)
        elif comando in ("ACK", "NACK"):
            self._responder(headers.get("id"), comando == "ACK")
        elif comando == "DISCONNECT":
            seguir = False
        else:
            con.enviar("ERROR", {"message": f"Comando no soportado: {comando}"})
            return False
        if "receipt" in headers:
            con.enviar("RECEIPT", {"receipt-id": headers["receipt"]})
        return seguir

    def _recibir(self, headers, cuerpo):
        if "destination" not in headers:
            raise ValueError("SEND sin destination")
        destino = headers["destination"]
        propios = {k: v for k, v in headers.items()
                   if k not in ("destination", "receipt", "content-length", "transaction")}
        mensaje = {"destino": destino, "cuerpo": cuerpo, "headers": propios}
        with self._lock:
            self.recibidos.append(mensaje)
            self.colas.setdefault(destino, deque()).append(mensaje)
            self._entregar(destino)

    def _suscribir(self, con, headers):
        if "id" not in headers or "destination" not in headers:
            raise ValueError("SUBSCRIBE sin id o destination")
        suscripcion = {
            "con": con,
            "id": headers["id"],
            "destino": headers["destination"],
            "ack": headers.get("ack", "auto"),
            "prefetch": int(headers.get("prefetch-count") or 0) or None,
            "pendientes": {},  # id de mensaje -> mensaje entregado y sin ACK
        }
        with self._lock:
            con.suscripciones[suscripcion["id"]] = suscripcion
            self.suscripciones.append(suscripcion)
            self._entregar(suscripcion["destino"])

    def _responder(self, id_mensaje, confirmar):
        with self._lock:
            for suscripcion in self.suscripciones:
                mensaje = suscripcion["pendientes"].pop(id_mensaje, None)
                if mensaje is not None:
                    (self.confirmados if confirmar else self.rechazados).append(mensaje)
                    self._entregar(suscripcion["destino"])
                    return

    def _entregar(self, destino):
        """Reparte los mensajes de la cola respetando el prefetch de cada consumidor."""
        cola = self.colas.get(destino)
        suscriptores = [s for s in self.suscripciones if s["destino"] == destino]
        avanzo = True
        while cola and suscriptores and avanzo:
            avanzo = False
            for suscripcion in suscriptores:
                if not cola:
                    break
                con_ack = suscripcion["ack"] != "auto"
                if con_ack and suscripcion["prefetch"] and len(suscripcion["pendientes"]) >= suscripcion["prefetch"]:
                    continue
                mensaje = cola.popleft()
                id_mensaje = str(next(self._ids))
                headers = {
                    "subscription": suscripcion["id"],
                    "message-id": id_mensaje,
                    "destination": destino,
                    **mensaje["headers"],
                    "content-length": str(len(mensaje["cuerpo"].encode("utf-8"))),
                }
                if con_ack:
                    headers["ack"] = id_mensaje
                    suscripcion["pendientes"][id_mensaje] = mensaje
                else:
                    self.confirmados.append(mensaje)
                suscripcion["con"].enviar("MESSAGE", headers, mensaje["cuerpo"])
                avanzo = True

    def cerrar(self, con):
        """Si un consumidor se va sin confirmar, sus mensajes vuelven al principio de la cola."""
        with self._lock:
            for suscripcion in list(con.suscripciones.values()):
                self.suscripciones = [s for s in self.suscripciones if s is not suscripcion]
                cola = self.colas.setdefault(suscripcion["destino"], deque())
                for mensaje in reversed(list(suscripcion["pendientes"].values())):
                    cola.appendleft(mensaje)
                self._entregar(suscripcion["destino"])
            con.suscripciones.clear()


def main():
    parser = argparse.ArgumentParser(description="Broker STOMP de prueba (no es ActiveMQ)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=61613)
    args = parser.parse_args()
    broker = BrokerPrueba(args.host, args.port).iniciar()
    print(f"Broker de prueba escuchando en {args.host}:{broker.puerto}. Ctrl+C para salir.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nBroker detenido.")
        broker.detener()


if __name__ == "__main__":
    main()
