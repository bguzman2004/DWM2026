import json
import time

import httpx
import pytest

from common.vault import VaultClient, VaultError
from scripts.vault_bootstrap import revoke_previous_edge, rotate_edge
from tests.support.helpers import ADMIN, db_of, pay, place_order, start_payment, webhook
from tests.support.stack import DEMO_PASSWORD, Stack


def test_servicios_privados_rechazan_llamadas_sin_credencial(shared_stack):
    for name, path in [("inventory", "/products"), ("clients", "/clients"), ("orders", "/orders"), ("payments", "/payments"), ("auth", "/introspect")]:
        url = shared_stack.urls[name]
        assert httpx.get(f"{url}{path}").status_code in (403, 405)
        assert httpx.get(f"{url}{path}", headers={"X-Service-Caller": "api-gateway", "X-Service-Token": "falso"}).status_code in (403, 405)


def test_token_de_otra_arista_no_sirve(shared_stack):
    token_orders = shared_stack.root.read("mariachi/edges/inventory/orders")["token"]
    r = httpx.get(
        f"{shared_stack.urls['inventory']}/products",
        headers={"X-Service-Caller": "orders", "X-Service-Token": token_orders},
    )
    assert r.status_code == 403
    r = httpx.post(
        f"{shared_stack.urls['inventory']}/reservations",
        json={"order_id": "ORD-XXXX", "items": [{"product_id": 1, "qty": 1}]},
        headers={"X-Service-Caller": "api-gateway", "X-Service-Token": shared_stack.root.read("mariachi/edges/inventory/api-gateway")["token"]},
    )
    assert r.status_code == 403


def test_llamador_fuera_de_la_topologia_es_rechazado(shared_stack):
    r = httpx.get(f"{shared_stack.urls['inventory']}/products", headers={"X-Service-Caller": "payments", "X-Service-Token": "x"})
    assert r.status_code == 403


def test_cliente_no_puede_inyectar_identidad_ni_roles(shared_stack):
    camila = shared_stack.client("camila")
    headers = {"X-Roles": "admin", "X-User-Id": "USR-004", "X-Username": "benjamin", "X-Service-Caller": "orders"}
    r = camila.post("/products", json={"name": "Hack", "category": "Tacos", "price": 100}, headers=headers)
    assert r.status_code == 403
    assert camila.get("/auth/me", headers=headers).json()["username"] == "camila"


def test_login_cookie_httponly_y_token_fuera_del_cuerpo(shared_stack):
    http = httpx.Client(base_url=shared_stack.urls["api-gateway"])
    r = http.post("/auth/login", json={"username": "camila", "password": DEMO_PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    token = http.cookies.get("session_token")
    assert token and token not in r.text


def test_credenciales_incorrectas_mismo_mensaje(shared_stack):
    http = httpx.Client(base_url=shared_stack.urls["api-gateway"])
    a = http.post("/auth/login", json={"username": "camila", "password": "mala"})
    b = http.post("/auth/login", json={"username": "fantasma", "password": "mala"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["message"] == b.json()["error"]["message"]
    assert "set-cookie" not in a.headers


def test_sin_sesion_y_con_cookie_falsa_401(shared_stack):
    anon = httpx.Client(base_url=shared_stack.urls["api-gateway"])
    assert anon.get("/orders").status_code == 401
    anon.cookies.set("session_token", "x" * 40)
    assert anon.get("/orders").status_code == 401


def test_logout_revoca_la_sesion(shared_stack):
    camila = shared_stack.client("camila")
    token = camila.cookies.get("session_token")
    assert camila.post("/auth/logout").json() == {"revoked": True}
    reuse = httpx.Client(base_url=shared_stack.urls["api-gateway"])
    reuse.cookies.set("session_token", token)
    assert reuse.get("/auth/me").status_code == 401


def test_sesion_expirada_401(tmp_path):
    s = Stack(tmp_path, extra={"auth": {"session_ttl": 1}}).start()
    try:
        camila = s.client("camila")
        assert camila.get("/auth/me").status_code == 200
        time.sleep(1.3)
        assert camila.get("/auth/me").status_code == 401
    finally:
        s.stop()


def test_bloqueo_de_cuenta_tras_intentos_fallidos(tmp_path):
    s = Stack(tmp_path, extra={"auth": {"max_failures": 3, "lock_seconds": 30}}).start()
    try:
        http = httpx.Client(base_url=s.urls["api-gateway"])
        codes = [http.post("/auth/login", json={"username": "matias", "password": "mala"}).status_code for _ in range(4)]
        assert codes == [401, 401, 401, 429]
        assert http.post("/auth/login", json={"username": "matias", "password": DEMO_PASSWORD}).status_code == 429
    finally:
        s.stop()


def test_limite_de_tasa_en_login_del_gateway(tmp_path):
    s = Stack(tmp_path, extra={"api-gateway": {"limits": {"login": (3, 60)}}}).start()
    try:
        http = httpx.Client(base_url=s.urls["api-gateway"])
        codes = [http.post("/auth/login", json={"username": "x", "password": "y"}).status_code for _ in range(5)]
        assert codes[:3] == [401, 401, 401] and codes[3:] == [429, 429]
    finally:
        s.stop()


MATRIZ = [
    ("camila", "GET", "/products", None, 200),
    ("camila", "POST", "/products", {"name": "Nuevo", "category": "Tacos", "price": 100}, 403),
    ("camila", "GET", "/stock", None, 403),
    ("camila", "GET", "/clients", None, 403),
    ("camila", "PATCH", "/orders/ORD-1/status", {"status": "preparando"}, 403),
    ("camila", "POST", "/orders/expire-pending", None, 403),
    ("cocina", "GET", "/stock", None, 200),
    ("cocina", "POST", "/orders", {"items": [{"product_id": 1, "qty": 1}]}, 403),
    ("cocina", "POST", "/payments", {"order_id": "ORD-1"}, 403),
    ("cocina", "GET", "/payments", None, 403),
    ("cocina", "GET", "/clients", None, 403),
    ("cocina", "DELETE", "/products/1", None, 403),
    ("benjamin", "GET", "/clients", None, 200),
    ("benjamin", "GET", "/stock", None, 200),
    ("benjamin", "GET", "/payments", None, 200),
    ("benjamin", "DELETE", "/products/999", None, 404),
    (None, "GET", "/promotions", None, 200),
    (None, "PATCH", "/promotions/1", {"active": False}, 401),
    ("cocina", "PATCH", "/promotions/1", {"active": False}, 403),
    ("benjamin", "PATCH", "/promotions/999", {"active": True}, 404),
]


@pytest.mark.parametrize("user,method,path,body,expected", MATRIZ)
def test_matriz_de_permisos_http(shared_stack, user, method, path, body, expected):
    http = shared_stack.client(user)
    r = http.request(method, path, json=body) if body is not None else http.request(method, path)
    assert r.status_code == expected, r.text


def test_propiedad_de_ordenes_entre_clientes(stack):
    camila, matias = stack.client("camila"), stack.client("matias")
    orden = place_order(camila).json()
    assert camila.get(f"/orders/{orden['id']}").status_code == 200
    assert matias.get(f"/orders/{orden['id']}").status_code == 404
    assert matias.post(f"/orders/{orden['id']}/cancel").status_code == 404
    assert start_payment(matias, orden["id"]).status_code == 404
    assert matias.get("/orders").json()["total"] == 0
    assert camila.get("/orders").json()["total"] == 1
    assert matias.get("/clients/CLI-001").status_code == 404
    assert camila.get("/clients/CLI-001").status_code == 200
    assert matias.patch("/clients/CLI-001", json={"name": "Hack"}).status_code == 404


def test_datos_del_cliente_enmascarados_para_cocina(stack):
    camila, cocina, admin = stack.client("camila"), stack.client("cocina"), stack.client("benjamin")
    orden = place_order(camila).json()
    created, _ = pay(stack, camila, orden)
    visto = cocina.get("/clients/CLI-001").json()
    assert set(visto) == {"id", "name"}
    assert "email" in admin.get("/clients/CLI-001").json()


def test_vault_minimo_privilegio_por_servicio(shared_stack):
    orders = VaultClient(shared_stack.vault_url, shared_stack.tokens["orders"])
    assert orders.read("mariachi/edges/inventory/orders")["token"]
    for path in ("mariachi/payments", "mariachi/edges/payments/api-gateway", "mariachi/edges/auth/api-gateway"):
        with pytest.raises(VaultError):
            orders.read(path)
    gateway = VaultClient(shared_stack.vault_url, shared_stack.tokens["api-gateway"])
    with pytest.raises(VaultError):
        gateway.read("mariachi/payments")
    payments = VaultClient(shared_stack.vault_url, shared_stack.tokens["payments"])
    assert payments.read("mariachi/payments")["webhook_hmac"]


def test_secretos_distintos_por_integracion(shared_stack):
    from common.topology import EDGES, edge_path

    values = [shared_stack.root.read(edge_path(callee, caller))["token"] for caller, callee in EDGES]
    values.append(shared_stack.root.read("mariachi/payments")["webhook_hmac"])
    assert len(set(values)) == len(values)


def test_rotacion_con_gracia_y_revocacion(stack):
    viejo = stack.root.read("mariachi/edges/inventory/orders")["token"]
    interno = lambda token: httpx.get(
        f"{stack.urls['inventory']}/products", headers={"X-Service-Caller": "graphql-gateway", "X-Service-Token": token}
    )
    rotate_edge(stack.root, "orders", "inventory")
    nuevo = stack.root.read("mariachi/edges/inventory/orders")
    assert nuevo["token"] != viejo and nuevo["previous"] == viejo
    camila = stack.client("camila")
    assert place_order(camila).status_code == 201

    def reservar(token):
        return httpx.post(
            f"{stack.urls['inventory']}/reservations/ORD-ZZZZ/release",
            headers={"X-Service-Caller": "orders", "X-Service-Token": token},
        )

    assert reservar(viejo).status_code == 200
    assert reservar(nuevo["token"]).status_code == 200
    revoke_previous_edge(stack.root, "orders", "inventory")
    assert reservar(viejo).status_code == 403
    assert reservar(nuevo["token"]).status_code == 200
    assert place_order(camila).status_code == 201


def test_vault_caido_falla_cerrado(stack):
    camila = stack.client("camila")
    stack.vault_app.state.state["down"] = True
    try:
        assert camila.get("/orders").status_code == 500
        direct = httpx.get(f"{stack.urls['inventory']}/products", headers={"X-Service-Caller": "api-gateway", "X-Service-Token": "x"})
        assert direct.status_code == 503
        assert httpx.get(f"{stack.urls['inventory']}/health").status_code == 200
        assert httpx.get(f"{stack.urls['inventory']}/ready").status_code == 503
    finally:
        stack.vault_app.state.state["down"] = False
    assert camila.get("/orders").status_code == 200


def test_contrasenas_y_sesiones_no_se_guardan_en_claro(stack):
    camila = stack.client("camila")
    token = camila.cookies.get("session_token")
    auth_db = db_of(stack, "auth")
    dump = json.dumps(auth_db.all("SELECT * FROM users")) + json.dumps(auth_db.all("SELECT * FROM sessions"))
    assert DEMO_PASSWORD not in dump and token not in dump


def test_los_logs_no_contienen_secretos(stack):
    camila, admin = stack.client("camila"), stack.client("benjamin")
    orden = place_order(camila).json()
    created, _ = pay(stack, camila, orden)
    httpx.Client(base_url=stack.urls["api-gateway"]).post("/auth/login", json={"username": "camila", "password": "contrasena-mala-123"})
    prohibidos = [DEMO_PASSWORD, "contrasena-mala-123", camila.cookies.get("session_token"), admin.cookies.get("session_token")]
    prohibidos += list(stack.tokens.values()) + [stack.root.read("mariachi/payments")["webhook_hmac"]]
    from common.topology import EDGES, edge_path

    prohibidos += [stack.root.read(edge_path(callee, caller))["token"] for caller, callee in EDGES]
    texto = "\n".join(stack.capture.lines)
    assert len(texto) > 1000
    for secreto in prohibidos:
        assert secreto not in texto


def test_gateway_corta_antes_de_llamar_al_servicio(stack):
    camila = stack.client("camila")
    stack.call_log.clear()
    assert camila.post("/products", json={"name": "Nuevo", "category": "Tacos", "price": 100}).status_code == 403
    assert camila.get("/stock").status_code == 403
    assert [c for c in stack.call_log if c[0] in ("inventory", "orders")] == []


def test_limite_de_tasa_general_del_gateway(tmp_path):
    s = Stack(tmp_path, extra={"api-gateway": {"limits": {"login": (100, 60), "default": (5, 60)}}}).start()
    try:
        camila = s.client("camila")
        codes = [camila.get("/products").status_code for _ in range(8)]
        assert codes == [200] * 5 + [429] * 3
    finally:
        s.stop()
