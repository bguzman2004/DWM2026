from tests.support.helpers import gql, items_payload


def test_p02_menu_filtra_por_categoria_incluida_otros(stack):
    camila = stack.client("camila")
    otros = camila.get("/products", params={"category": "Otros"}).json()
    assert [(p["name"], p["price"]) for p in otros["items"]] == [("Quesadilla Mixta", 3200), ("Elote Preparado", 2000)]
    bebidas = camila.get("/products", params={"category": "Bebidas"}).json()
    assert [p["name"] for p in bebidas["items"]] == ["Agua de Horchata", "Agua de Jamaica"]
    assert camila.get("/products", params={"category": "Pizza"}).status_code == 422
    nombres = {p["name"] for p in camila.get("/products").json()["items"]}
    assert {"Tacos al Pastor", "Burrito Especial", "Nachos Supreme", "Quesadilla Mixta"} <= nombres


def test_p03_notas_del_pedido_se_guardan_y_se_limitan_a_200(stack):
    camila = stack.client("camila")
    r = camila.post("/orders", json={**items_payload([(1, 1)]), "notes": "sin cebolla, mas salsa"})
    assert r.status_code == 201 and r.json()["notes"] == "sin cebolla, mas salsa"
    assert camila.post("/orders", json={**items_payload([(1, 1)]), "notes": "x" * 201}).status_code == 422
    assert camila.post("/orders", json={**items_payload([(1, 1)]), "notes": "x" * 200}).status_code == 201
    vacio = camila.post("/orders", json={**items_payload([(1, 1)]), "notes": "   "}).json()
    assert vacio["notes"] is None


def test_p03_carrito_vacio_o_cantidades_invalidas_se_rechazan(stack):
    camila = stack.client("camila")
    assert camila.post("/orders", json={"items": []}).status_code == 422
    assert camila.post("/orders", json=items_payload([(1, 0)])).status_code == 422
    assert camila.post("/orders", json=items_payload([(1, 21)])).status_code == 422
    assert camila.post("/orders", json=items_payload([(999, 1)])).status_code == 409


def test_p04_confirmacion_con_una_sola_consulta_graphql(stack):
    camila = stack.client("camila")
    orden = camila.post("/orders", json={**items_payload([(1, 2), (11, 1)]), "notes": "para llevar"}).json()
    consulta = (
        'query($id: String!) { order(id: $id) { id createdAt subtotal discount total notes status '
        "client { name phone } items { qty name unitPrice discount promo } } }"
    )
    r = gql(camila, consulta, {"id": orden["id"]}).json()
    assert "errors" not in r
    datos = r["data"]["order"]
    assert datos["id"] == orden["id"] and datos["notes"] == "para llevar"
    assert (datos["subtotal"], datos["discount"], datos["total"]) == (8200, 2500, 5700)
    assert datos["client"] == {"name": "Camila Rojas", "phone": "+56911111111"}
    assert [(i["qty"], i["name"], i["unitPrice"], i["discount"], i["promo"]) for i in datos["items"]] == [
        (2, "Tacos al Pastor", 2500, 2500, "2x1"),
        (1, "Quesadilla Mixta", 3200, 0, None),
    ]


def test_el_total_nunca_viene_del_navegador(stack):
    camila = stack.client("camila")
    r = camila.post(
        "/orders", json={**items_payload([(1, 1)]), "total": 1, "unit_price": 1, "discount": 2500, "status": "pagado"}
    )
    assert r.json()["total"] == 2500 and r.json()["discount"] == 0 and r.json()["status"] == "pendiente_pago"


FRONTEND_PLATILLOS = (
    {"id": 1, "nombre": "Tacos al Pastor", "categoria": "Tacos", "precio": 2500},
    {"id": 2, "nombre": "Tacos de Carnitas", "categoria": "Tacos", "precio": 2500},
    {"id": 3, "nombre": "Tacos de Birria", "categoria": "Tacos", "precio": 3000},
    {"id": 4, "nombre": "Burrito Especial", "categoria": "Burritos", "precio": 4500},
    {"id": 5, "nombre": "Burrito de Pollo", "categoria": "Burritos", "precio": 4200},
    {"id": 6, "nombre": "Burrito Vegetariano", "categoria": "Burritos", "precio": 4000},
    {"id": 7, "nombre": "Nachos Supreme", "categoria": "Nachos", "precio": 3500},
    {"id": 8, "nombre": "Nachos con Carne", "categoria": "Nachos", "precio": 4200},
    {"id": 9, "nombre": "Agua de Horchata", "categoria": "Bebidas", "precio": 1800},
    {"id": 10, "nombre": "Agua de Jamaica", "categoria": "Bebidas", "precio": 1800},
    {"id": 11, "nombre": "Quesadilla Mixta", "categoria": "Otros", "precio": 3200},
    {"id": 12, "nombre": "Elote Preparado", "categoria": "Otros", "precio": 2000},
)

FRONTEND_PROMO = "PROMOCIÓN DEL DÍA: 2x1 en Tacos al Pastor"


def test_catalogo_coincide_con_los_datos_del_frontend(stack):
    anon = stack.client()
    catalogo = anon.get("/products", params={"limit": 100}).json()
    assert catalogo["total"] == len(FRONTEND_PLATILLOS)
    for platillo in FRONTEND_PLATILLOS:
        p = anon.get(f"/products/{platillo['id']}").json()
        assert (p["id"], p["name"], p["category"], p["price"]) == tuple(platillo.values())
        assert p["in_stock"] is True and "on_hand" not in p


def test_p01_promocion_del_dia_se_aplica_en_el_servidor(stack):
    anon, camila, admin = stack.client(), stack.client("camila"), stack.client("benjamin")
    promos = anon.get("/promotions").json()["items"]
    assert [(p["product_id"], p["kind"], p["label"]) for p in promos] == [(1, "2x1", FRONTEND_PROMO)]
    impar = camila.post("/orders", json=items_payload([(1, 3)])).json()
    assert (impar["subtotal"], impar["discount"], impar["total"]) == (7500, 2500, 5000)
    sin_promo = camila.post("/orders", json=items_payload([(4, 2)])).json()
    assert (sin_promo["discount"], sin_promo["total"]) == (0, 9000)
    assert camila.patch(f"/promotions/{promos[0]['id']}", json={"active": False}).status_code == 403
    try:
        assert admin.patch(f"/promotions/{promos[0]['id']}", json={"active": False}).json()["active"] is False
        assert anon.get("/promotions").json()["items"] == []
        apagada = camila.post("/orders", json=items_payload([(1, 2)])).json()
        assert (apagada["discount"], apagada["total"]) == (0, 5000)
    finally:
        admin.patch(f"/promotions/{promos[0]['id']}", json={"active": True})
    assert anon.get("/promotions").json()["items"][0]["active"] is True


def test_p03_formulario_del_frontend_valida_contacto_en_el_servidor(stack):
    camila = stack.client("camila")
    formulario = {"name": "  Camila   Rojas ", "phone": "9 1111 1111"}
    r = camila.patch("/clients/CLI-001", json=formulario)
    assert r.status_code == 200
    assert (r.json()["name"], r.json()["phone"]) == ("Camila Rojas", "+56911111111")
    for malo in ({"phone": "12345"}, {"phone": "+56 2 2345 6789"}, {"name": "Al"}, {"email": "no-es-correo"}):
        assert camila.patch("/clients/CLI-001", json=malo).status_code == 422, malo
    carrito = [(1, 2), (11, 1)]
    pedido = camila.post("/orders", json={**items_payload(carrito), "notes": "sin cebolla"})
    assert pedido.status_code == 201
    assert pedido.json()["client_id"] == "CLI-001"
