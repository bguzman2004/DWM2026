import json
import os
import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.vault import VaultClient
from services.payments.main import sign

GATEWAY = os.environ["GATEWAY_URL"]
PASSWORD = os.environ["DEMO_PASSWORD"]
VAULT = VaultClient(os.environ["VAULT_ADDR"], os.environ["VAULT_ROOT_TOKEN"])
results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition)))
    print(("OK   " if condition else "FALLA"), name, detail)


def session(user):
    http = httpx.Client(base_url=GATEWAY, timeout=15)
    r = http.post("/auth/login", json={"username": user, "password": PASSWORD})
    return http, r


def main():
    anon = httpx.Client(base_url=GATEWAY, timeout=15)
    check("A sin sesion -> 401", anon.get("/orders").status_code == 401)
    _, bad = session("camila") if False else (None, httpx.post(f"{GATEWAY}/auth/login", json={"username": "camila", "password": "incorrecta"}))
    check("B login incorrecto -> 401", bad.status_code == 401)

    camila, login = session("camila")
    check("C login camila -> 200 con cookie HttpOnly", login.status_code == 200 and "httponly" in login.headers["set-cookie"].lower())
    check("C catalogo -> 200", camila.get("/products").status_code == 200)
    check("D cliente no crea productos -> 403", camila.post("/products", json={"name": "X1", "category": "Tacos", "price": 100}).status_code == 403)

    orden = camila.post("/orders", json={"items": [{"product_id": 1, "qty": 2}, {"product_id": 4, "qty": 1}]}).json()
    check("E orden creada con total calculado en servidor", orden["total"] == 7000, orden["id"])
    check("E promocion 2x1 aplicada por el servidor", (orden["subtotal"], orden["discount"]) == (9500, 2500))

    matias, _ = session("matias")
    check("F otro cliente no ve la orden -> 404", matias.get(f"/orders/{orden['id']}").status_code == 404)

    pago = camila.post("/payments", json={"order_id": orden["id"]}, headers={"Idempotency-Key": uuid.uuid4().hex}).json()
    evento = {"event_id": "evt_" + uuid.uuid4().hex[:12], "type": "payment.succeeded", "provider_ref": pago["provider_ref"], "amount": pago["amount"]}
    cuerpo = json.dumps(evento).encode()
    firma = sign(VAULT.read("mariachi/payments")["webhook_hmac"], cuerpo)
    cabeceras = {"content-type": "application/json", "X-Signature": firma}
    primero = httpx.post(f"{GATEWAY}/payments/webhook", content=cuerpo, headers=cabeceras)
    segundo = httpx.post(f"{GATEWAY}/payments/webhook", content=cuerpo, headers=cabeceras)
    check("G webhook firmado procesado", primero.json().get("status") == "processed")
    check("G webhook duplicado ignorado", segundo.json().get("status") == "duplicate")
    check("G orden pagada una sola vez", camila.get(f"/orders/{orden['id']}").json()["status"] == "pagado")
    sin_firma = httpx.post(f"{GATEWAY}/payments/webhook", content=cuerpo, headers={"content-type": "application/json", "X-Signature": "00"})
    check("G firma invalida -> 401", sin_firma.status_code == 401)

    cocina, _ = session("cocina")
    paso = cocina.patch(f"/orders/{orden['id']}/status", json={"status": "preparando"})
    check("H cocina avanza la orden", paso.status_code == 200 and paso.json()["status"] == "preparando")

    consulta = "{ myOrders(first: 5) { total nodes { id status client { name email } items { name product { name } } payment { status } } } }"
    gql = camila.post("/graphql", json={"query": consulta}).json()
    check("I GraphQL agrega ordenes+clientes+inventario+pagos", gql["data"]["myOrders"]["nodes"][0]["payment"]["status"] == "succeeded" and "errors" not in gql)

    admin, _ = session("benjamin")
    admin.post("/graphql", json={"query": "mutation { syncAnalytics }"})
    resumen = admin.post("/graphql", json={"query": "{ salesSummary(days: 7) { orders revenue topProducts { name units } } }"}).json()
    check("J analitica gRPC via GraphQL (admin)", resumen["data"]["salesSummary"]["orders"] >= 1, str(resumen["data"]["salesSummary"]))
    denegado = camila.post("/graphql", json={"query": "{ salesSummary { orders } }"}).json()
    check("J analitica denegada a cliente", "errors" in denegado)

    camila.post("/auth/logout")
    check("K logout revoca la sesion", camila.get("/auth/me").status_code == 401)
    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} verificaciones correctas")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
