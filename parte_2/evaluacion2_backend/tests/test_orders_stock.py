import threading

import httpx

from tests.support.helpers import db_of, items_payload, pay, place_order, stock_of


def test_orden_reserva_stock_y_calcula_total_en_servidor(stack):
    camila = stack.client("camila")
    r = camila.post("/orders", json={"items": [{"product_id": 1, "qty": 2, "price": 1}], "total": 1})
    assert r.status_code == 201
    assert (r.json()["subtotal"], r.json()["discount"], r.json()["total"]) == (5000, 2500, 2500)
    assert r.json()["items"][0]["unit_price"] == 2500
    assert stock_of(stack, 1) == (50, 2)


def test_no_se_puede_vender_mas_de_lo_que_hay(stack):
    camila = stack.client("camila")
    assert place_order(camila, [(7, 20)]).status_code == 201
    assert place_order(camila, [(7, 10)]).status_code == 201
    r = place_order(camila, [(7, 1)])
    assert r.status_code == 409
    assert "Stock insuficiente" in r.json()["error"]["message"]
    assert stock_of(stack, 7) == (30, 30)
    assert db_of(stack, "orders").one("SELECT COUNT(*) AS n FROM orders")["n"] == 2


def test_orden_con_un_item_sin_stock_no_reserva_ninguno(stack):
    camila = stack.client("camila")
    r = place_order(camila, [(1, 5), (7, 20), (7, 11)])
    assert r.status_code == 409
    assert stock_of(stack, 1) == (50, 0)


def test_concurrencia_no_genera_sobreventa(stack):
    clientes = [stack.client("camila" if i % 2 else "matias") for i in range(10)]
    resultados = []

    def comprar(c):
        resultados.append(place_order(c, [(7, 5)]).status_code)

    hilos = [threading.Thread(target=comprar, args=(c,)) for c in clientes]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert sorted(resultados).count(201) == 6
    assert sorted(resultados).count(409) == 4
    assert stock_of(stack, 7) == (30, 30)


def test_idempotencia_al_crear_orden(stack):
    camila = stack.client("camila")
    a = place_order(camila, [(1, 2)], key="clave-orden-0001")
    b = place_order(camila, [(1, 2)], key="clave-orden-0001")
    assert a.status_code == 201 and b.status_code == 200
    assert a.json()["id"] == b.json()["id"]
    assert stock_of(stack, 1) == (50, 2)


def test_cancelar_libera_el_stock(stack):
    camila = stack.client("camila")
    orden = place_order(camila, [(4, 4)]).json()
    assert stock_of(stack, 4) == (40, 4)
    r = camila.post(f"/orders/{orden['id']}/cancel")
    assert r.status_code == 200 and r.json()["stock_released"] is True
    assert stock_of(stack, 4) == (40, 0)
    assert camila.post(f"/orders/{orden['id']}/cancel").status_code == 409


def test_expirar_ordenes_pendientes_recupera_stock(stack):
    camila, admin = stack.client("camila"), stack.client("benjamin")
    a = place_order(camila, [(1, 3)]).json()
    b = place_order(camila, [(2, 2)]).json()
    pagada, _ = pay(stack, camila, b)
    r = admin.post("/orders/expire-pending", params={"older_than_seconds": 0})
    assert r.json()["expired"] == [a["id"]]
    assert stock_of(stack, 1) == (50, 0)
    assert stock_of(stack, 2) == (50, 2)
    assert admin.get(f"/orders/{a['id']}").json()["status"] == "expirado"
    assert admin.get(f"/orders/{b['id']}").json()["status"] == "pagado"


def test_no_se_expira_lo_reciente(stack):
    camila, admin = stack.client("camila"), stack.client("benjamin")
    place_order(camila)
    assert admin.post("/orders/expire-pending", params={"older_than_seconds": 900}).json()["expired"] == []


def test_flujo_de_estados_y_commit_de_stock(stack):
    camila, cocina = stack.client("camila"), stack.client("cocina")
    orden = place_order(camila, [(1, 2)]).json()
    assert cocina.get("/orders").json()["total"] == 0
    pay(stack, camila, orden)
    assert cocina.get("/orders").json()["total"] == 1
    assert cocina.patch(f"/orders/{orden['id']}/status", json={"status": "listo"}).status_code == 409
    assert cocina.patch(f"/orders/{orden['id']}/status", json={"status": "preparando"}).json()["status"] == "preparando"
    assert stock_of(stack, 1) == (48, 0)
    assert cocina.patch(f"/orders/{orden['id']}/status", json={"status": "listo"}).json()["status"] == "listo"
    assert cocina.patch(f"/orders/{orden['id']}/status", json={"status": "entregado"}).json()["status"] == "entregado"
    assert cocina.patch(f"/orders/{orden['id']}/status", json={"status": "preparando"}).status_code == 409


def test_orden_pendiente_no_puede_prepararse(stack):
    camila, cocina = stack.client("camila"), stack.client("cocina")
    orden = place_order(camila).json()
    assert cocina.patch(f"/orders/{orden['id']}/status", json={"status": "preparando"}).status_code == 409
    assert cocina.get(f"/orders/{orden['id']}").status_code == 200


def test_cliente_no_cancela_orden_pagada_pero_admin_si(stack):
    camila, admin = stack.client("camila"), stack.client("benjamin")
    orden = place_order(camila, [(2, 1)]).json()
    pay(stack, camila, orden)
    assert camila.post(f"/orders/{orden['id']}/cancel").status_code == 409
    r = admin.post(f"/orders/{orden['id']}/cancel")
    assert r.status_code == 200 and r.json()["refund_required"] is True
    assert stock_of(stack, 2) == (50, 0)


def test_orden_no_se_crea_si_inventario_esta_caido(stack):
    camila = stack.client("camila")
    stack.stop_service("inventory")
    try:
        r = place_order(camila)
        assert r.status_code == 503 or r.status_code == 502
    finally:
        stack.start_service("inventory")
    assert db_of(stack, "orders").one("SELECT COUNT(*) AS n FROM orders")["n"] == 0
    assert place_order(camila).status_code == 201


def test_orden_no_se_crea_si_clientes_esta_caido(stack):
    camila = stack.client("camila")
    stack.stop_service("clients")
    try:
        assert place_order(camila).status_code in (502, 503)
    finally:
        stack.start_service("clients")
    assert stock_of(stack, 1) == (50, 0)


def test_recuperacion_de_stock_si_inventario_cae_al_cancelar(stack):
    camila, admin = stack.client("camila"), stack.client("benjamin")
    orden = place_order(camila, [(6, 3)]).json()
    stack.stop_service("inventory")
    try:
        r = camila.post(f"/orders/{orden['id']}/cancel")
        assert r.status_code == 200 and r.json()["stock_released"] is False
    finally:
        stack.start_service("inventory")
    assert stock_of(stack, 6) == (40, 3)
    reconciliado = admin.post("/orders/reconcile-stock").json()
    assert reconciliado == {"released": [orden["id"]], "pending": 0}
    assert stock_of(stack, 6) == (40, 0)
    assert admin.post("/orders/reconcile-stock").json() == {"released": [], "pending": 0}


def test_paginacion_de_ordenes(stack):
    camila = stack.client("camila")
    for _ in range(5):
        place_order(camila)
    primera = camila.get("/orders", params={"limit": 2, "offset": 0}).json()
    segunda = camila.get("/orders", params={"limit": 2, "offset": 2}).json()
    assert primera["total"] == 5 and len(primera["items"]) == 2
    assert not {o["id"] for o in primera["items"]} & {o["id"] for o in segunda["items"]}
    assert camila.get("/orders", params={"limit": 500}).status_code == 422


def test_ajuste_de_stock_no_baja_de_lo_reservado(stack):
    camila, cocina = stack.client("camila"), stack.client("cocina")
    place_order(camila, [(1, 10)])
    assert cocina.post("/stock/1/adjust", json={"delta": -41, "reason": "merma"}).status_code == 409
    assert cocina.post("/stock/1/adjust", json={"delta": -40, "reason": "merma"}).json()["available"] == 0
    assert cocina.post("/stock/1/adjust", json={"delta": 5, "reason": "reposicion"}).json()["on_hand"] == 15


def test_persistencia_real_sobrevive_al_reinicio(stack):
    camila = stack.client("camila")
    orden = place_order(camila, [(1, 1)]).json()
    for nombre in ("orders", "inventory", "auth"):
        stack.stop_service(nombre)
        stack.start_service(nombre)
    assert camila.get(f"/orders/{orden['id']}").json()["id"] == orden["id"]
    assert stock_of(stack, 1) == (50, 1)
