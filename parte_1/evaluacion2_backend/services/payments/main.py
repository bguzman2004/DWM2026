import hmac
import hashlib
import json
import secrets as pysecrets
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field, ValidationError

from common.app import create_service_app
from common.calls import ServiceClient, raise_for_upstream
from common.config import Settings
from common.db import Database, now_iso
from common.logs import log
from common.security import make_guard, require_roles, require_user, tokens_match
from common.vault import VaultError, make_secrets

SCHEMA = Path(__file__).with_name("schema.sql")


class PaymentIn(BaseModel):
    order_id: str = Field(min_length=4, max_length=40)


class WebhookEvent(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    type: Literal["payment.succeeded", "payment.failed"]
    provider_ref: str = Field(min_length=4, max_length=64)
    amount: int = Field(gt=0)


def sign(secret, body):
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def view(row):
    return {k: row[k] for k in ("id", "order_id", "amount", "status", "provider_ref", "created_at", "updated_at")}


def create_app(cfg=None):
    cfg = cfg or Settings.from_env("payments")
    secrets = make_secrets(cfg)
    db = Database(cfg.db_path)
    db.init(SCHEMA)
    app = create_service_app(cfg, secrets, db)
    guard = make_guard(cfg, secrets)
    edge = guard("api-gateway", "graphql-gateway")
    gateway_only = guard("api-gateway")
    orders = ServiceClient(cfg, secrets, "orders")
    app.state.closers.append(orders.close)

    def valid_signature(raw, received):
        try:
            data = secrets.get("mariachi/payments")
        except VaultError:
            raise HTTPException(503, "Secretos no disponibles")
        keys = [data.get("webhook_hmac"), data.get("previous")]
        return tokens_match(received, [sign(k, raw) for k in keys if k])

    async def sync_order(payment):
        try:
            response = await orders.request(
                "POST",
                f"/internal/orders/{payment['order_id']}/paid",
                json={"payment_id": payment["id"], "amount": payment["amount"]},
            )
        except Exception:
            log(cfg.name, "order_sync_pending", payment_id=payment["id"])
            return "pending"
        if response.status_code == 200:
            with db.tx() as c:
                c.execute("UPDATE payments SET order_synced = 1, updated_at = ? WHERE id = ?", (now_iso(), payment["id"]))
            return "synced"
        if response.status_code == 409:
            with db.tx() as c:
                c.execute(
                    "UPDATE payments SET status = 'requires_refund', order_synced = 1, updated_at = ? WHERE id = ?",
                    (now_iso(), payment["id"]),
                )
            log(cfg.name, "payment_requires_refund", payment_id=payment["id"])
            return "requires_refund"
        log(cfg.name, "order_sync_pending", payment_id=payment["id"])
        return "pending"

    @app.post("/payments", status_code=201)
    async def create_payment(
        body: PaymentIn,
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=64),
        caller=Depends(edge),
    ):
        user = require_roles(caller, "customer")
        same_key = db.one("SELECT * FROM payments WHERE client_id = ? AND idempotency_key = ?", (user.client_id, idempotency_key))
        if same_key:
            if same_key["order_id"] != body.order_id:
                raise HTTPException(409, "La clave de idempotencia ya se uso con otra orden")
            return {**view(same_key), "reused": True}
        response = await orders.request("GET", f"/internal/orders/{body.order_id}")
        if response.status_code == 404:
            raise HTTPException(404, "Orden no encontrada")
        raise_for_upstream(response)
        order = response.json()
        if order["client_id"] != user.client_id:
            raise HTTPException(404, "Orden no encontrada")
        if order["status"] != "pendiente_pago":
            raise HTTPException(409, f"La orden esta {order['status']} y no admite pago")
        now = now_iso()
        try:
            with db.tx() as c:
                open_one = c.execute(
                    "SELECT * FROM payments WHERE order_id = ? AND status IN ('pending','succeeded') ORDER BY created_at LIMIT 1",
                    (body.order_id,),
                ).fetchone()
                if open_one:
                    return {**view(open_one), "reused": True}
                payment_id = "PAY-" + pysecrets.token_hex(5).upper()
                c.execute(
                    "INSERT INTO payments(id,order_id,client_id,amount,status,provider_ref,idempotency_key,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (payment_id, body.order_id, user.client_id, order["total"], "pending",
                     "chk_" + pysecrets.token_hex(8), idempotency_key, now, now),
                )
        except sqlite3.IntegrityError:
            row = db.one("SELECT * FROM payments WHERE client_id = ? AND idempotency_key = ?", (user.client_id, idempotency_key))
            return {**view(row), "reused": True}
        log(cfg.name, "payment_created", payment_id=payment_id, order_id=body.order_id)
        return {**view(db.one("SELECT * FROM payments WHERE id = ?", (payment_id,))), "reused": False}

    @app.post("/payments/webhook")
    async def webhook(request: Request, x_signature: str = Header("", alias="X-Signature"), caller=Depends(gateway_only)):
        raw = await request.body()
        if not x_signature or not valid_signature(raw, x_signature):
            log(cfg.name, "webhook_bad_signature")
            raise HTTPException(401, "Firma invalida")
        try:
            event = WebhookEvent(**json.loads(raw))
        except (ValueError, ValidationError, TypeError):
            raise HTTPException(422, "Evento invalido")
        payment = db.one("SELECT * FROM payments WHERE provider_ref = ?", (event.provider_ref,))
        if not payment:
            raise HTTPException(404, "Pago no encontrado")
        if event.amount != payment["amount"]:
            raise HTTPException(409, "El monto del evento no coincide")
        duplicate = False
        with db.tx() as c:
            seen = c.execute("SELECT 1 FROM webhook_events WHERE event_id = ?", (event.event_id,)).fetchone()
            if seen:
                duplicate = True
            else:
                if event.type == "payment.succeeded":
                    c.execute(
                        "UPDATE payments SET status = 'succeeded', updated_at = ? WHERE id = ? AND status IN ('pending','failed')",
                        (now_iso(), payment["id"]),
                    )
                else:
                    c.execute(
                        "UPDATE payments SET status = 'failed', updated_at = ? WHERE id = ? AND status = 'pending'",
                        (now_iso(), payment["id"]),
                    )
                c.execute(
                    "INSERT INTO webhook_events(event_id,payment_id,type,received_at) VALUES(?,?,?,?)",
                    (event.event_id, payment["id"], event.type, now_iso()),
                )
        current = db.one("SELECT * FROM payments WHERE id = ?", (payment["id"],))
        sync = "not_needed"
        if current["status"] == "succeeded" and not current["order_synced"]:
            sync = await sync_order(current)
        elif current["status"] == "requires_refund":
            sync = "requires_refund"
        log(cfg.name, "webhook_processed", payment_id=payment["id"], duplicate=duplicate, type=event.type)
        return {"status": "duplicate" if duplicate else "processed", "payment_status": view(
            db.one("SELECT * FROM payments WHERE id = ?", (payment["id"],)))["status"], "order_sync": sync}

    @app.post("/payments/reconcile")
    async def reconcile(caller=Depends(edge)):
        require_roles(caller, "admin")
        rows = db.all("SELECT * FROM payments WHERE status = 'succeeded' AND order_synced = 0")
        results = {row["id"]: await sync_order(row) for row in rows}
        return {"results": results}

    @app.get("/payments")
    def list_payments(
        order_id: str | None = Query(None, max_length=40),
        order_ids: str | None = Query(None, max_length=800),
        caller=Depends(edge),
    ):
        user = require_roles(caller, "customer", "admin")
        wanted = [order_id] if order_id else [i for i in (order_ids or "").split(",") if i][:100]
        where, params = [], []
        if wanted:
            where.append(f"order_id IN ({','.join('?' * len(wanted))})")
            params.extend(wanted)
        if not user.has("admin"):
            where.append("client_id = ?")
            params.append(user.client_id)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        rows = db.all(f"SELECT * FROM payments{clause} ORDER BY created_at DESC LIMIT 100", params)
        return {"items": [{**view(r), "client_id": r["client_id"]} for r in rows]}

    @app.get("/payments/{payment_id}")
    def get_payment(payment_id: str, caller=Depends(edge)):
        user = require_roles(caller, "customer", "admin")
        row = db.one("SELECT * FROM payments WHERE id = ?", (payment_id,))
        if not row or not (user.has("admin") or row["client_id"] == user.client_id):
            raise HTTPException(404, "Pago no encontrado")
        return view(row)

    return app
