import json

import httpx

from tests.support.helpers import pay, place_order


def test_un_mismo_request_id_recorre_todos_los_servicios(stack):
    camila = stack.client("camila")
    stack.capture.lines.clear()
    r = place_order(camila, [(1, 1)])
    rid = r.headers["x-request-id"]
    eventos = [e for e in stack.capture.events() if e["request_id"] == rid]
    servicios = {e["service"] for e in eventos}
    assert {"api-gateway", "auth", "orders", "clients", "inventory"} <= servicios


def test_el_gateway_ignora_request_id_del_cliente(stack):
    camila = stack.client("camila")
    r = camila.get("/products", headers={"X-Request-Id": "inyectado-12345"})
    assert r.headers["x-request-id"] != "inyectado-12345"


def test_errores_incluyen_request_id(stack):
    r = httpx.get(f"{stack.urls['api-gateway']}/orders")
    assert r.json()["error"]["request_id"] == r.headers["x-request-id"]


def test_logs_estructurados_con_campos_minimos(stack):
    camila = stack.client("camila")
    pay(stack, camila, place_order(camila).json())
    for linea in stack.capture.lines:
        dato = json.loads(linea)
        assert {"ts", "level", "service", "request_id", "event"} <= set(dato)
    pagos = [e for e in stack.capture.events() if e["event"] == "webhook_processed"]
    assert pagos and pagos[0]["service"] == "payments"


def test_siembra_y_esquema_son_reproducibles(stack, tmp_path):
    from services.inventory.main import create_app
    from tests.support.helpers import db_of

    assert db_of(stack, "inventory").one("SELECT COUNT(*) AS n FROM products")["n"] == 12
    assert db_of(stack, "clients").one("SELECT COUNT(*) AS n FROM clients")["n"] == 2
    assert db_of(stack, "auth").one("SELECT COUNT(*) AS n FROM users")["n"] == 4
    stack.stop_service("inventory")
    stack.start_service("inventory")
    assert db_of(stack, "inventory").one("SELECT COUNT(*) AS n FROM products")["n"] == 12


def test_restricciones_de_base_de_datos_impiden_datos_invalidos(stack):
    import sqlite3

    import pytest

    from tests.support.helpers import db_of

    with pytest.raises(sqlite3.IntegrityError):
        with db_of(stack, "inventory").tx() as c:
            c.execute("UPDATE stock SET reserved = on_hand + 1 WHERE product_id = 1")
    with pytest.raises(sqlite3.IntegrityError):
        with db_of(stack, "orders").tx() as c:
            c.execute("INSERT INTO orders(id,client_id,status,total,created_at,updated_at) VALUES('X','C','inventado',1,'a','b')")
