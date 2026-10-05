"""Pruebas del Authentication Service (auth-service.py). Ejecutar con:  pytest -q"""
import importlib.util
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from auth_passwords import hash_password, verify_password  # noqa: E402

SECRETO = "secreto-de-prueba"
H_OK = {"X-Gateway-Auth-Secret": SECRETO}


def cargar_servicio():
    spec = importlib.util.spec_from_file_location("auth_service_test", RAIZ / "auth-service.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def auth():
    anterior = os.environ.get("AUTH_INTROSPECTION_SECRET")
    os.environ["AUTH_INTROSPECTION_SECRET"] = SECRETO
    yield cargar_servicio()
    if anterior is None:
        os.environ.pop("AUTH_INTROSPECTION_SECRET", None)
    else:
        os.environ["AUTH_INTROSPECTION_SECRET"] = anterior


@pytest.fixture()
def cliente(auth):
    auth.SESSIONS.clear()
    auth.INTENTOS_FALLIDOS.clear()
    auth.BLOQUEADOS.clear()
    return TestClient(auth.app)


def login(cliente, usuario="matias", clave="5678"):
    return cliente.post("/login", json={"username": usuario, "password": clave}, headers=H_OK)


# ---------- arranque y secreto del gateway ----------
def test_no_arranca_sin_el_secreto(monkeypatch):
    monkeypatch.delenv("AUTH_INTROSPECTION_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        cargar_servicio()


ENDPOINTS = [
    ("post", "/login", {"username": "matias", "password": "5678"}),
    ("post", "/introspect", {"token": "x"}),
    ("post", "/logout", {"token": "x"}),
    ("get", "/health", None),
]


@pytest.mark.parametrize("metodo,ruta,cuerpo", ENDPOINTS)
def test_todos_los_endpoints_exigen_el_secreto_del_gateway(cliente, metodo, ruta, cuerpo):
    pedir = getattr(cliente, metodo)
    kwargs = {"json": cuerpo} if cuerpo is not None else {}
    assert pedir(ruta, **kwargs).status_code == 403
    assert pedir(ruta, headers={"X-Gateway-Auth-Secret": "otro"}, **kwargs).status_code == 403
    assert pedir(ruta, headers=H_OK, **kwargs).status_code != 403


def test_header_con_tildes_responde_403_y_no_500(cliente):
    r = cliente.get("/health", headers={"X-Gateway-Auth-Secret": "ñandú".encode("utf-8")})
    assert r.status_code == 403


# ---------- login ----------
def test_login_correcto_entrega_token_de_15_minutos(cliente, auth):
    r = login(cliente)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["expires_in"] == 900 == auth.TOKEN_LIFETIME_MINUTES * 60
    assert len(cuerpo["access_token"]) >= 40
    assert cuerpo["access_token"] in auth.SESSIONS


def test_login_ignora_mayusculas_y_espacios_en_el_usuario(cliente):
    assert login(cliente, "  Matias ").status_code == 200


def test_el_admin_recibe_su_rol(cliente):
    token = login(cliente, "benjamin", "admin123").json()["access_token"]
    r = cliente.post("/introspect", json={"token": token}, headers=H_OK).json()
    assert r["active"] is True and r["roles"] == ["user", "admin"] and r["username"] == "benjamin"


def test_usuario_inexistente_y_clave_mala_dan_exactamente_lo_mismo(cliente):
    sin_usuario = login(cliente, "fantasma", "x")
    clave_mala = login(cliente, "matias", "mala")
    assert sin_usuario.status_code == clave_mala.status_code == 401
    assert sin_usuario.json() == clave_mala.json() == {"detail": "Credenciales incorrectas"}


def test_campos_demasiado_largos_se_rechazan(cliente):
    assert login(cliente, "u" * 65, "x").status_code == 422
    assert login(cliente, "matias", "p" * 129).status_code == 422


# ---------- contraseñas ----------
def test_no_hay_contrasenas_en_texto_plano(auth):
    for datos in auth.USERS.values():
        assert "password" not in datos
        assert datos["password_hash"].startswith("pbkdf2_sha256$")
    codigo = (RAIZ / "auth-service.py").read_text(encoding="utf-8")
    for clave in ("1234", "5678", "admin123"):
        assert f'"{clave}"' not in codigo


def test_hash_y_verificacion():
    h = hash_password("clave-secreta", iteraciones=1000)
    assert verify_password("clave-secreta", h) is True
    assert verify_password("otra", h) is False
    assert hash_password("clave-secreta", iteraciones=1000) != h  # la sal hace distinto cada hash
    assert verify_password("x", "formato-invalido") is False
    assert verify_password("x", "md5$1$00$00") is False


# ---------- límite de intentos ----------
def test_cinco_fallos_bloquean_al_usuario_por_un_minuto(cliente, auth):
    for _ in range(5):
        assert login(cliente, "matias", "mala").status_code == 401
    r = login(cliente, "matias", "5678")  # ni con la clave correcta mientras está bloqueado
    assert r.status_code == 429
    assert 1 <= int(r.headers["Retry-After"]) <= auth.BLOQUEO_SEGUNDOS
    assert login(cliente, "camila", "1234").status_code == 200  # los demás usuarios no se afectan
    auth.BLOQUEADOS["matias"] = time.monotonic() - 1  # pasa el minuto
    assert login(cliente, "matias", "5678").status_code == 200


def test_un_login_correcto_reinicia_los_fallos(cliente):
    for _ in range(4):
        login(cliente, "matias", "mala")
    assert login(cliente, "matias", "5678").status_code == 200
    for _ in range(4):
        assert login(cliente, "matias", "mala").status_code == 401  # no se bloquea: contó desde cero


def test_tambien_se_bloquean_usuarios_inventados(cliente):
    for _ in range(5):
        login(cliente, "intruso", "x")
    assert login(cliente, "intruso", "x").status_code == 429


# ---------- introspección, vencimiento y logout ----------
def test_introspect_de_token_valido_e_invalido(cliente):
    token = login(cliente).json()["access_token"]
    r = cliente.post("/introspect", json={"token": token}, headers=H_OK).json()
    assert r["active"] is True and r["user_id"] == "USR-002" and r["roles"] == ["user"]
    assert cliente.post("/introspect", json={"token": "inventado"}, headers=H_OK).json() == {"active": False}


def test_token_vencido_queda_inactivo_y_se_borra(cliente, auth):
    token = login(cliente).json()["access_token"]
    auth.SESSIONS[token]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert cliente.post("/introspect", json={"token": token}, headers=H_OK).json() == {"active": False}
    assert token not in auth.SESSIONS


def test_los_logins_limpian_las_sesiones_vencidas(cliente, auth):
    viejo = login(cliente).json()["access_token"]
    auth.SESSIONS[viejo]["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    login(cliente, "camila", "1234")
    assert viejo not in auth.SESSIONS


def test_logout_cierra_la_sesion(cliente):
    token = login(cliente).json()["access_token"]
    assert cliente.post("/logout", json={"token": token}, headers=H_OK).status_code == 200
    assert cliente.post("/introspect", json={"token": token}, headers=H_OK).json() == {"active": False}
    assert cliente.post("/logout", json={"token": token}, headers=H_OK).status_code == 200  # repetirlo no falla


def test_health(cliente):
    r = cliente.get("/health", headers=H_OK)
    assert r.status_code == 200 and r.json()["status"] == "OK"
