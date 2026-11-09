import sqlite3
from pathlib import Path

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from common.app import create_service_app
from common.config import Settings
from common.db import Database, now_iso
from common.security import make_guard, require_roles, require_user
from common.validators import clean_email, clean_name, clean_phone
from common.vault import make_secrets

SCHEMA = Path(__file__).with_name("schema.sql")

SEED_CLIENTS = (
    ("CLI-001", "Camila Rojas", "camila.rojas@example.com", "+56911111111"),
    ("CLI-002", "Matias Canete", "matias.canete@example.com", "+56922222222"),
)


def seed(conn):
    for client_id, name, email, phone in SEED_CLIENTS:
        conn.execute(
            "INSERT INTO clients(id,name,email,phone,created_at) VALUES(?,?,?,?,?)",
            (client_id, name, email, phone, now_iso()),
        )


class ClientIn(BaseModel):
    name: str = Field(max_length=80)
    email: str = Field(max_length=120)
    phone: str | None = Field(None, max_length=20)

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


class ClientPatch(BaseModel):
    name: str | None = Field(None, max_length=80)
    email: str | None = Field(None, max_length=120)
    phone: str | None = Field(None, max_length=20)

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


def view(row, user):
    if user is None or user.has("admin") or user.client_id == row["id"]:
        return {k: row[k] for k in ("id", "name", "email", "phone", "created_at")}
    return {"id": row["id"], "name": row["name"]}


def create_app(cfg=None):
    cfg = cfg or Settings.from_env("clients")
    secrets = make_secrets(cfg)
    db = Database(cfg.db_path)
    db.init(SCHEMA, seed if cfg.seed else None)
    app = create_service_app(cfg, secrets, db)
    guard = make_guard(cfg, secrets)
    access = guard("api-gateway", "graphql-gateway", "orders")

    def can_read(user, client_id):
        return user is None or user.has("admin", "kitchen") or user.client_id == client_id

    @app.get("/clients")
    def list_clients(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), caller=Depends(access)):
        require_roles(caller, "admin")
        total = db.one("SELECT COUNT(*) AS n FROM clients")["n"]
        rows = db.all("SELECT * FROM clients ORDER BY id LIMIT ? OFFSET ?", (limit, offset))
        return {"items": [view(r, caller.user) for r in rows], "total": total}

    @app.get("/clients/batch")
    def batch(ids: str = Query(min_length=1, max_length=800), caller=Depends(access)):
        wanted = sorted({i for i in ids.split(",") if i})[:100]
        marks = ",".join("?" * len(wanted))
        rows = db.all(f"SELECT * FROM clients WHERE id IN ({marks})", wanted)
        return {"items": [view(r, caller.user) for r in rows if can_read(caller.user, r["id"])]}

    @app.get("/clients/{client_id}")
    def get_client(client_id: str, caller=Depends(access)):
        row = db.one("SELECT * FROM clients WHERE id = ?", (client_id,))
        if not row or not can_read(caller.user, client_id):
            raise HTTPException(404, "Cliente no encontrado")
        return view(row, caller.user)

    def insert_client(body):
        with db.tx() as c:
            try:
                count = c.execute("SELECT COUNT(*) AS n FROM clients").fetchone()["n"]
                client_id = f"CLI-{count + 1:03d}"
                c.execute(
                    "INSERT INTO clients(id,name,email,phone,created_at) VALUES(?,?,?,?,?)",
                    (client_id, body.name, body.email, body.phone, now_iso()),
                )
            except sqlite3.IntegrityError:
                raise HTTPException(409, "Ya existe un cliente con ese correo")
        return client_id

    @app.post("/clients", status_code=201)
    def create_client(body: ClientIn, caller=Depends(access)):
        require_roles(caller, "admin")
        client_id = insert_client(body)
        return view(db.one("SELECT * FROM clients WHERE id = ?", (client_id,)), caller.user)

    @app.post("/internal/clients", status_code=201)
    def register_client(body: ClientIn, caller=Depends(guard("auth"))):
        return {"id": insert_client(body)}

    @app.patch("/clients/{client_id}")
    def patch_client(client_id: str, body: ClientPatch, caller=Depends(access)):
        user = require_user(caller)
        if not (user.has("admin") or user.client_id == client_id):
            raise HTTPException(404, "Cliente no encontrado")
        changes = body.model_dump(exclude_none=True)
        if not changes:
            raise HTTPException(422, "Sin cambios")
        sets = ", ".join(f"{k} = ?" for k in changes)
        try:
            with db.tx() as c:
                cursor = c.execute(f"UPDATE clients SET {sets} WHERE id = ?", [*changes.values(), client_id])
                if cursor.rowcount == 0:
                    raise HTTPException(404, "Cliente no encontrado")
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Ya existe un cliente con ese correo")
        return view(db.one("SELECT * FROM clients WHERE id = ?", (client_id,)), user)

    return app
