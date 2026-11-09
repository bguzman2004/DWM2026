import secrets as pysecrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from common.app import create_service_app
from common.calls import ServiceClient, raise_for_upstream
from common.config import Settings
from common.db import Database, now_iso
from common.logs import log
from common.security import make_guard, require_roles, require_user
from common.vault import make_secrets

SCHEMA = Path(__file__).with_name("schema.sql")
STAFF = ("kitchen", "admin")
KITCHEN_VISIBLE = ("pagado", "preparando", "listo")
FORWARD = {"pagado": "preparando", "preparando": "listo", "listo": "entregado"}
PAID_STATES = ("pagado", "preparando", "listo", "entregado")


class ItemIn(BaseModel):
    product_id: int = Field(ge=1)
    qty: int = Field(ge=1, le=20)


class OrderIn(BaseModel):
    items: list[ItemIn] = Field(min_length=1, max_length=20)
    notes: str | None = Field(None, max_length=200)


class StatusIn(BaseModel):
    status: Literal["preparando", "listo", "entregado"]


class PaidIn(BaseModel):
    payment_id: str = Field(min_length=3, max_length=40)
    amount: int = Field(gt=0)


def hydrate(db, rows):
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    marks = ",".join("?" * len(ids))
    lines = db.all(
        f"SELECT order_id, product_id, name, unit_price, qty, discount, promo FROM order_items WHERE order_id IN ({marks}) "
        "ORDER BY product_id",
        ids,
    )
    grouped = {}
    for line in lines:
        grouped.setdefault(line["order_id"], []).append(
            {k: line[k] for k in ("product_id", "name", "unit_price", "qty", "discount", "promo")}
        )
    return [
        {
            "id": r["id"],
            "client_id": r["client_id"],
            "status": r["status"],
            "subtotal": r["subtotal"],
            "discount": r["discount"],
            "total": r["total"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "notes": r["notes"],
            "items": grouped.get(r["id"], []),
        }
        for r in rows
    ]


def create_app(cfg=None):
    cfg = cfg or Settings.from_env("orders")
    secrets = make_secrets(cfg)
    db = Database(cfg.db_path)
    db.init(SCHEMA)
    app = create_service_app(cfg, secrets, db)
    guard = make_guard(cfg, secrets)
    edge = guard("api-gateway", "graphql-gateway")
    from_payments = guard("payments")
    from_analytics = guard("analytics")
    inventory = ServiceClient(cfg, secrets, "inventory")
    clients = ServiceClient(cfg, secrets, "clients")

    app.state.closers.extend([inventory.close, clients.close])

    def fetch(order_id):
        rows = db.all("SELECT * FROM orders WHERE id = ?", (order_id,))
        return hydrate(db, rows)[0] if rows else None

    def record(conn, order_id, event, detail=None):
        conn.execute(
            "INSERT INTO order_events(order_id,event,at,detail) VALUES(?,?,?,?)", (order_id, event, now_iso(), detail)
        )

    async def release_stock(order_id):
        try:
            response = await inventory.request("POST", f"/reservations/{order_id}/release")
        except Exception:
            log(cfg.name, "stock_release_pending", order_id=order_id)
            return False
        if response.status_code != 200:
            log(cfg.name, "stock_release_pending", order_id=order_id)
            return False
        with db.tx() as c:
            c.execute("UPDATE orders SET stock_released = 1 WHERE id = ?", (order_id,))
        return True

    def close_order(order_id, new_status, allowed, event):
        with db.tx() as c:
            cursor = c.execute(
                f"UPDATE orders SET status = ?, updated_at = ? WHERE id = ? AND status IN ({','.join('?' * len(allowed))})",
                (new_status, now_iso(), order_id, *allowed),
            )
            if cursor.rowcount:
                record(c, order_id, event)
            return cursor.rowcount == 1

    @app.post("/orders", status_code=201)
    async def create_order(
        body: OrderIn,
        response: Response,
        idempotency_key: str | None = Header(None, alias="Idempotency-Key", min_length=8, max_length=64),
        caller=Depends(edge),
    ):
        user = require_roles(caller, "customer")
        if not user.client_id:
            raise HTTPException(403, "El usuario no tiene un cliente asociado")
        if idempotency_key:
            row = db.one("SELECT order_id FROM idempotency WHERE client_id = ? AND key = ?", (user.client_id, idempotency_key))
            if row:
                response.status_code = 200
                return fetch(row["order_id"])
        found = await clients.request("GET", f"/clients/{user.client_id}", user=user)
        if found.status_code == 404:
            raise HTTPException(409, "El cliente no esta registrado")
        raise_for_upstream(found)
        order_id = "ORD-" + pysecrets.token_hex(4).upper()
        reserved = await inventory.request(
            "POST",
            "/reservations",
            json={"order_id": order_id, "items": [i.model_dump() for i in body.items]},
        )
        raise_for_upstream(reserved)
        data = reserved.json()
        now = now_iso()
        try:
            with db.tx() as c:
                c.execute(
                    "INSERT INTO orders(id,client_id,status,subtotal,discount,total,created_at,updated_at,notes) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        order_id, user.client_id, "pendiente_pago", data["subtotal"], data["discount"], data["total"],
                        now, now, (body.notes or "").strip() or None,
                    ),
                )
                for line in data["lines"]:
                    c.execute(
                        "INSERT INTO order_items(order_id,product_id,name,unit_price,qty,discount,promo) VALUES(?,?,?,?,?,?,?)",
                        (
                            order_id, line["product_id"], line["name"], line["unit_price"], line["qty"],
                            line["discount"], line["promo"],
                        ),
                    )
                record(c, order_id, "created")
                if idempotency_key:
                    c.execute(
                        "INSERT INTO idempotency(client_id,key,order_id) VALUES(?,?,?)",
                        (user.client_id, idempotency_key, order_id),
                    )
        except sqlite3.IntegrityError:
            await inventory.request("POST", f"/reservations/{order_id}/release")
            row = db.one("SELECT order_id FROM idempotency WHERE client_id = ? AND key = ?", (user.client_id, idempotency_key))
            if row:
                response.status_code = 200
                return fetch(row["order_id"])
            raise
        except Exception:
            await inventory.request("POST", f"/reservations/{order_id}/release")
            raise
        log(cfg.name, "order_created", order_id=order_id, total=data["total"])
        return fetch(order_id)

    @app.get("/orders")
    def list_orders(
        status: str | None = None,
        limit: int = Query(20, ge=1, le=50),
        offset: int = Query(0, ge=0),
        caller=Depends(edge),
    ):
        user = require_user(caller)
        where, params = [], []
        if user.has("admin"):
            pass
        elif user.has("kitchen"):
            where.append(f"status IN ({','.join('?' * len(KITCHEN_VISIBLE))})")
            params.extend(KITCHEN_VISIBLE)
        elif user.has("customer") and user.client_id:
            where.append("client_id = ?")
            params.append(user.client_id)
        else:
            raise HTTPException(403, "Sin permisos para esta operacion")
        if status:
            where.append("status = ?")
            params.append(status)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        total = db.one(f"SELECT COUNT(*) AS n FROM orders{clause}", params)["n"]
        rows = db.all(f"SELECT * FROM orders{clause} ORDER BY created_at DESC, id LIMIT ? OFFSET ?", [*params, limit, offset])
        return {"items": hydrate(db, rows), "total": total}

    @app.post("/orders/expire-pending")
    async def expire_pending(older_than_seconds: int = Query(900, ge=0, le=86400), caller=Depends(edge)):
        require_roles(caller, "admin")
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)).isoformat(timespec="microseconds")
        rows = db.all("SELECT id FROM orders WHERE status = 'pendiente_pago' AND created_at <= ?", (cutoff,))
        expired = []
        for row in rows:
            if close_order(row["id"], "expirado", ("pendiente_pago",), "expired"):
                expired.append(row["id"])
                await release_stock(row["id"])
        return {"expired": expired}

    @app.post("/orders/reconcile-stock")
    async def reconcile_stock(caller=Depends(edge)):
        require_roles(caller, "admin")
        rows = db.all("SELECT id FROM orders WHERE status IN ('cancelado','expirado') AND stock_released = 0")
        fixed = [row["id"] for row in rows if await release_stock(row["id"])]
        return {"released": fixed, "pending": len(rows) - len(fixed)}

    @app.get("/orders/{order_id}")
    def get_order(order_id: str, caller=Depends(edge)):
        user = require_user(caller)
        order = fetch(order_id)
        if not order:
            raise HTTPException(404, "Orden no encontrada")
        if user.has(*STAFF):
            return order
        if user.has("customer") and user.client_id == order["client_id"]:
            return order
        raise HTTPException(404, "Orden no encontrada")

    @app.post("/orders/{order_id}/cancel")
    async def cancel(order_id: str, caller=Depends(edge)):
        user = require_user(caller)
        order = fetch(order_id)
        if not order:
            raise HTTPException(404, "Orden no encontrada")
        owner = user.has("customer") and user.client_id == order["client_id"]
        if not (owner or user.has("admin")):
            raise HTTPException(404, "Orden no encontrada")
        allowed = ("pendiente_pago",) if not user.has("admin") else ("pendiente_pago", "pagado")
        if order["status"] not in allowed:
            raise HTTPException(409, f"No se puede cancelar una orden en estado {order['status']}")
        if not close_order(order_id, "cancelado", allowed, "cancelled"):
            raise HTTPException(409, "La orden cambio de estado, reintente")
        released = await release_stock(order_id)
        refund = order["status"] == "pagado"
        return {"id": order_id, "status": "cancelado", "stock_released": released, "refund_required": refund}

    @app.patch("/orders/{order_id}/status")
    async def advance(order_id: str, body: StatusIn, caller=Depends(edge)):
        require_roles(caller, *STAFF)
        order = fetch(order_id)
        if not order:
            raise HTTPException(404, "Orden no encontrada")
        if FORWARD.get(order["status"]) != body.status:
            raise HTTPException(409, f"Transicion invalida: {order['status']} -> {body.status}")
        if body.status == "preparando":
            response = await inventory.request("POST", f"/reservations/{order_id}/commit")
            raise_for_upstream(response)
        if not close_order(order_id, body.status, (order["status"],), f"status:{body.status}"):
            raise HTTPException(409, "La orden cambio de estado, reintente")
        return fetch(order_id)

    @app.get("/internal/orders/export")
    def export(after: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=2000), caller=Depends(from_analytics)):
        events = db.all(
            "SELECT id, order_id, at FROM order_events WHERE event = 'paid' AND id > ? ORDER BY id LIMIT ?",
            (after, limit),
        )
        facts = []
        for event in events:
            for line in db.all(
                "SELECT product_id, name, qty, unit_price, discount FROM order_items WHERE order_id = ? ORDER BY product_id",
                (event["order_id"],),
            ):
                facts.append(
                    {
                        "event_id": event["id"],
                        "order_id": event["order_id"],
                        "product_id": line["product_id"],
                        "name": line["name"],
                        "qty": line["qty"],
                        "amount": line["qty"] * line["unit_price"] - line["discount"],
                        "at": event["at"],
                    }
                )
        return {"facts": facts, "next_after": events[-1]["id"] if events else after}

    @app.get("/internal/orders/{order_id}")
    def internal_get(order_id: str, caller=Depends(from_payments)):
        row = db.one("SELECT id, client_id, total, status FROM orders WHERE id = ?", (order_id,))
        if not row:
            raise HTTPException(404, "Orden no encontrada")
        return row

    @app.post("/internal/orders/{order_id}/paid")
    def mark_paid(order_id: str, body: PaidIn, caller=Depends(from_payments)):
        with db.tx() as c:
            row = c.execute("SELECT status, total FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Orden no encontrada")
            if row["status"] in PAID_STATES:
                return {"changed": False, "status": row["status"]}
            if row["status"] != "pendiente_pago":
                raise HTTPException(409, f"La orden esta {row['status']} y no puede pagarse")
            if body.amount != row["total"]:
                raise HTTPException(409, "El monto no coincide con el total de la orden")
            c.execute("UPDATE orders SET status = 'pagado', updated_at = ? WHERE id = ?", (now_iso(), order_id))
            record(c, order_id, "paid", body.payment_id)
        return {"changed": True, "status": "pagado"}

    return app
