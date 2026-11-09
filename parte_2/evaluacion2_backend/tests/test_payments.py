import json
import threading
import uuid

import httpx

from scripts.vault_bootstrap import revoke_previous_webhook, rotate_webhook
from tests.support.helpers import db_of, pay, place_order, start_payment, stock_of, webhook


def eventos_pagado(stack, order_id):
    return db_of(stack, "orders").one(
        "SELECT COUNT(*) AS n FROM order_events WHERE event='paid' AND order_id=?", (order_id,)
    )["n"]


def test_pago_exitoso_marca_la_orden_pagada(stack):
    camila = stack.client("camila")
    orden = place_order(camila, [(1, 2)]).json()
    pago, resultado = pay(stack, camila, orden)
    assert pago["amount"] == orden["total"] and pago["status"] == "pending"
    assert resultado.json() == {"status": "processed", "payment_status": "succeeded", "order_sync": "synced"}
    assert camila.get(f"/orders/{orden['id']}").json()["status"] == "pagado"


def test_webhook_duplicado_no_paga_dos_veces(stack):
    camila = stack.client("camila")
    orden = place_order(camila).json()
    pago = start_payment(camila, orden["id"]).json()
    primero = webhook(stack, pago["provider_ref"], pago["amount"], event_id="evt_duplicado_01")
    segundo = webhook(stack, pago["provider_ref"], pago["amount"], event_id="evt_duplicado_01")
    assert primero.json()["status"] == "processed"
    assert segundo.status_code == 200 and segundo.json()["status"] == "duplicate"
    assert eventos_pagado(stack, orden["id"]) == 1
    assert db_of(stack, "payments").one("SELECT COUNT(*) AS n FROM webhook_events")["n"] == 1


def test_webhooks_duplicados_en_paralelo(stack):
    camila = stack.client("camila")
    orden = place_order(camila).json()
    pago = start_payment(camila, orden["id"]).json()
    respuestas = []

    def enviar():
        respuestas.append(webhook(stack, pago["provider_ref"], pago["amount"], event_id="evt_paralelo_01").json()["status"])

    hilos = [threading.Thread(target=enviar) for _ in range(8)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert respuestas.count("processed") == 1
    assert respuestas.count("duplicate") == 7
    assert eventos_pagado(stack, orden["id"]) == 1


def test_dos_eventos_distintos_de_exito_no_duplican_el_cobro(stack):
    camila = stack.client("camila")
    orden = place_order(camila).json()
    pago = start_payment(camila, orden["id"]).json()
    webhook(stack, pago["provider_ref"], pago["amount"], event_id="evt_distinto_001")
    webhook(stack, pago["provider_ref"], pago["amount"], event_id="evt_distinto_002")
    assert eventos_pagado(stack, orden["id"]) == 1
    assert camila.get(f"/payments/{pago['id']}").json()["status"] == "succeeded"


def test_crear_pago_dos_veces_devuelve_el_mismo(stack):
    camila = stack.client("camila")
    orden = place_order(camila).json()
    a = start_payment(camila, orden["id"], key="clave-pago-0001")
    b = start_payment(camila, orden["id"], key="clave-pago-0001")
    c = start_payment(camila, orden["id"], key="clave-pago-0002")
    assert a.status_code == 201
    assert b.json()["id"] == a.json()["id"] and b.json()["reused"] is True
    assert c.json()["id"] == a.json()["id"] and c.json()["reused"] is True
    assert db_of(stack, "payments").one("SELECT COUNT(*) AS n FROM payments")["n"] == 1


def test_misma_clave_con_otra_orden_es_conflicto(stack):
    camila = stack.client("camila")
    a, b = place_order(camila).json(), place_order(camila).json()
    start_payment(camila, a["id"], key="clave-pago-0009")
    assert start_payment(camila, b["id"], key="clave-pago-0009").status_code == 409


def test_pago_requiere_clave_de_idempotencia(stack):
    camila = stack.client("camila")
    orden = place_order(camila).json()
    assert camila.post("/payments", json={"order_id": orden["id"]}).status_code == 422


def test_firma_invalida_o_ausente(stack):
    camila = stack.client("camila")
    orden = place_order(camila).json()
    pago = start_payment(camila, orden["id"]).json()
    assert webhook(stack, pago["provider_ref"], pago["amount"], secret="clave-incorrecta").status_code == 401
    alterado = webhook(stack, pago["provider_ref"], pago["amount"], mutate=lambda b: b.replace(b'"amount": %d' % pago["amount"], b'"amount": 1'))
    assert alterado.status_code == 401
    sin_firma = httpx.post(
        f"{stack.urls['api-gateway']}/payments/webhook",
        json={"event_id": "evt_sin_firma_1", "type": "payment.succeeded", "provider_ref": pago["provider_ref"], "amount": pago["amount"]},
    )
    assert sin_firma.status_code == 401
    assert camila.get(f"/orders/{orden['id']}").json()["status"] == "pendiente_pago"


def test_monto_distinto_es_rechazado(stack):
    camila = stack.client("camila")
    orden = place_order(camila).json()
    pago = start_payment(camila, orden["id"]).json()
    assert webhook(stack, pago["provider_ref"], pago["amount"] - 1).status_code == 409
    assert webhook(stack, "chk_inexistente", 100).status_code == 404


def test_pago_fallido_permite_reintentar(stack):
    camila = stack.client("camila")
    orden = place_order(camila).json()
    primero = start_payment(camila, orden["id"]).json()
    webhook(stack, primero["provider_ref"], primero["amount"], kind="payment.failed")
    assert camila.get(f"/payments/{primero['id']}").json()["status"] == "failed"
    segundo = start_payment(camila, orden["id"]).json()
    assert segundo["id"] != primero["id"]
    webhook(stack, segundo["provider_ref"], segundo["amount"])
    assert camila.get(f"/orders/{orden['id']}").json()["status"] == "pagado"


def test_no_se_paga_orden_ajena_ni_ya_pagada(stack):
    camila, matias = stack.client("camila"), stack.client("matias")
    orden = place_order(camila).json()
    assert start_payment(matias, orden["id"]).status_code == 404
    pay(stack, camila, orden)
    assert start_payment(camila, orden["id"]).status_code == 409
    assert camila.get("/payments").json()["items"][0]["order_id"] == orden["id"]
    assert matias.get("/payments").json()["items"] == []


def test_ordenes_ajenas_no_aparecen_en_pagos(stack):
    camila, matias = stack.client("camila"), stack.client("matias")
    orden = place_order(camila).json()
    pago = start_payment(camila, orden["id"]).json()
    assert matias.get(f"/payments/{pago['id']}").status_code == 404
    assert camila.get(f"/payments/{pago['id']}").status_code == 200


def test_webhook_con_ordenes_caido_se_recupera_con_reintento(stack):
    camila = stack.client("camila")
    orden = place_order(camila).json()
    pago = start_payment(camila, orden["id"]).json()
    stack.stop_service("orders")
    try:
        r = webhook(stack, pago["provider_ref"], pago["amount"], event_id="evt_reintento_01")
        assert r.status_code == 200 and r.json()["order_sync"] == "pending"
    finally:
        stack.start_service("orders")
    assert camila.get(f"/orders/{orden['id']}").json()["status"] == "pendiente_pago"
    r = webhook(stack, pago["provider_ref"], pago["amount"], event_id="evt_reintento_01")
    assert r.json()["status"] == "duplicate" and r.json()["order_sync"] == "synced"
    assert camila.get(f"/orders/{orden['id']}").json()["status"] == "pagado"
    assert eventos_pagado(stack, orden["id"]) == 1


def test_conciliacion_manual_de_pagos_pendientes(stack):
    camila, admin = stack.client("camila"), stack.client("benjamin")
    orden = place_order(camila).json()
    pago = start_payment(camila, orden["id"]).json()
    stack.stop_service("orders")
    try:
        webhook(stack, pago["provider_ref"], pago["amount"])
    finally:
        stack.start_service("orders")
    assert admin.post("/payments/reconcile").json()["results"] == {pago["id"]: "synced"}
    assert camila.get(f"/orders/{orden['id']}").json()["status"] == "pagado"


def test_pago_tardio_sobre_orden_expirada_requiere_reembolso(stack):
    camila, admin = stack.client("camila"), stack.client("benjamin")
    orden = place_order(camila, [(1, 2)]).json()
    pago = start_payment(camila, orden["id"]).json()
    admin.post("/orders/expire-pending", params={"older_than_seconds": 0})
    r = webhook(stack, pago["provider_ref"], pago["amount"])
    assert r.json()["order_sync"] == "requires_refund"
    assert camila.get(f"/payments/{pago['id']}").json()["status"] == "requires_refund"
    assert camila.get(f"/orders/{orden['id']}").json()["status"] == "expirado"
    assert stock_of(stack, 1) == (50, 0)


def test_rotacion_del_secreto_del_webhook(stack):
    camila = stack.client("camila")
    viejo = stack.root.read("mariachi/payments")["webhook_hmac"]
    rotate_webhook(stack.root)
    a = place_order(camila).json()
    pa = start_payment(camila, a["id"]).json()
    assert webhook(stack, pa["provider_ref"], pa["amount"], secret=viejo).status_code == 200
    revoke_previous_webhook(stack.root)
    b = place_order(camila).json()
    pb = start_payment(camila, b["id"]).json()
    assert webhook(stack, pb["provider_ref"], pb["amount"], secret=viejo).status_code == 401
    assert webhook(stack, pb["provider_ref"], pb["amount"]).status_code == 200


def test_orders_valida_el_monto_aunque_el_aviso_venga_de_payments(stack):
    camila = stack.client("camila")
    orden = place_order(camila, [(4, 1)]).json()
    interno = stack.internal("payments", "orders")
    r = interno.post(f"/internal/orders/{orden['id']}/paid", json={"payment_id": "PAY-falso", "amount": orden["total"] - 1})
    assert r.status_code == 409
    assert camila.get(f"/orders/{orden['id']}").json()["status"] == "pendiente_pago"
    ok = interno.post(f"/internal/orders/{orden['id']}/paid", json={"payment_id": "PAY-real", "amount": orden["total"]})
    assert ok.json() == {"changed": True, "status": "pagado"}
