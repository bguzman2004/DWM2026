import httpx
import pytest

from tests.support.helpers import gql, pay, place_order

CONSULTA_AGREGADA = """
{ myOrders(first: 10) { total nextCursor nodes { id status total
    client { id name email }
    items { name qty product { id name inStock } }
    payment { status amount } } } }
"""


def test_agrega_ordenes_inventario_clientes_y_pagos(stack):
    camila = stack.client("camila")
    orden = place_order(camila, [(1, 2), (4, 1)]).json()
    pay(stack, camila, orden)
    body = gql(camila, CONSULTA_AGREGADA).json()
    assert "errors" not in body
    nodo = body["data"]["myOrders"]["nodes"][0]
    assert nodo["id"] == orden["id"] and nodo["status"] == "pagado"
    assert nodo["client"] == {"id": "CLI-001", "name": "Camila Rojas", "email": "camila.rojas@example.com"}
    assert [i["product"]["name"] for i in nodo["items"]] == ["Tacos al Pastor", "Burrito Especial"]
    assert nodo["payment"] == {"status": "succeeded", "amount": orden["total"]}


def test_batching_evita_n_mas_1(stack):
    camila = stack.client("camila")
    for _ in range(5):
        place_order(camila, [(1, 1), (2, 1), (4, 1)])
    stack.call_log.clear()
    body = gql(camila, CONSULTA_AGREGADA).json()
    assert len(body["data"]["myOrders"]["nodes"]) == 5
    llamadas = [c for c in stack.call_log if c[0] != "auth"]
    gql_calls = [c for c in llamadas if c[0] in ("orders", "inventory", "clients", "payments")]
    assert gql_calls.count(("inventory", "GET", "/products/batch")) == 1
    assert gql_calls.count(("clients", "GET", "/clients/batch")) == 1
    assert gql_calls.count(("payments", "GET", "/payments")) == 1
    assert gql_calls.count(("orders", "GET", "/orders")) == 1


def test_paginacion_con_cursor_sin_duplicados(stack):
    camila = stack.client("camila")
    consulta = "query($c: String){ products(first: 2, after: $c) { total nextCursor nodes { id name } } }"
    vistos, cursor = [], None
    for _ in range(8):
        pagina = gql(camila, consulta, {"c": cursor}).json()["data"]["products"]
        assert pagina["total"] == 12
        vistos += [n["id"] for n in pagina["nodes"]]
        cursor = pagina["nextCursor"]
        if cursor is None:
            break
    assert vistos == list(range(1, 13))


def test_limites_de_pagina_y_cursor_invalido(stack):
    camila = stack.client("camila")
    assert "entre 1 y 50" in gql(camila, "{ products(first: 51) { total } }").json()["errors"][0]["message"]
    assert "entre 1 y 50" in gql(camila, "{ products(first: 0) { total } }").json()["errors"][0]["message"]
    assert "Cursor invalido" in gql(camila, '{ products(first: 2, after: "basura") { total } }').json()["errors"][0]["message"]


def test_limite_de_profundidad(tmp_path):
    from tests.support.stack import Stack

    s = Stack(tmp_path, extra={"graphql-gateway": {"max_depth": 4}}).start()
    try:
        cocina = s.client("cocina")
        permitida = gql(cocina, "{ myOrders(first: 1) { nodes { items { name } } } }").json()
        assert "errors" not in permitida
        profunda = gql(cocina, "{ myOrders(first: 1) { nodes { items { product { stock { available } } } } } }").json()
        assert profunda.get("data") is None
        assert "depth" in profunda["errors"][0]["message"].lower() or "profund" in profunda["errors"][0]["message"].lower()
    finally:
        s.stop()


def test_limite_de_costo_rechaza_consultas_abusivas(stack):
    camila = stack.client("camila")
    base = "myOrders(first: 50) { nodes { items { product { name } } client { name } } }"
    abusiva = "{ " + " ".join(f"q{i}: {base}" for i in range(6)) + " }"
    r = gql(camila, abusiva).json()
    assert "demasiado costosa" in r["errors"][0]["message"].lower()
    assert r.get("data") is None
    razonable = "{ " + " ".join(f"q{i}: {base}" for i in range(1)) + " }"
    assert "errors" not in gql(camila, razonable).json()


def test_introspeccion_deshabilitada_y_get_no_permitido(stack):
    camila = stack.client("camila")
    r = gql(camila, "{ __schema { types { name } } }").json()
    assert "errors" in r and r.get("data") is None
    assert camila.get("/graphql", params={"query": "{ me { username } }"}).status_code in (404, 405)


def test_batch_de_operaciones_no_permitido(stack):
    camila = stack.client("camila")
    r = camila.post("/graphql", json=[{"query": "{ me { username } }"}, {"query": "{ me { username } }"}])
    assert r.status_code in (400, 422, 502)


def test_autorizacion_por_campo(stack):
    camila, cocina, admin = stack.client("camila"), stack.client("cocina"), stack.client("benjamin")
    place_order(camila)
    consulta_stock = "{ product(id: 1) { name stock { available } } }"
    r = gql(camila, consulta_stock).json()
    assert r["data"]["product"]["stock"] is None and "cocina" in r["errors"][0]["message"]
    assert gql(cocina, consulta_stock).json()["data"]["product"]["stock"]["available"] == 49
    ordenes_cocina = gql(cocina, "{ myOrders(first: 5) { nodes { id } } }").json()
    assert ordenes_cocina["data"]["myOrders"]["nodes"] == []
    pago = gql(cocina, "{ order(id: \"ORD-X\") { payment { status } } }").json()
    assert pago["data"]["order"] is None


def test_correo_del_cliente_solo_para_dueno_o_admin(stack):
    camila, cocina, admin = stack.client("camila"), stack.client("cocina"), stack.client("benjamin")
    orden = place_order(camila).json()
    pay(stack, camila, orden)
    q = f'{{ order(id: "{orden["id"]}") {{ client {{ name email phone }} payment {{ status }} }} }}'
    vista_cocina = gql(cocina, q).json()
    assert vista_cocina["data"]["order"]["client"]["name"] == "Camila Rojas"
    assert vista_cocina["data"]["order"]["client"]["email"] is None
    assert vista_cocina["data"]["order"]["payment"] is None
    assert len(vista_cocina["errors"]) == 3
    vista_admin = gql(admin, q).json()
    assert vista_admin["data"]["order"]["client"]["email"] == "camila.rojas@example.com"
    assert "errors" not in vista_admin


def test_no_se_ve_la_orden_de_otro_cliente(stack):
    camila, matias = stack.client("camila"), stack.client("matias")
    orden = place_order(camila).json()
    assert gql(matias, f'{{ order(id: "{orden["id"]}") {{ id }} }}').json()["data"]["order"] is None
    assert gql(matias, "{ myOrders(first: 5) { total } }").json()["data"]["myOrders"]["total"] == 0


def test_errores_parciales_si_clientes_no_responde(stack):
    camila = stack.client("camila")
    place_order(camila)
    stack.stop_service("clients")
    try:
        r = gql(camila, "{ myOrders(first: 5) { nodes { id total client { name } items { name } } } }").json()
    finally:
        stack.start_service("clients")
    nodo = r["data"]["myOrders"]["nodes"][0]
    assert nodo["client"] is None and nodo["total"] == 2500 and nodo["items"][0]["name"] == "Tacos al Pastor"
    assert r["errors"][0]["path"] == ["myOrders", "nodes", 0, "client"]
    assert "no disponible" in r["errors"][0]["message"]


def test_errores_parciales_si_inventario_no_responde(stack):
    camila = stack.client("camila")
    place_order(camila)
    stack.stop_service("inventory")
    try:
        r = gql(camila, "{ myOrders(first: 5) { nodes { id client { name } items { name product { name } } } } }").json()
    finally:
        stack.start_service("inventory")
    nodo = r["data"]["myOrders"]["nodes"][0]
    assert nodo["client"]["name"] == "Camila Rojas" and nodo["items"][0]["product"] is None
    assert any("inventory" in e["message"] for e in r["errors"])


def test_crear_orden_por_graphql(stack):
    camila = stack.client("camila")
    mutacion = 'mutation { createOrder(items: [{productId: 2, qty: 3}], idempotencyKey: "gql-clave-0001") { id total status } }'
    a = gql(camila, mutacion).json()["data"]["createOrder"]
    b = gql(camila, mutacion).json()["data"]["createOrder"]
    assert a["total"] == 7500 and a["id"] == b["id"]


def test_graphql_exige_sesion_y_llamador_autorizado(stack):
    anon = httpx.Client(base_url=stack.urls["api-gateway"])
    assert gql(anon, "{ me { username } }").status_code == 401
    assert httpx.post(f"{stack.urls['graphql-gateway']}/graphql", json={"query": "{ me { username } }"}).status_code == 403


def test_errores_internos_no_filtran_detalles(stack):
    camila = stack.client("camila")
    r = gql(camila, "{ order(id: \"../../etc\") { id } }").json()
    texto = str(r)
    assert "Traceback" not in texto and "sqlite" not in texto.lower()
