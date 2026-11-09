CREATE TABLE IF NOT EXISTS orders(
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pendiente_pago','pagado','preparando','listo','entregado','cancelado','expirado')),
    subtotal INTEGER NOT NULL CHECK(subtotal > 0),
    discount INTEGER NOT NULL DEFAULT 0 CHECK(discount >= 0),
    total INTEGER NOT NULL CHECK(total > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    stock_released INTEGER NOT NULL DEFAULT 0 CHECK(stock_released IN (0,1)),
    notes TEXT CHECK(notes IS NULL OR length(notes) <= 200),
    CHECK(total = subtotal - discount)
);
CREATE INDEX IF NOT EXISTS idx_orders_client ON orders(client_id, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status, created_at);
CREATE TABLE IF NOT EXISTS order_items(
    order_id TEXT NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    unit_price INTEGER NOT NULL CHECK(unit_price > 0),
    qty INTEGER NOT NULL CHECK(qty > 0),
    discount INTEGER NOT NULL DEFAULT 0 CHECK(discount >= 0 AND discount < unit_price * qty),
    promo TEXT,
    PRIMARY KEY(order_id, product_id)
);
CREATE TABLE IF NOT EXISTS order_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES orders(id),
    event TEXT NOT NULL,
    at TEXT NOT NULL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_kind ON order_events(event, id);
CREATE TABLE IF NOT EXISTS idempotency(
    client_id TEXT NOT NULL,
    key TEXT NOT NULL,
    order_id TEXT NOT NULL REFERENCES orders(id),
    PRIMARY KEY(client_id, key)
);
