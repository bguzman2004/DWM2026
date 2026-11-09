CREATE TABLE IF NOT EXISTS sales_facts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    qty INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    at TEXT NOT NULL,
    UNIQUE(order_id, product_id)
);
CREATE INDEX IF NOT EXISTS idx_facts_at ON sales_facts(at);
CREATE TABLE IF NOT EXISTS sync_state(
    key TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);
