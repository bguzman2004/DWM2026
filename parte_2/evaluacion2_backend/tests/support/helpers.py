import json
import uuid

import httpx

from common.db import Database
from common.security import Identity
from services.payments.main import sign

ADMIN = Identity("USR-004", "benjamin", ("customer", "admin"), "")
KITCHEN = Identity("USR-003", "cocina", ("kitchen",), "")


def items_payload(items):
    return {"items": [{"product_id": p, "qty": q} for p, q in items]}


def place_order(client, items=((1, 1),), key=None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post("/orders", json=items_payload(items), headers=headers)


def start_payment(client, order_id, key=None):
    return client.post("/payments", json={"order_id": order_id}, headers={"Idempotency-Key": key or uuid.uuid4().hex})


def webhook(stack, provider_ref, amount, kind="payment.succeeded", event_id=None, secret=None, mutate=None):
    event = {
        "event_id": event_id or "evt_" + uuid.uuid4().hex[:12],
        "type": kind,
        "provider_ref": provider_ref,
        "amount": amount,
    }
    body = json.dumps(event).encode()
    key = secret or stack.root.read("mariachi/payments")["webhook_hmac"]
    signature = sign(key, body)
    if mutate:
        body = mutate(body)
    return httpx.post(
        f"{stack.urls['api-gateway']}/payments/webhook",
        content=body,
        headers={"content-type": "application/json", "X-Signature": signature},
        timeout=15.0,
    )


def pay(stack, client, order, event_id=None):
    created = start_payment(client, order["id"]).json()
    result = webhook(stack, created["provider_ref"], created["amount"], event_id=event_id)
    return created, result


def db_of(stack, name):
    return Database(str(stack.tmp / f"{name}.db"))


def stock_of(stack, product_id):
    row = db_of(stack, "inventory").one("SELECT on_hand, reserved FROM stock WHERE product_id = ?", (product_id,))
    return row["on_hand"], row["reserved"]


def gql(client, query, variables=None):
    return client.post("/graphql", json={"query": query, "variables": variables or {}})
