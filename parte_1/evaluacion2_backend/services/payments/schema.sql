CREATE TABLE IF NOT EXISTS payments(
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK(amount > 0),
    status TEXT NOT NULL CHECK(status IN ('pending','succeeded','failed','requires_refund')),
    provider_ref TEXT NOT NULL UNIQUE,
    idempotency_key TEXT NOT NULL,
    order_synced INTEGER NOT NULL DEFAULT 0 CHECK(order_synced IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(client_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE TABLE IF NOT EXISTS webhook_events(
    event_id TEXT PRIMARY KEY,
    payment_id TEXT NOT NULL REFERENCES payments(id),
    type TEXT NOT NULL,
    received_at TEXT NOT NULL
);
