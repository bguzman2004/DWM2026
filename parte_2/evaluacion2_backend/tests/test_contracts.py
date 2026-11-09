import httpx
import pytest

from common.topology import SERVICES



def test_health_y_ready_de_todos_los_servicios(shared_stack):
    for name in SERVICES:
        if name == "analytics":
            continue
        url = shared_stack.urls[name]
        assert httpx.get(f"{url}/health").json() == {"status": "ok", "service": name}
        ready = httpx.get(f"{url}/ready")
        assert ready.status_code == 200, (name, ready.text)
        assert ready.json()["checks"]["vault"] == "ok"


def test_catalogo_para_cliente_no_expone_cantidades(shared_stack):
    camila = shared_stack.client("camila")
    body = camila.get("/products").json()
    assert body["total"] == 12
    assert set(body["items"][0]) == {"id", "name", "category", "price", "active", "in_stock"}


def test_catalogo_para_cocina_muestra_stock(shared_stack):
    cocina = shared_stack.client("cocina")
    assert {"on_hand", "reserved", "available"} <= set(cocina.get("/products/1").json())


def test_validacion_devuelve_422_con_formato_estandar(shared_stack):
    admin = shared_stack.client("benjamin")
    r = admin.post("/products", json={"name": "X", "category": "Pizza", "price": -5})
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["status"] == 422 and error["request_id"] and error["details"]
    assert all(set(d) == {"loc", "msg"} for d in error["details"])


def test_ruta_inexistente_y_metodo_no_permitido(shared_stack):
    camila = shared_stack.client("camila")
    assert camila.get("/no-existe").status_code == 404
    assert camila.put("/products/1", json={}).status_code == 405


@pytest.mark.parametrize("path", ["/reservations", "/internal/orders/ORD-1", "/internal/orders/export", "/reservations/ORD-1/release"])
def test_rutas_internas_no_salen_por_el_gateway(shared_stack, path):
    admin = shared_stack.client("benjamin")
    assert admin.get(path).status_code == 404
    assert admin.post(path, json={}).status_code in (404, 405)


def test_cuerpo_no_json_y_cuerpo_grande(shared_stack):
    admin = shared_stack.client("benjamin")
    assert admin.post("/orders", content=b"hola", headers={"content-type": "text/plain"}).status_code == 415
    big = b'{"x": "' + b"a" * 70000 + b'"}'
    assert admin.post("/products", content=big, headers={"content-type": "application/json"}).status_code == 413


def test_cada_servicio_publica_su_contrato_openapi(shared_stack):
    esperado = {
        "inventory": "/reservations",
        "orders": "/orders/{order_id}/cancel",
        "payments": "/payments/webhook",
        "clients": "/clients/{client_id}",
        "auth": "/introspect",
    }
    for name, path in esperado.items():
        spec = httpx.get(f"{shared_stack.urls[name]}/openapi.json").json()
        assert path in spec["paths"], name
    assert httpx.get(f"{shared_stack.urls['api-gateway']}/openapi.json").status_code == 404


def test_catalogo_publico_para_visitantes_solo_campos_publicos(shared_stack):
    anon = httpx.Client(base_url=shared_stack.urls["api-gateway"])
    r = anon.get("/products")
    assert r.status_code == 200 and r.json()["total"] == 12
    assert all(set(p) == {"id", "name", "category", "price", "active", "in_stock"} for p in r.json()["items"])
    assert anon.get("/products/1").status_code == 200
    assert anon.get("/products", params={"include_inactive": "true"}).json()["total"] == 12
    assert anon.get("/stock").status_code == 401
    anon.cookies.set("session_token", "x" * 40)
    assert anon.get("/products").status_code == 200


def test_catalogo_con_sesion_de_cocina_incluye_stock(shared_stack):
    cocina = shared_stack.client("cocina")
    assert "available" in cocina.get("/products/1").json()
