import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

from common.app import create_service_app
from common.config import Settings
from common.db import Database, now_iso
from common.security import make_guard, require_roles
from common.vault import make_secrets

SCHEMA = Path(__file__).with_name("schema.sql")
STAFF = ("kitchen", "admin")

SEED_PRODUCTS = (
    ("Tacos al Pastor", "Tacos", 2500, 50),
    ("Tacos de Carnitas", "Tacos", 2500, 50),
    ("Tacos de Birria", "Tacos", 3000, 40),
    ("Burrito Especial", "Burritos", 4500, 40),
    ("Burrito de Pollo", "Burritos", 4200, 40),
    ("Burrito Vegetariano", "Burritos", 4000, 40),
    ("Nachos Supreme", "Nachos", 3500, 30),
    ("Nachos con Carne", "Nachos", 4200, 30),
    ("Agua de Horchata", "Bebidas", 1800, 60),
    ("Agua de Jamaica", "Bebidas", 1800, 60),
    ("Quesadilla Mixta", "Otros", 3200, 40),
    ("Elote Preparado", "Otros", 2000, 40),
)

SEED_PROMOTIONS = ((1, "2x1", "PROMOCIÓN DEL DÍA: 2x1 en Tacos al Pastor"),)


def seed(conn):
    for name, category, price, qty in SEED_PRODUCTS:
        cursor = conn.execute("INSERT INTO products(name,category,price) VALUES(?,?,?)", (name, category, price))
        conn.execute("INSERT INTO stock(product_id,on_hand) VALUES(?,?)", (cursor.lastrowid, qty))
    for product_id, kind, label in SEED_PROMOTIONS:
        conn.execute("INSERT INTO promotions(product_id,kind,label) VALUES(?,?,?)", (product_id, kind, label))


def promo_discount(kind, unit_price, qty):
    if kind == "2x1":
        return (qty // 2) * unit_price
    return 0


class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    category: Literal["Tacos", "Burritos", "Nachos", "Bebidas", "Otros"]
    price: int = Field(gt=0, le=1_000_000)
    stock: int = Field(0, ge=0, le=100_000)


class ProductPatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=80)
    price: int | None = Field(None, gt=0, le=1_000_000)
    active: bool | None = None


class AdjustIn(BaseModel):
    delta: int = Field(ge=-100_000, le=100_000)
    reason: str = Field(min_length=3, max_length=120)


class PromotionPatch(BaseModel):
    active: bool


class Line(BaseModel):
    product_id: int = Field(ge=1)
    qty: int = Field(ge=1, le=50)


class ReserveIn(BaseModel):
    order_id: str = Field(min_length=4, max_length=40)
    items: list[Line] = Field(min_length=1, max_length=20)


PRODUCT_SQL = (
    "SELECT p.id, p.name, p.category, p.price, p.active, s.on_hand, s.reserved "
    "FROM products p JOIN stock s ON s.product_id = p.id"
)


def product_view(row, staff):
    available = row["on_hand"] - row["reserved"]
    view = {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "price": row["price"],
        "active": bool(row["active"]),
        "in_stock": available > 0,
    }
    if staff:
        view.update({"on_hand": row["on_hand"], "reserved": row["reserved"], "available": available})
    return view


def create_app(cfg=None):
    cfg = cfg or Settings.from_env("inventory")
    secrets = make_secrets(cfg)
    db = Database(cfg.db_path)
    db.init(SCHEMA, seed if cfg.seed else None)
    app = create_service_app(cfg, secrets, db)
    guard = make_guard(cfg, secrets)
    public = guard("api-gateway", "graphql-gateway", "orders")
    edge = guard("api-gateway", "graphql-gateway")
    only_orders = guard("orders")

    def is_staff(caller):
        return caller.user is not None and caller.user.has(*STAFF)

    @app.get("/products")
    def list_products(
        category: Literal["Tacos", "Burritos", "Nachos", "Bebidas", "Otros"] | None = None,
        include_inactive: bool = False,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        caller=Depends(edge),
    ):
        staff = is_staff(caller)
        where, params = [], []
        if category:
            where.append("p.category = ?")
            params.append(category)
        if not (include_inactive and staff):
            where.append("p.active = 1")
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        total = db.one(f"SELECT COUNT(*) AS n FROM products p{clause}", params)["n"]
        rows = db.all(f"{PRODUCT_SQL}{clause} ORDER BY p.id LIMIT ? OFFSET ?", [*params, limit, offset])
        return {"items": [product_view(r, staff) for r in rows], "total": total}

    @app.get("/products/batch")
    def batch(ids: str = Query(min_length=1, max_length=400), caller=Depends(edge)):
        try:
            wanted = sorted({int(i) for i in ids.split(",")})[:100]
        except ValueError:
            raise HTTPException(422, "ids invalidos")
        marks = ",".join("?" * len(wanted))
        rows = db.all(f"{PRODUCT_SQL} WHERE p.id IN ({marks})", wanted)
        staff = is_staff(caller)
        return {"items": [product_view(r, staff) for r in rows]}

    @app.get("/products/{product_id}")
    def get_product(product_id: int, caller=Depends(edge)):
        row = db.one(f"{PRODUCT_SQL} WHERE p.id = ?", (product_id,))
        staff = is_staff(caller)
        if not row or (not row["active"] and not staff):
            raise HTTPException(404, "Producto no encontrado")
        return product_view(row, staff)

    @app.post("/products", status_code=201)
    def create_product(body: ProductIn, caller=Depends(edge)):
        require_roles(caller, "admin")
        try:
            with db.tx() as c:
                cursor = c.execute(
                    "INSERT INTO products(name,category,price) VALUES(?,?,?)", (body.name, body.category, body.price)
                )
                c.execute("INSERT INTO stock(product_id,on_hand) VALUES(?,?)", (cursor.lastrowid, body.stock))
                new_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Ya existe un producto con ese nombre")
        return product_view(db.one(f"{PRODUCT_SQL} WHERE p.id = ?", (new_id,)), True)

    @app.patch("/products/{product_id}")
    def patch_product(product_id: int, body: ProductPatch, caller=Depends(edge)):
        require_roles(caller, "admin")
        changes = body.model_dump(exclude_none=True)
        if not changes:
            raise HTTPException(422, "Sin cambios")
        if "active" in changes:
            changes["active"] = int(changes["active"])
        sets = ", ".join(f"{k} = ?" for k in changes)
        try:
            with db.tx() as c:
                cursor = c.execute(f"UPDATE products SET {sets} WHERE id = ?", [*changes.values(), product_id])
                if cursor.rowcount == 0:
                    raise HTTPException(404, "Producto no encontrado")
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Ya existe un producto con ese nombre")
        return product_view(db.one(f"{PRODUCT_SQL} WHERE p.id = ?", (product_id,)), True)

    @app.delete("/products/{product_id}")
    def delete_product(product_id: int, caller=Depends(edge)):
        require_roles(caller, "admin")
        with db.tx() as c:
            cursor = c.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))
            if cursor.rowcount == 0:
                raise HTTPException(404, "Producto no encontrado")
        return {"deactivated": product_id}

    @app.get("/stock")
    def stock(caller=Depends(edge)):
        require_roles(caller, *STAFF)
        rows = db.all(f"{PRODUCT_SQL} ORDER BY p.id")
        return {"items": [product_view(r, True) for r in rows]}

    @app.post("/stock/{product_id}/adjust")
    def adjust(product_id: int, body: AdjustIn, caller=Depends(edge)):
        require_roles(caller, *STAFF)
        try:
            with db.tx() as c:
                cursor = c.execute(
                    "UPDATE stock SET on_hand = on_hand + ? WHERE product_id = ?", (body.delta, product_id)
                )
                if cursor.rowcount == 0:
                    raise HTTPException(404, "Producto no encontrado")
        except sqlite3.IntegrityError:
            raise HTTPException(409, "El ajuste deja el stock bajo lo reservado o bajo cero")
        return product_view(db.one(f"{PRODUCT_SQL} WHERE p.id = ?", (product_id,)), True)

    PROMO_SQL = (
        "SELECT pr.id, pr.product_id, p.name AS product_name, pr.kind, pr.label, pr.active "
        "FROM promotions pr JOIN products p ON p.id = pr.product_id"
    )

    def promo_view(row):
        return {k: row[k] for k in ("id", "product_id", "product_name", "kind", "label")} | {"active": bool(row["active"])}

    @app.get("/promotions")
    def list_promotions(caller=Depends(edge)):
        admin = caller.user is not None and caller.user.has("admin")
        clause = "" if admin else " WHERE pr.active = 1 AND p.active = 1"
        rows = db.all(f"{PROMO_SQL}{clause} ORDER BY pr.id")
        return {"items": [promo_view(r) for r in rows]}

    @app.patch("/promotions/{promo_id}")
    def patch_promotion(promo_id: int, body: PromotionPatch, caller=Depends(edge)):
        require_roles(caller, "admin")
        with db.tx() as c:
            cursor = c.execute("UPDATE promotions SET active = ? WHERE id = ?", (int(body.active), promo_id))
            if cursor.rowcount == 0:
                raise HTTPException(404, "Promocion no encontrada")
        return promo_view(db.one(f"{PROMO_SQL} WHERE pr.id = ?", (promo_id,)))

    def reservation_lines(rows):
        return [
            {
                "product_id": r["product_id"],
                "unit_price": r["unit_price"],
                "qty": r["qty"],
                "name": r["name"],
                "discount": r["discount"],
                "promo": r["promo"],
            }
            for r in rows
        ]

    def summary(order_id, lines):
        subtotal = sum(l["qty"] * l["unit_price"] for l in lines)
        discount = sum(l["discount"] for l in lines)
        return {"order_id": order_id, "lines": lines, "subtotal": subtotal, "discount": discount, "total": subtotal - discount}

    RES_SQL = (
        "SELECT r.product_id, r.unit_price, r.qty, r.discount, r.promo, r.status, p.name FROM reservations r "
        "JOIN products p ON p.id = r.product_id WHERE r.order_id = ? ORDER BY r.product_id"
    )

    @app.post("/reservations")
    def reserve(body: ReserveIn, caller=Depends(only_orders)):
        wanted = {}
        for line in body.items:
            wanted[line.product_id] = wanted.get(line.product_id, 0) + line.qty
        with db.tx() as c:
            existing = c.execute(RES_SQL, (body.order_id,)).fetchall()
            if existing:
                if any(r["status"] != "reserved" for r in existing):
                    raise HTTPException(409, "La reserva de esta orden ya fue cerrada")
                return summary(body.order_id, reservation_lines(existing))
            lines = []
            for product_id, qty in wanted.items():
                product = c.execute("SELECT id, name, price, active FROM products WHERE id = ?", (product_id,)).fetchone()
                if not product or not product["active"]:
                    raise HTTPException(409, {"message": "Producto no disponible", "product_id": product_id})
                cursor = c.execute(
                    "UPDATE stock SET reserved = reserved + ? WHERE product_id = ? AND on_hand - reserved >= ?",
                    (qty, product_id, qty),
                )
                if cursor.rowcount == 0:
                    raise HTTPException(
                        409, {"message": f"Stock insuficiente para {product['name']}", "product_id": product_id}
                    )
                promo = c.execute(
                    "SELECT kind FROM promotions WHERE product_id = ? AND active = 1", (product_id,)
                ).fetchone()
                kind = promo["kind"] if promo else None
                discount = promo_discount(kind, product["price"], qty)
                c.execute(
                    "INSERT INTO reservations(order_id,product_id,qty,unit_price,discount,promo,status,created_at) "
                    "VALUES(?,?,?,?,?,?,'reserved',?)",
                    (body.order_id, product_id, qty, product["price"], discount, kind, now_iso()),
                )
                lines.append(
                    {
                        "product_id": product_id,
                        "unit_price": product["price"],
                        "qty": qty,
                        "name": product["name"],
                        "discount": discount,
                        "promo": kind,
                    }
                )
        return summary(body.order_id, lines)

    @app.post("/reservations/{order_id}/release")
    def release(order_id: str, caller=Depends(only_orders)):
        released = 0
        with db.tx() as c:
            rows = c.execute(
                "SELECT product_id, qty FROM reservations WHERE order_id = ? AND status = 'reserved'", (order_id,)
            ).fetchall()
            for row in rows:
                c.execute("UPDATE stock SET reserved = reserved - ? WHERE product_id = ?", (row["qty"], row["product_id"]))
                released += 1
            c.execute("UPDATE reservations SET status = 'released' WHERE order_id = ? AND status = 'reserved'", (order_id,))
        return {"order_id": order_id, "released": released}

    @app.post("/reservations/{order_id}/commit")
    def commit(order_id: str, caller=Depends(only_orders)):
        with db.tx() as c:
            rows = c.execute("SELECT product_id, qty, status FROM reservations WHERE order_id = ?", (order_id,)).fetchall()
            if not rows:
                raise HTTPException(404, "Reserva no encontrada")
            if any(r["status"] == "released" for r in rows):
                raise HTTPException(409, "La reserva fue liberada")
            pending = [r for r in rows if r["status"] == "reserved"]
            for row in pending:
                c.execute(
                    "UPDATE stock SET on_hand = on_hand - ?, reserved = reserved - ? WHERE product_id = ?",
                    (row["qty"], row["qty"], row["product_id"]),
                )
            c.execute("UPDATE reservations SET status = 'committed' WHERE order_id = ? AND status = 'reserved'", (order_id,))
        return {"order_id": order_id, "committed": len(pending)}

    return app
