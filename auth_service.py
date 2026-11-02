import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="El Mariachi - Authentication Service",
    description="Verifica credenciales, emite tokens, introspección y logout"
)

AUTH_INTROSPECTION_SECRET = os.getenv("AUTH_INTROSPECTION_SECRET")
if not AUTH_INTROSPECTION_SECRET:
    raise RuntimeError("AUTH_INTROSPECTION_SECRET no esta configurado")

TOKEN_LIFETIME_MINUTES = 15

USERS = {
    "camila": {
        "user_id": "USR-001",
        "salt": "eae7ebedab4acef7614d5d75559dd45a",
        "password_hash": "f580ce5fc77fa1d3fbf5f1983772460cc260c53efe5523ec94358d5f4f35300a452daaad56befe41dbf7cb88b42fb8bea70171e46063e0477e448bc3b3ace1a2",
        "roles": ["user"]
    },
    "matias": {
        "user_id": "USR-002",
        "salt": "f82e7fefe90660c906e0d5e0618a3ab9",
        "password_hash": "cfc2e221503fee8d76aa944d47f6530b11def52035262afd7257adea10479a6c9d676a3791f6a03e390e9121790e71a50f3213633a0c1b08bfdab9962cab9fe7",
        "roles": ["user"]
    },
    "benjamin": {
        "user_id": "USR-003",
        "salt": "7b6a013a287871472edb66d8e4cb1e7b",
        "password_hash": "0a8764d4c87d1bd9e34b72f509cf0d0b9de5868ee881d0b07b155e39a29875fc536c2a53829be58d700c3370ea025c9a4bfaf12275f5010731a99c9255c361d4",
        "roles": ["user", "admin"]
    }
}

DUMMY_SALT = "00" * 16

SESSIONS = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenRequest(BaseModel):
    token: str


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.scrypt(
        password.encode(),
        salt=bytes.fromhex(salt_hex),
        n=2 ** 14,
        r=8,
        p=1
    ).hex()


def require_gateway(
    x_gateway_auth_secret: str = Header(default="")
):
    valid = secrets.compare_digest(
        x_gateway_auth_secret.encode(),
        AUTH_INTROSPECTION_SECRET.encode()
    )
    if not valid:
        raise HTTPException(
            status_code=403,
            detail="Gateway no autorizado"
        )


@app.get("/health")
def health():
    return {
        "status": "OK",
        "service": "El Mariachi - Authentication Service"
    }


@app.post("/login")
def login(request: LoginRequest):
    user = USERS.get(request.username)
    salt = user["salt"] if user else DUMMY_SALT
    candidate = hash_password(request.password, salt)
    expected = user["password_hash"] if user else ""
    valid = user is not None and secrets.compare_digest(
        candidate.encode(),
        expected.encode()
    )
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas"
        )
    access_token = secrets.token_urlsafe(32)
    SESSIONS[access_token] = {
        "user_id": user["user_id"],
        "username": request.username,
        "roles": user["roles"],
        "expires_at": datetime.now(timezone.utc) + timedelta(
            minutes=TOKEN_LIFETIME_MINUTES
        )
    }
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": TOKEN_LIFETIME_MINUTES * 60
    }


@app.post("/introspect")
def introspect(
    request: TokenRequest,
    x_gateway_auth_secret: str = Header(default="")
):
    require_gateway(x_gateway_auth_secret)
    session = SESSIONS.get(request.token)
    if session is None:
        return {"active": False}
    if datetime.now(timezone.utc) > session["expires_at"]:
        SESSIONS.pop(request.token, None)
        return {"active": False}
    return {
        "active": True,
        "user_id": session["user_id"],
        "username": session["username"],
        "roles": session["roles"],
        "expires_at": session["expires_at"].isoformat()
    }


@app.post("/logout")
def logout(
    request: TokenRequest,
    x_gateway_auth_secret: str = Header(default="")
):
    require_gateway(x_gateway_auth_secret)
    SESSIONS.pop(request.token, None)
    return {"message": "Sesión finalizada"}
