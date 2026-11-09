import httpx

from tests.support.helpers import db_of, place_order
from tests.support.stack import DEMO_PASSWORD

NUEVO = {"username": "valentina", "password": "clave-larga-123", "name": "Valentina Mora", "email": "Valentina@Example.com", "phone": "+56933333333"}


def registrar(stack, **cambios):
    return httpx.post(f"{stack.urls['api-gateway']}/auth/register", json={**NUEVO, **cambios}, timeout=15.0)


def test_registro_login_y_primer_pedido(stack):
    r = registrar(stack)
    assert r.status_code == 201
    assert r.json()["client_id"].startswith("CLI-") and "password" not in r.text
    http = httpx.Client(base_url=stack.urls["api-gateway"])
    assert http.post("/auth/login", json={"username": "valentina", "password": "clave-larga-123"}).status_code == 200
    assert http.get("/auth/me").json()["roles"] == ["customer"]
    assert place_order(http).status_code == 201
    assert http.get("/clients/" + r.json()["client_id"]).json()["email"] == "valentina@example.com"


def test_registro_no_puede_pedir_roles_ni_cliente(stack):
    r = registrar(stack, roles=["admin"], client_id="CLI-001")
    assert r.status_code == 201
    http = httpx.Client(base_url=stack.urls["api-gateway"])
    http.post("/auth/login", json={"username": "valentina", "password": "clave-larga-123"})
    me = http.get("/auth/me").json()
    assert me["roles"] == ["customer"] and me["client_id"] != "CLI-001"


def test_usuario_y_correo_duplicados(stack):
    assert registrar(stack).status_code == 201
    assert registrar(stack, email="otra@example.com").status_code == 409
    assert registrar(stack, username="otro_usuario").status_code == 409
    assert registrar(stack, username="otro_usuario", email="otra@example.com").status_code == 201


def test_correo_duplicado_no_deja_usuario_huerfano(stack):
    assert registrar(stack, username="uno").status_code == 201
    assert registrar(stack, username="dos").status_code == 409
    assert db_of(stack, "auth").one("SELECT COUNT(*) AS n FROM users WHERE username='dos'")["n"] == 0
    assert registrar(stack, username="dos", email="distinto@example.com").status_code == 201


def test_registro_con_clientes_caido_no_consume_el_usuario(stack):
    stack.stop_service("clients")
    try:
        assert registrar(stack).status_code in (502, 503)
    finally:
        stack.start_service("clients")
    assert db_of(stack, "auth").one("SELECT COUNT(*) AS n FROM users WHERE username='valentina'")["n"] == 0
    assert registrar(stack).status_code == 201


def test_registro_valida_entrada(stack):
    assert registrar(stack, password="corta").status_code == 422
    assert registrar(stack, username="Con Espacios").status_code == 422
    assert registrar(stack, email="no-es-correo").status_code == 422
    assert registrar(stack, name="").status_code == 422
    assert registrar(stack, name="Al").status_code == 422
    assert registrar(stack, phone="12345678").status_code == 422
    assert registrar(stack, phone="+1 555 123 4567").status_code == 422


def test_registro_normaliza_el_telefono_como_el_frontend(stack):
    r = registrar(stack, phone="9 3333 3333")
    assert r.status_code == 201
    http = httpx.Client(base_url=stack.urls["api-gateway"])
    http.post("/auth/login", json={"username": "valentina", "password": "clave-larga-123"})
    assert http.get("/clients/" + r.json()["client_id"]).json()["phone"] == "+56933333333"


def test_clave_registrada_se_guarda_con_hash(stack):
    registrar(stack)
    fila = db_of(stack, "auth").one("SELECT * FROM users WHERE username='valentina'")
    assert "clave-larga-123" not in str(fila) and len(fila["password_hash"]) == 64 and fila["salt"]


def test_registro_con_limite_de_tasa(tmp_path):
    from tests.support.stack import Stack

    s = Stack(tmp_path, extra={"api-gateway": {"limits": {"login": (100, 60), "register": (2, 60), "default": (100, 60)}}}).start()
    try:
        codes = [registrar(s, username=f"usuario{i}", email=f"u{i}@example.com").status_code for i in range(4)]
        assert codes == [201, 201, 429, 429]
    finally:
        s.stop()


def test_clientes_internos_no_se_publican_por_el_gateway(stack):
    admin = stack.client("benjamin")
    assert admin.post("/internal/clients", json={"name": "Hack", "email": "h@example.com"}).status_code == 404
    directo = httpx.post(f"{stack.urls['clients']}/internal/clients", json={"name": "Hack", "email": "h@example.com"})
    assert directo.status_code == 403
