import threading
import time
from concurrent import futures
from datetime import datetime, timedelta, timezone
from pathlib import Path

import grpc
import httpx

from common.config import Settings
from common.db import Database
from common.logs import log, request_id_var, setup_logging
from common.security import verify_edge
from common.topology import edge_path
from common.vault import VaultError, make_secrets
from services.analytics import analytics_pb2 as pb
from services.analytics import analytics_pb2_grpc as rpc

SCHEMA = Path(__file__).with_name("schema.sql")
ALLOWED_CALLERS = {"graphql-gateway"}
PUBLIC_METHODS = {"/mariachi.analytics.v1.Analytics/Health"}


class AuthInterceptor(grpc.ServerInterceptor):
    def __init__(self, cfg, secrets):
        self.cfg = cfg
        self.secrets = secrets

    def intercept_service(self, continuation, handler_call_details):
        handler = continuation(handler_call_details)
        if handler_call_details.method in PUBLIC_METHODS or handler is None:
            return handler
        meta = dict(handler_call_details.invocation_metadata)
        caller = meta.get("x-service-caller", "")
        token = meta.get("x-service-token", "")
        roles = meta.get("x-user-roles", "").split(",")
        denied = None
        if caller not in ALLOWED_CALLERS or not token:
            denied = (grpc.StatusCode.PERMISSION_DENIED, "Llamador no autorizado")
        else:
            try:
                if not verify_edge(self.secrets, self.cfg.name, caller, token):
                    denied = (grpc.StatusCode.PERMISSION_DENIED, "Llamador no autorizado")
            except Exception:
                denied = (grpc.StatusCode.UNAVAILABLE, "Secretos no disponibles")
        if denied is None and "admin" not in roles:
            denied = (grpc.StatusCode.PERMISSION_DENIED, "Se requiere rol admin")
        if denied is None:
            return handler
        code, message = denied

        def abort(request, context):
            log(self.cfg.name, "grpc_denied", method=handler_call_details.method, reason=message)
            context.abort(code, message)

        if handler.unary_stream:
            return grpc.unary_stream_rpc_method_handler(abort)
        return grpc.unary_unary_rpc_method_handler(abort)


class AnalyticsService(rpc.AnalyticsServicer):
    def __init__(self, cfg, secrets, db):
        self.cfg = cfg
        self.secrets = secrets
        self.db = db

    def Health(self, request, context):
        return pb.HealthReply(status="ok")

    def Sync(self, request, context):
        try:
            edge = self.secrets.get(edge_path("orders", self.cfg.name))
        except VaultError:
            context.abort(grpc.StatusCode.UNAVAILABLE, "Secretos no disponibles")
        headers = {"X-Service-Caller": self.cfg.name, "X-Service-Token": edge["token"], "X-Request-Id": request_id_var.get()}
        imported = 0
        cursor = self.db.one("SELECT value FROM sync_state WHERE key='after'")
        after = cursor["value"] if cursor else 0
        try:
            with httpx.Client(base_url=self.cfg.urls["orders"], timeout=5.0, headers=headers) as http:
                while True:
                    response = http.get("/internal/orders/export", params={"after": after, "limit": 500})
                    if response.status_code != 200:
                        context.abort(grpc.StatusCode.UNAVAILABLE, "Ordenes no disponible")
                    body = response.json()
                    if not body["facts"] and body["next_after"] == after:
                        break
                    with self.db.tx() as c:
                        for fact in body["facts"]:
                            c.execute(
                                "INSERT OR IGNORE INTO sales_facts(order_id,product_id,name,qty,amount,at) VALUES(?,?,?,?,?,?)",
                                (fact["order_id"], fact["product_id"], fact["name"], fact["qty"], fact["amount"], fact["at"]),
                            )
                            imported += c.execute("SELECT changes() AS n").fetchone()["n"]
                        c.execute(
                            "INSERT INTO sync_state(key,value) VALUES('after',?) "
                            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (body["next_after"],),
                        )
                    after = body["next_after"]
        except httpx.HTTPError:
            context.abort(grpc.StatusCode.UNAVAILABLE, "Ordenes no disponible")
        log(self.cfg.name, "sync_done", imported=imported)
        return pb.SyncReply(imported=imported)

    def SalesSummary(self, request, context):
        days = request.days if 0 < request.days <= 365 else 7
        top = request.top if 0 < request.top <= 50 else 5
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="microseconds")
        totals = self.db.one(
            "SELECT COUNT(DISTINCT order_id) AS orders, COALESCE(SUM(amount),0) AS revenue FROM sales_facts WHERE at >= ?",
            (since,),
        )
        rows = self.db.all(
            "SELECT product_id, name, SUM(qty) AS units, SUM(amount) AS revenue FROM sales_facts WHERE at >= ? "
            "GROUP BY product_id, name ORDER BY revenue DESC, product_id LIMIT ?",
            (since, top),
        )
        return pb.SummaryReply(
            orders=totals["orders"],
            revenue=totals["revenue"],
            top_products=[
                pb.ProductTotal(product_id=r["product_id"], name=r["name"], units=r["units"], revenue=r["revenue"])
                for r in rows
            ],
        )

    def StreamSales(self, request, context):
        after = request.after_id
        limit = request.limit if 0 < request.limit <= 1_000_000 else 100_000
        sent = 0
        while sent < limit and context.is_active():
            batch = self.db.all(
                "SELECT id, order_id, product_id, qty, amount, at FROM sales_facts WHERE id > ? ORDER BY id LIMIT ?",
                (after, min(2000, limit - sent)),
            )
            if not batch:
                return
            yield pb.SalesBatch(facts=[pb.SaleFact(**row) for row in batch], last_id=batch[-1]["id"])
            after = batch[-1]["id"]
            sent += len(batch)


class AnalyticsServer:
    def __init__(self, cfg, host="0.0.0.0"):
        setup_logging()
        self.cfg = cfg
        self.host = host
        self.secrets = make_secrets(cfg)
        self.db = Database(cfg.db_path)
        self.db.init(SCHEMA)
        self.server = None
        self.port = None
        self._stop = threading.Event()

    def start(self, port=0):
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=16),
            interceptors=[AuthInterceptor(self.cfg, self.secrets)],
        )
        rpc.add_AnalyticsServicer_to_server(AnalyticsService(self.cfg, self.secrets, self.db), self.server)
        self.port = self.server.add_insecure_port(f"{self.host}:{port}")
        self.server.start()
        interval = self.cfg.extra.get("sync_interval", 0)
        if interval:
            threading.Thread(target=self._loop, args=(interval,), daemon=True).start()
        log(self.cfg.name, "grpc_started", port=self.port)
        return self.port

    def _loop(self, interval):
        while not self._stop.wait(interval):
            try:
                AnalyticsService(self.cfg, self.secrets, self.db).Sync(pb.Empty(), _LoopContext())
            except Exception:
                log(self.cfg.name, "sync_failed", level=40)

    def stop(self):
        self._stop.set()
        if self.server:
            self.server.stop(0).wait()

    def wait(self):
        self.server.wait_for_termination()


class _LoopContext:
    def abort(self, code, message):
        raise RuntimeError(message)


def main():
    cfg = Settings.from_env("analytics")
    server = AnalyticsServer(cfg)
    server.start(cfg.extra["grpc_port"])
    server.wait()


if __name__ == "__main__":
    main()
