import hashlib
import hmac
import re
import sqlite3
import secrets as pysecrets
import time
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from common.app import create_service_app
from common.calls import ServiceClient, raise_for_upstream
from common.config import Settings
from common.db import Database
from common.logs import log
from common.security import make_guard
from common.validators import clean_email, clean_name, clean_phone
from common.vault import make_secrets

SCHEMA = Path(__file__).with_name("schema.sql")
DUMMY_SALT = bytes(16)


def hash_password(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


DEMO_USERS = (
    ("USR-001", "camila", "customer", "CLI-001"),
    ("USR-002", "matias", "customer", "CLI-002"),
    ("USR-003", "cocina", "kitchen", None),
    ("USR-004", "benjamin", "customer,admin", None),
)


def make_seed(password):
    if not password:
        raise RuntimeError("DEMO_PASSWORD es obligatorio para sembrar usuarios de prueba")

    def seed(conn):
        for user_id, username, roles, client_id in DEMO_USERS:
            salt = pysecrets.token_bytes(16)
            conn.execute(
                "INSERT INTO users(id,username,salt,password_hash,roles,client_id) VALUES(?,?,?,?,?,?)",
                (user_id, username, salt.hex(), hash_password(password, salt).hex(), roles, client_id),
            )

    return seed


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(max_length=80)
    email: str = Field(max_length=120)
    phone: str | None = Field(None, max_length=20)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value):
        if not re.fullmatch(r"[a-z0-9_]+", value):
            raise ValueError("solo minusculas, numeros y guion bajo")
        return value

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        return clean_name(value)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        return clean_email(value)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value):
        return clean_phone(value)


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


def create_app(cfg=None):
    cfg = cfg or Settings.from_env("auth")
    secrets = make_secrets(cfg)
    db = Database(cfg.db_path)
    db.init(SCHEMA, make_seed(cfg.extra.get("demo_password")) if cfg.seed else None)
    app = create_service_app(cfg, secrets, db)
    guard = make_guard(cfg, secrets)
    clients = ServiceClient(cfg, secrets, "clients")
    app.state.closers.append(clients.close)
    session_ttl = int(cfg.extra.get("session_ttl", 900))
    max_failures = int(cfg.extra.get("max_failures", 5))
    lock_seconds = int(cfg.extra.get("lock_seconds", 60))

    def register_failure(username):
        if len(username) > 64:
            return
        with db.tx() as c:
            row = c.execute("SELECT count FROM login_failures WHERE username=?", (username,)).fetchone()
            count = (row["count"] if row else 0) + 1
            locked = time.time() + lock_seconds if count >= max_failures else 0
            if locked:
                count = 0
            c.execute(
                "INSERT INTO login_failures(username,count,locked_until) VALUES(?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET count=excluded.count, locked_until=excluded.locked_until",
                (username, count, locked),
            )

    @app.post("/register", status_code=201)
    async def register(body: RegisterIn, caller=Depends(guard("api-gateway"))):
        salt = pysecrets.token_bytes(16)
        digest = await run_in_threadpool(hash_password, body.password, salt)
        user_id = "USR-" + pysecrets.token_hex(4).upper()
        try:
            with db.tx() as c:
                c.execute(
                    "INSERT INTO users(id,username,salt,password_hash,roles,client_id,active) VALUES(?,?,?,?,?,?,0)",
                    (user_id, body.username, salt.hex(), digest.hex(), "customer", None),
                )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "El nombre de usuario no esta disponible")

        def discard():
            with db.tx() as c:
                c.execute("DELETE FROM users WHERE id=? AND active=0", (user_id,))

        try:
            response = await clients.request(
                "POST", "/internal/clients", json={"name": body.name, "email": body.email, "phone": body.phone}
            )
            raise_for_upstream(response)
        except BaseException:
            discard()
            raise
        client_id = response.json()["id"]
        with db.tx() as c:
            c.execute("UPDATE users SET client_id=?, active=1 WHERE id=?", (client_id, user_id))
        log(cfg.name, "register_ok", user_id=user_id, client_id=client_id)
        return {"user_id": user_id, "client_id": client_id, "username": body.username}

    @app.post("/login")
    def login(body: LoginIn, caller=Depends(guard("api-gateway"))):
        now = time.time()
        failure = db.one("SELECT locked_until FROM login_failures WHERE username=?", (body.username,))
        if failure and failure["locked_until"] > now:
            log(cfg.name, "login_locked", username_hash=hash_token(body.username)[:10])
            raise HTTPException(429, "Demasiados intentos, reintente mas tarde")
        user = db.one("SELECT * FROM users WHERE username=?", (body.username,))
        salt = bytes.fromhex(user["salt"]) if user else DUMMY_SALT
        expected = bytes.fromhex(user["password_hash"]) if user else bytes(32)
        match = hmac.compare_digest(hash_password(body.password, salt), expected)
        if not (user and user["active"] and match):
            register_failure(body.username)
            log(cfg.name, "login_failed", username_hash=hash_token(body.username)[:10])
            raise HTTPException(401, "Credenciales incorrectas")
        token = pysecrets.token_urlsafe(32)
        with db.tx() as c:
            c.execute("DELETE FROM login_failures WHERE username=?", (body.username,))
            c.execute("DELETE FROM sessions WHERE expires_at<?", (now,))
            c.execute(
                "INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                (hash_token(token), user["id"], now, now + session_ttl),
            )
        log(cfg.name, "login_ok", user_id=user["id"])
        return {
            "token": token,
            "expires_in": session_ttl,
            "user": {
                "user_id": user["id"],
                "username": user["username"],
                "roles": user["roles"].split(","),
                "client_id": user["client_id"],
            },
        }

    @app.post("/introspect")
    def introspect(body: TokenIn, caller=Depends(guard("api-gateway"))):
        row = db.one(
            "SELECT u.id, u.username, u.roles, u.client_id, u.active, s.expires_at FROM sessions s "
            "JOIN users u ON u.id=s.user_id WHERE s.token_hash=?",
            (hash_token(body.token),),
        )
        if not row or row["expires_at"] <= time.time() or not row["active"]:
            return {"active": False}
        return {
            "active": True,
            "user_id": row["id"],
            "username": row["username"],
            "roles": row["roles"].split(","),
            "client_id": row["client_id"],
            "exp": row["expires_at"],
        }

    @app.post("/logout")
    def logout(body: TokenIn, caller=Depends(guard("api-gateway"))):
        with db.tx() as c:
            cursor = c.execute("DELETE FROM sessions WHERE token_hash=?", (hash_token(body.token),))
        return {"revoked": cursor.rowcount > 0}

    return app
