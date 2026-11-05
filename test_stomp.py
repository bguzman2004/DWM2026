"""Pruebas de la mensajeria STOMP: las reglas del pedido, el formato de los mensajes y el
recorrido completo productor -> broker de prueba -> consumidor. No necesitan ActiveMQ.

    pip install -r requirements.txt
    pytest -q
"""
import json
import socket
import time
from decimal import Decimal

import pytest

from contrato import (
    calcular_total, comanda, construir_mensaje, interpretar, pesos, revisar_pedido, validar_items,
)

PEDIDO = {"id": "482913", "cliente": "Camila Rojas", "items": [(1, 2), (4, 1)], "monto": "5700.00"}
LEIDO = {"id": "482913", "cliente": "Camila Rojas", "items": [(1, 2), (4, 1)], "monto": Decimal("5700.00")}

MENSAJES = {
    "fijo": "482913" + "Camila Rojas".ljust(20) + "0005700.00" + "2" + "01020401",
    "json": '{"id": "482913", "cliente": "Camila Rojas", "items": [{"platillo": 1, "cantidad": 2}, '
            '{"platillo": 4, "cantidad": 1}], "monto": "5700.00"}',
    "xml": "<pedido><id>482913</id><cliente>Camila Rojas</cliente><monto>5700.00</monto><items>"
           "<item><platillo>1</platillo><cantidad>2</cantidad></item>"
           "<item><platillo>4</platillo><cantidad>1</cantidad></item></items></pedido>",
}


def leer(cuerpo, formato):
    """Interpreta el mensaje y, si es un pedido, lo revisa contra el menu (como el consumidor)."""
    _, contenido = interpretar(cuerpo, {"x-formato": formato})
    return revisar_pedido(contenido) if isinstance(contenido, dict) else contenido


def json_con(**cambios):
    datos = {"id": "482913", "cliente": "Camila Rojas",
             "items": [{"platillo": 1, "cantidad": 2}, {"platillo": 4, "cantidad": 1}], "monto": "5700.00"}
    datos.update(cambios)
    return json.dumps(datos)


# ---------- menu y total ----------

@pytest.mark.parametrize("items, total", [
    ([(1, 1)], "2500.00"), ([(1, 2)], "2500.00"), ([(1, 3)], "5000.00"), ([(1, 4)], "5000.00"),
    ([(2, 2)], "9000.00"), ([(1, 2), (4, 1)], "5700.00"), ([(3, 1), (2, 1), (4, 1)], "11200.00"),
])
def test_el_total_sale_del_menu_con_el_2x1(items, total):
    assert calcular_total(items) == Decimal(total)


def test_pesos_con_punto_de_miles():
    assert pesos(Decimal("5700.00")) == "$5.700"
    assert pesos("1234567") == "$1.234.567"
    assert pesos(0) == "$0"


@pytest.mark.parametrize("items", [
    [], [(1, 1)] * 10, [(9, 1)], [(1, 1), (1, 2)], [(1, 0)], [(1, 21)], [(2, -1)],
])
def test_items_invalidos(items):
    with pytest.raises(ValueError):
        validar_items(items)


# ---------- mensajes ----------

@pytest.mark.parametrize("formato", ["fijo", "json", "xml"])
def test_el_mensaje_es_exactamente_el_del_contrato(formato):
    cuerpo, _ = construir_mensaje(formato, PEDIDO, "")
    assert cuerpo == MENSAJES[formato]


@pytest.mark.parametrize("formato", ["fijo", "json", "xml"])
def test_cada_formato_se_arma_y_se_vuelve_a_leer_igual(formato):
    cuerpo, mime = construir_mensaje(formato, PEDIDO, "")
    assert interpretar(cuerpo, {"x-formato": formato, "content-type": mime}) == (formato, LEIDO)


def test_el_registro_de_ancho_fijo_tiene_el_largo_de_su_cabecera_mas_4_por_item():
    cuerpo, _ = construir_mensaje("fijo", PEDIDO, "")
    assert len(cuerpo) == 37 + 4 * 2
    cuerpo, _ = construir_mensaje("fijo", {**PEDIDO, "items": [(1, 1)], "monto": "2500.00"}, "")
    assert len(cuerpo) == 37 + 4


def test_el_texto_viaja_tal_cual_y_no_es_un_pedido():
    cuerpo, mime = construir_mensaje("texto", PEDIDO, "  Mesa 4 pide la cuenta ")
    assert cuerpo == "Mesa 4 pide la cuenta"
    assert interpretar(cuerpo, {"x-formato": "texto", "content-type": mime}) == ("texto", cuerpo)


def test_sin_x_formato_se_usa_el_content_type_y_si_no_hay_es_texto():
    assert interpretar(MENSAJES["json"], {"content-type": "application/json; charset=utf-8"}) == ("json", LEIDO)
    assert interpretar(MENSAJES["xml"], {"content-type": "text/xml"}) == ("xml", LEIDO)
    assert interpretar("hola", {}) == ("texto", "hola")


def test_texto_vacio_o_gigante_y_formatos_que_no_existen():
    with pytest.raises(ValueError):
        construir_mensaje("texto", PEDIDO, "   ")
    with pytest.raises(ValueError):
        construir_mensaje("texto", PEDIDO, "a" * 2001)
    with pytest.raises(ValueError, match="demasiado largo"):
        interpretar("a" * 2001, {"x-formato": "texto"})
    with pytest.raises(ValueError, match="desconocido"):
        construir_mensaje("yaml", PEDIDO, "")
    with pytest.raises(ValueError, match="no soportado"):
        interpretar("x", {"x-formato": "yaml"})


# ---------- cliente, id y monto ----------

def test_ancho_fijo_pasa_tildes_y_enie_a_letras_sin_tilde():
    pedido = {**PEDIDO, "cliente": "Matías Cañete"}
    cuerpo, _ = construir_mensaje("fijo", pedido, "")
    assert cuerpo[6:26].rstrip() == "Matias Canete"
    assert leer(cuerpo, "fijo") == calcular_total(pedido["items"])


@pytest.mark.parametrize("formato", ["json", "xml"])
def test_json_y_xml_conservan_las_tildes(formato):
    cuerpo, mime = construir_mensaje(formato, {**PEDIDO, "cliente": "Matías Cañete"}, "")
    assert interpretar(cuerpo, {"x-formato": formato})[1]["cliente"] == "Matías Cañete"


def test_el_xml_escapa_los_caracteres_especiales():
    cuerpo, _ = construir_mensaje("xml", {**PEDIDO, "cliente": "Ana <b> & Co"}, "")
    assert "<b>" not in cuerpo
    assert interpretar(cuerpo, {"x-formato": "xml"})[1]["cliente"] == "Ana <b> & Co"


def test_largo_del_cliente_segun_el_formato():
    largo = "x" * 21
    with pytest.raises(ValueError, match="hasta 20"):
        construir_mensaje("fijo", {**PEDIDO, "cliente": largo}, "")
    assert interpretar(construir_mensaje("json", {**PEDIDO, "cliente": largo}, "")[0], {"x-formato": "json"})
    with pytest.raises(ValueError, match="hasta 60"):
        construir_mensaje("json", {**PEDIDO, "cliente": "x" * 61}, "")


@pytest.mark.parametrize("cliente", ["", "   ", "Camila\nRojas", "Camila\x1b[31m", 5, None])
def test_cliente_invalido(cliente):
    for formato in ("fijo", "json", "xml"):
        with pytest.raises(ValueError):
            construir_mensaje(formato, {**PEDIDO, "cliente": cliente}, "")


def test_ancho_fijo_no_acepta_lo_que_no_se_puede_pasar_a_ascii():
    with pytest.raises(ValueError, match="En formato fijo"):
        construir_mensaje("fijo", {**PEDIDO, "cliente": "Camila 🌮"}, "")


@pytest.mark.parametrize("id_pedido", ["", "abc", "1234567", "12.5", "-1", " ", True, None, "١٢٣"])
def test_id_invalido(id_pedido):
    with pytest.raises(ValueError, match="id"):
        construir_mensaje("json", {**PEDIDO, "id": id_pedido}, "")


@pytest.mark.parametrize("id_pedido, esperado", [("1", "000001"), ("000123", "000123"), (482913, "482913")])
def test_el_id_se_rellena_con_ceros_en_el_registro_y_en_la_comanda(id_pedido, esperado):
    cuerpo, _ = construir_mensaje("fijo", {**PEDIDO, "id": id_pedido}, "")
    assert cuerpo[:6] == esperado
    pedido = interpretar(cuerpo, {"x-formato": "fijo"})[1]
    assert f"MRC-{esperado} " in comanda("fijo", pedido, calcular_total(pedido["items"]))


@pytest.mark.parametrize("monto", ["abc", "-1", "NaN", "Infinity", "1e400", "10000000", "2500.555", "", None])
def test_monto_invalido(monto):
    for formato in ("fijo", "json", "xml"):
        with pytest.raises(ValueError):
            construir_mensaje(formato, {**PEDIDO, "monto": monto}, "")


@pytest.mark.parametrize("monto, registro", [
    ("2500", "0002500.00"), ("2500.5", "0002500.50"), (1234, "0001234.00"),
    ("0", "0000000.00"), ("-0", "0000000.00"), ("9999999.99", "9999999.99"),
])
def test_monto_valido_en_ancho_fijo(monto, registro):
    cuerpo, _ = construir_mensaje("fijo", {**PEDIDO, "monto": monto}, "")
    assert cuerpo[26:36] == registro


# ---------- el consumidor revisa el total contra el menu ----------

def test_la_comanda():
    assert comanda("json", LEIDO, calcular_total(LEIDO["items"])) == (
        "[COMANDA] pedido MRC-482913 · Camila Rojas · formato=json\n"
        "  2 x Tacos al Pastor (2x1)\n"
        "  1 x Quesadilla Mixta\n"
        "  Total: $5.700"
    )


def test_un_total_que_no_es_el_del_menu_se_rechaza():
    pedido = {**LEIDO, "monto": Decimal("100.00")}
    with pytest.raises(ValueError, match=r"no coincide con el menu: el total es \$5\.700"):
        revisar_pedido(pedido)
    assert revisar_pedido(LEIDO) == Decimal("5700.00")


# ---------- mensajes mal armados ----------

FIJO = MENSAJES["fijo"]


@pytest.mark.parametrize("cuerpo", [
    "",
    FIJO[:-1],
    FIJO + "0",
    "48291A" + FIJO[6:],
    FIJO[:26] + "00057a0.00" + FIJO[36:],
    FIJO[:26] + "0005700,00" + FIJO[36:],
    FIJO[:36] + "0" + FIJO[37:],
    FIJO[:36] + "x" + FIJO[37:],
    FIJO.replace("Camila", "Camilá"),
    "482913" + " " * 20 + FIJO[26:],
    FIJO[:37] + "99020401",
    FIJO[:37] + "01020000",
    FIJO[:37] + "01030401",
    FIJO[:26] + "0000100.00" + FIJO[36:],
])
def test_registro_de_ancho_fijo_mal_armado(cuerpo):
    with pytest.raises(ValueError):
        leer(cuerpo, "fijo")


@pytest.mark.parametrize("cuerpo", [
    "no es json", "[]", "null", '"482913"', '{"id": "1"}', "[" * 1500,
    json_con(items="x"), json_con(items=[1]), json_con(items=[{"platillo": 1}]), json_con(items=[]),
    json_con(items=[{"platillo": 1.9, "cantidad": 2}]), json_con(items=[{"platillo": 1, "cantidad": True}]),
    json_con(items=[{"platillo": 9, "cantidad": 1}]), json_con(items=[{"platillo": 1, "cantidad": 0}]),
    json_con(items=[{"platillo": "uno", "cantidad": 1}]),
    json_con(monto="abc"), json_con(monto="NaN"), json_con(monto="5700.001"), json_con(monto="100"),
    json_con(id="abc"), json_con(id="1234567"), json_con(id=None), json_con(cliente=5), json_con(cliente=""),
])
def test_json_mal_armado(cuerpo):
    with pytest.raises(ValueError):
        leer(cuerpo, "json")


@pytest.mark.parametrize("cuerpo", [
    "<pedido><id>482913</id>",
    "<orden><id>482913</id></orden>",
    MENSAJES["xml"].replace("<monto>5700.00</monto>", ""),
    MENSAJES["xml"].replace("<cantidad>2</cantidad>", ""),
    MENSAJES["xml"].replace("<cantidad>2</cantidad>", "<cantidad>dos</cantidad>"),
    MENSAJES["xml"].replace("<monto>5700.00</monto>", "<monto>100</monto>"),
    "<pedido><id>482913</id><cliente>Camila Rojas</cliente><monto>5700.00</monto></pedido>",
    '<!DOCTYPE pedido [<!ENTITY a "x">]>' + MENSAJES["xml"].replace("Camila Rojas", "&a;"),
])
def test_xml_mal_armado(cuerpo):
    with pytest.raises(ValueError):
        leer(cuerpo, "xml")


# ---------- recorrido completo con el broker de prueba ----------

class Entorno:
    """Un broker de prueba y los comandos para usar el productor y el consumidor contra el."""

    def __init__(self, broker, productor, consumidor, stomp):
        self.broker, self.productor, self.consumidor, self.stomp = broker, productor, consumidor, stomp

    def enviar(self, *args):
        assert self.productor.main([*args, "--port", str(self.broker.puerto), "--clave", "demo123"]) == 0

    def enviar_crudo(self, cuerpo, formato, mime="text/plain; charset=utf-8"):
        """Deja en la cola un mensaje sin pasar por las validaciones del productor."""
        conexion = self.stomp.Connection12([("127.0.0.1", self.broker.puerto)], vhost="/")
        conexion.connect("demo", "demo123", wait=True)
        conexion.send(destination="/queue/mariachi.pedidos", body=cuerpo,
                      headers={"content-type": mime, "x-formato": formato})
        conexion.disconnect()

    def consumir(self, cantidad=1):
        assert self.consumidor.main([
            "--port", str(self.broker.puerto), "--clave", "demo123",
            "--max-mensajes", str(cantidad), "--espera", "10",
        ]) == 0

    def esperar(self, condicion, segundos=5):
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            if condicion():
                return
            time.sleep(0.05)
        raise AssertionError("el broker no registro lo esperado a tiempo")


@pytest.fixture
def entorno(monkeypatch):
    stomp = pytest.importorskip("stomp")
    import consumidor
    import productor
    from broker_prueba import BrokerPrueba

    monkeypatch.delenv("STOMP_CLAVE", raising=False)
    with BrokerPrueba() as broker:
        yield Entorno(broker, productor, consumidor, stomp)


@pytest.mark.parametrize("formato", ["fijo", "xml", "json"])
def test_un_pedido_viaja_por_la_cola_en_cada_formato(entorno, capsys, formato):
    entorno.enviar("--formato", formato)
    capsys.readouterr()
    entorno.consumir()
    salida = capsys.readouterr().out
    assert "Cocina escuchando /queue/mariachi.pedidos. Presiona Ctrl+C para salir.\n" in salida
    assert (
        f"\n[COMANDA] pedido MRC-482913 · Camila Rojas · formato={formato}\n"
        "  2 x Tacos al Pastor (2x1)\n"
        "  1 x Quesadilla Mixta\n"
        "  Total: $5.700\n"
    ) in salida
    entorno.esperar(lambda: len(entorno.broker.confirmados) == 1)
    assert entorno.broker.rechazados == []


def test_el_pedido_con_items_y_cliente_propios(entorno, capsys):
    entorno.enviar("--formato", "json", "--id", "77", "--cliente", "Matías Cañete",
                   "--item", "2:1", "--item", "3:2", "--item", "1:3")
    capsys.readouterr()
    entorno.consumir()
    salida = capsys.readouterr().out
    assert "[COMANDA] pedido MRC-000077 · Matías Cañete · formato=json" in salida
    assert "  3 x Tacos al Pastor (2x1)" in salida
    assert "  Total: $16.500" in salida  # 4500 + 2*3500 + 2*2500


def test_el_mensaje_de_texto_es_solo_un_aviso(entorno, capsys):
    entorno.enviar("--formato", "texto", "--mensaje", "Mesa 4 pide la cuenta")
    capsys.readouterr()
    entorno.consumir()
    assert "[AVISO] formato=texto\nMesa 4 pide la cuenta" in capsys.readouterr().out
    entorno.esperar(lambda: len(entorno.broker.confirmados) == 1)


def test_un_total_alterado_se_rechaza_con_nack(entorno, capsys):
    entorno.enviar("--formato", "json", "--monto", "100")
    capsys.readouterr()
    entorno.consumir()
    assert "[MENSAJE NO VALIDO] Monto $100 no coincide con el menu: el total es $5.700" in capsys.readouterr().out
    entorno.esperar(lambda: len(entorno.broker.rechazados) == 1)
    assert entorno.broker.confirmados == []


def test_los_pedidos_llegan_de_a_uno_y_en_orden(entorno, capsys):
    for id_pedido, formato in (("1001", "json"), ("1002", "fijo"), ("1003", "xml")):
        entorno.enviar("--formato", formato, "--id", id_pedido)
    capsys.readouterr()
    entorno.consumir(3)
    salida = capsys.readouterr().out
    assert salida.index("MRC-001001") < salida.index("MRC-001002") < salida.index("MRC-001003")
    entorno.esperar(lambda: len(entorno.broker.confirmados) == 3)


def test_un_mensaje_invalido_se_rechaza_y_la_cola_sigue(entorno, capsys):
    entorno.enviar_crudo("000123corto", "fijo")
    entorno.enviar("--formato", "json")
    capsys.readouterr()
    entorno.consumir(2)
    salida = capsys.readouterr().out
    assert "[MENSAJE NO VALIDO] Registro de ancho fijo no valido" in salida
    assert "[COMANDA] pedido MRC-482913" in salida
    entorno.esperar(lambda: len(entorno.broker.rechazados) == 1 and len(entorno.broker.confirmados) == 1)
    assert entorno.broker.rechazados[0]["cuerpo"] == "000123corto"


def test_un_mensaje_sin_confirmar_vuelve_a_la_cola(entorno, capsys):
    entorno.enviar("--formato", "json")
    conexion = entorno.stomp.Connection12([("127.0.0.1", entorno.broker.puerto)], vhost="/")
    conexion.connect("demo", "demo123", wait=True)
    conexion.subscribe(destination="/queue/mariachi.pedidos", id="x", ack="client-individual")
    entorno.esperar(lambda: any(s["pendientes"] for s in entorno.broker.suscripciones))
    conexion.disconnect()  # se va sin hacer ACK
    entorno.esperar(lambda: len(entorno.broker.colas["/queue/mariachi.pedidos"]) == 1)
    capsys.readouterr()
    entorno.consumir()
    assert "[COMANDA] pedido MRC-482913" in capsys.readouterr().out


def test_sin_mensajes_el_consumidor_termina_por_espera(entorno, capsys):
    assert entorno.consumidor.main(["--port", str(entorno.broker.puerto), "--clave", "demo123", "--espera", "1"]) == 0
    assert "Sin mensajes hace 1 segundos, terminando." in capsys.readouterr().out


@pytest.mark.parametrize("malos", [
    ["--monto", "abc"], ["--monto", "2500.555"], ["--id", "1234567"], ["--cliente", "x" * 21],
    ["--item", "9:1"], ["--item", "1:0"], ["--item", "1:1", "--item", "1:2"], ["--item", "uno"],
])
def test_el_productor_rechaza_datos_malos_antes_de_conectarse(entorno, capsys, malos):
    with pytest.raises(SystemExit) as salida:
        entorno.productor.main(["--formato", "fijo", *malos, "--port", str(entorno.broker.puerto), "--clave", "x"])
    assert salida.value.code == 2
    assert "usage:" in capsys.readouterr().err
    assert entorno.broker.recibidos == []


def test_sin_clave_los_dos_programas_avisan(entorno, capsys):
    for programa in (entorno.productor, entorno.consumidor):
        argv = ["--formato", "json"] if programa is entorno.productor else []
        with pytest.raises(SystemExit) as salida:
            programa.main([*argv, "--port", str(entorno.broker.puerto)])
        assert salida.value.code == 2
    assert "STOMP_CLAVE" in capsys.readouterr().err


def test_la_clave_tambien_se_puede_dar_por_variable_de_entorno(entorno, monkeypatch):
    monkeypatch.setenv("STOMP_CLAVE", "demo123")
    assert entorno.productor.main(["--formato", "json", "--port", str(entorno.broker.puerto)]) == 0


def test_sin_broker_el_productor_y_el_consumidor_avisan(entorno, capsys):
    with socket.socket() as libre:
        libre.bind(("127.0.0.1", 0))
        puerto = str(libre.getsockname()[1])
    assert entorno.productor.main(["--formato", "json", "--port", puerto, "--clave", "x"]) == 1
    assert entorno.consumidor.main(["--port", puerto, "--clave", "x"]) == 1
    assert "Esta andando el broker" in capsys.readouterr().err
