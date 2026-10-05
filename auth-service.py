from datetime import datetime, timedelta, timezone
import math
import os
import secrets
import time

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

from auth_passwords import hash_password, verify_password

app = FastAPI(
    title="El Mariachi - Authentication Service",
    description="Servicio de autenticación y emisión de tokens"
)

USERS = {
    "camila": {
        "password_hash": "pbkdf2_sha256$600000$d2233ef45045db52320ddf49c99c0a81$546d273b848c01a34a278349a45676cc88019f3c0ead84c277f8303b74e71648",
        "user_id": "USR-001",
        "roles": ["user"]
    },
    "matias": {
        "password_hash": "pbkdf2_sha256$600000$a873ed0e4086071f46b3a765793ca315$8cddef984b37e80310d024ec675aea6052ab784a55d99a4e67f5bbaee85f6d15",
        "user_id": "USR-002",
        "roles": ["user"]
    },
    "benjamin": {
        "password_hash": "pbkdf2_sha256$600000$81deeb75cbd7cbaacef6ac13fbad5074$c44b23b439a9dfd73ed33027691d8baa5274263d1745e01d1171ef1d53e2869c",
        "user_id": "USR-003",
        "roles": ["user", "admin"]
    },
}

SESSIONS = {}

TOKEN_LIFETIME_MINUTES = 15

# Protección contra adivinar contraseñas: 5 intentos fallidos en 5 minutos bloquean al usuario 60 segundos
MAX_INTENTOS_FALLIDOS = 5
VENTANA_INTENTOS_SEGUNDOS = 300
BLOQUEO_SEGUNDOS = 60
INTENTOS_FALLIDOS = {}
BLOQUEADOS = {}

AUTH_INTROSPECTION_SECRET = os.getenv(
    "AUTH_INTROSPECTION_SECRET"
)

if not AUTH_INTROSPECTION_SECRET:
    raise RuntimeError(
        "AUTH_INTROSPECTION_SECRET no esta configurado"
    )


def secreto_valido(recibido: str) -> bool:
    # Se compara como bytes: un header con ñ o tildes da 403 y no error 500
    return secrets.compare_digest(
        recibido.encode("utf-8"),
        AUTH_INTROSPECTION_SECRET.encode("utf-8")
    )


# Hash de mentira: se usa cuando el usuario no existe, para que tarde lo mismo que con un usuario real
HASH_USUARIO_INEXISTENTE = hash_password("usuario-inexistente")


def segundos_de_bloqueo(usuario: str) -> int:
    hasta = BLOQUEADOS.get(usuario)
    if hasta is None:
        return 0
    restante = hasta - time.monotonic()
    if restante <= 0:
        BLOQUEADOS.pop(usuario, None)
        return 0
    return math.ceil(restante)


def registrar_intento_fallido(usuario: str):
    ahora = time.monotonic()
    if len(INTENTOS_FALLIDOS) + len(BLOQUEADOS) > 1000:
        # evita que la memoria crezca si alguien prueba miles de usuarios inventados
        for clave in [c for c, t in INTENTOS_FALLIDOS.items() if ahora - t[-1] > VENTANA_INTENTOS_SEGUNDOS]:
            INTENTOS_FALLIDOS.pop(clave, None)
        for clave in [c for c, hasta in BLOQUEADOS.items() if hasta <= ahora]:
            BLOQUEADOS.pop(clave, None)
    recientes = [t for t in INTENTOS_FALLIDOS.get(usuario, []) if ahora - t < VENTANA_INTENTOS_SEGUNDOS]
    recientes.append(ahora)
    INTENTOS_FALLIDOS[usuario] = recientes
    if len(recientes) >= MAX_INTENTOS_FALLIDOS:
        BLOQUEADOS[usuario] = ahora + BLOQUEO_SEGUNDOS
        INTENTOS_FALLIDOS.pop(usuario, None)


def limpiar_sesiones_vencidas():
    ahora = datetime.now(timezone.utc)
    for token in [t for t, s in SESSIONS.items() if ahora > s["expires_at"]]:
        SESSIONS.pop(token, None)


class LoginRequest(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)


class IntrospectionRequest(BaseModel):
    token: str = Field(max_length=256)


@app.post("/login")
def login(request: LoginRequest,
    x_gateway_auth_secret: str = Header(default="")):
    if not secreto_valido(x_gateway_auth_secret):
        raise HTTPException(
            status_code=403,
            detail="Gateway no autorizado"
        )
    username = request.username.strip().lower()
    espera = segundos_de_bloqueo(username)
    if espera > 0:
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos fallidos, espera un momento e intenta de nuevo",
            headers={"Retry-After": str(espera)}
        )
    user = USERS.get(username)
    # Siempre se verifica un hash, exista o no el usuario: mismo mensaje y mismo tiempo de respuesta
    hash_guardado = user["password_hash"] if user else HASH_USUARIO_INEXISTENTE
    password_correcta = verify_password(request.password, hash_guardado)
    if user is None or not password_correcta:
        registrar_intento_fallido(username)
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas"
        )
    INTENTOS_FALLIDOS.pop(username, None)
    limpiar_sesiones_vencidas()
    access_token = secrets.token_urlsafe(32)
    expiration = (datetime.now(timezone.utc) + timedelta(minutes=TOKEN_LIFETIME_MINUTES))
    SESSIONS[access_token] = {
        "user_id": user["user_id"],
        "username": username,
        "roles": user["roles"],
        "expires_at": expiration
    }
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": TOKEN_LIFETIME_MINUTES * 60
    }


@app.post("/introspect")
def introspect(
    request: IntrospectionRequest,
    x_gateway_auth_secret: str = Header(default="")
):
    if not secreto_valido(x_gateway_auth_secret):
        raise HTTPException(
            status_code=403,
            detail="Gateway no autorizado"
        )
    session = SESSIONS.get(request.token)
    if session is None:
        return {
            "active": False
        }
    if (datetime.now(timezone.utc) > session["expires_at"]):
        SESSIONS.pop(request.token, None)
        return {
            "active": False
        }
    return {
        "active": True,
        "user_id": session["user_id"],
        "username": session["username"],
        "roles": session["roles"],
        "expires_at": session["expires_at"].isoformat()
    }


@app.post("/logout")
def logout(
    request: IntrospectionRequest,
    x_gateway_auth_secret: str = Header(default="")
):
    if not secreto_valido(x_gateway_auth_secret):
        raise HTTPException(
            status_code=403,
            detail="Gateway no autorizado"
        )
    SESSIONS.pop(request.token, None)
    return {
        "message": "Sesión finalizada"
    }


@app.get("/health")
def health(x_gateway_auth_secret: str = Header(default="")):
    if not secreto_valido(x_gateway_auth_secret):
        raise HTTPException(
            status_code=403,
            detail="Gateway no autorizado"
        )
    return {
        "status": "OK",
        "service": "El Mariachi - Authentication Service"
    }