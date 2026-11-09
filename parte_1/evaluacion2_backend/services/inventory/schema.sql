CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL CHECK(category IN ('Tacos','Burritos','Nachos','Bebidas','Otros')),
    price INTEGER NOT NULL CHECK(price > 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
CREATE TABLE IF NOT EXISTS stock(
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    on_hand INTEGER NOT NULL CHECK(on_hand >= 0),
    reserved INTEGER NOT NULL DEFAULT 0 CHECK(reserved >= 0),
    CHECK(reserved <= on_hand)
);
CREATE TABLE IF NOT EXISTS reservations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty INTEGER NOT NULL CHECK(qty > 0),
    unit_price INTEGER NOT NULL,
    discount INTEGER NOT NULL DEFAULT 0 CHECK(discount >= 0),
    promo TEXT,
    status TEXT NOT NULL CHECK(status IN ('reserved','committed','released')),
    created_at TEXT NOT NULL,
    UNIQUE(order_id, product_id)
);
CREATE INDEX IF NOT EXISTS idx_reservations_order ON reservations(order_id);

CREATE TABLE IF NOT EXISTS promotions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL UNIQUE REFERENCES products(id),
    kind TEXT NOT NULL CHECK(kind IN ('2x1')),
    label TEXT NOT NULL CHECK(length(label) BETWEEN 3 AND 120),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
