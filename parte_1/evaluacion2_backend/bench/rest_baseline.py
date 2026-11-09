from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Query

from common.db import Database


def create_rest_baseline(db_path):
    db = Database(db_path)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/sales")
    def sales(after_id: int = 0, limit: int = Query(2000, ge=1, le=5000)):
        rows = db.all(
            "SELECT id, order_id, product_id, qty, amount, at FROM sales_facts WHERE id > ? ORDER BY id LIMIT ?",
            (after_id, limit),
        )
        return {"items": rows}

    @app.get("/summary")
    def summary(days: int = 7, top: int = 5):
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="microseconds")
        totals = db.one(
            "SELECT COUNT(DISTINCT order_id) AS orders, COALESCE(SUM(amount),0) AS revenue FROM sales_facts WHERE at >= ?",
            (since,),
        )
        rows = db.all(
            "SELECT product_id, name, SUM(qty) AS units, SUM(amount) AS revenue FROM sales_facts WHERE at >= ? "
            "GROUP BY product_id, name ORDER BY revenue DESC, product_id LIMIT ?",
            (since, top),
        )
        return {**totals, "top_products": rows}

    return app
