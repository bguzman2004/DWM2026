import json
import logging
import secrets as pysecrets
import socket
import threading
import time

import httpx
import uvicorn

from common.config import Settings
from common.topology import SERVICES
from common.vault import VaultClient
from scripts.vault_bootstrap import bootstrap
from services.analytics.server import AnalyticsServer
from tools.dev_vault import create_dev_vault

ROOT_TOKEN = "root-" + pysecrets.token_urlsafe(16)
DEMO_PASSWORD = pysecrets.token_urlsafe(12)

FACTORIES = {
    "auth": "services.auth.main",
    "inventory": "services.inventory.main",
    "clients": "services.clients.main",
    "orders": "services.orders.main",
    "payments": "services.payments.main",
    "graphql-gateway": "services.graphql_gateway.main",
    "api-gateway": "services.api_gateway.main",
}


_used_ports = set()


def free_port():
    while True:
        port = pysecrets.randbelow(10000) + 20000
        if port in _used_ports:
            continue
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
        _used_ports.add(port)
        return port


class LogCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        from common.logs import JsonFormatter

        self.setFormatter(JsonFormatter())
        self.lines = []

    def emit(self, record):
        self.lines.append(self.format(record))

    def events(self):
        return [json.loads(line) for line in self.lines]


class Running:
    def __init__(self, app, port):
        self.app = app
        self.port = port
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", lifespan="on"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self):
        self.thread.start()
        deadline = time.time() + 15
        while not self.server.started:
            if time.time() > deadline:
                raise RuntimeError("servicio no inicio")
            time.sleep(0.02)

    def stop(self):
        self.server.should_exit = True
        self.thread.join(timeout=10)


class Stack:
    def __init__(self, tmp_path, extra=None, ttl=0.0):
        self.tmp = tmp_path
        self.ttl = ttl
        self.extra = extra or {}
        self.ports = {name: free_port() for name in SERVICES}
        self.urls = {name: f"http://127.0.0.1:{port}" for name, port in self.ports.items() if name != "analytics"}
        self.urls["analytics"] = f"http://127.0.0.1:{self.ports['analytics']}"
        self.vault_port = free_port()
        self.vault_url = f"http://127.0.0.1:{self.vault_port}"
        self.running = {}
        self.tokens = {}
        self.capture = LogCapture()
        self.call_log = []
        self.analytics = None

    def settings(self, name):
        extra = {
            "demo_password": DEMO_PASSWORD,
            "cookie_secure": False,
            "introspection": False,
            "analytics_addr": f"127.0.0.1:{self.ports['analytics']}",
            "sync_interval": 0,
            "call_log": self.call_log,
        }
        if name == "api-gateway":
            extra["limits"] = {"login": (10000, 60)}
        extra.update(self.extra.get(name, {}))
        return Settings(
            name=name,
            vault_addr=self.vault_url,
            vault_token=self.tokens[name],
            db_path=str(self.tmp / f"{name}.db"),
            urls={k: v for k, v in self.urls.items() if k != name},
            secret_ttl=self.ttl,
            seed=True,
            extra=extra,
        )

    def start(self):
        logging.getLogger("mariachi").addHandler(self.capture)
        self.vault_app = create_dev_vault(ROOT_TOKEN)
        self.vault = Running(self.vault_app, self.vault_port)
        self.vault.start()
        self.root = VaultClient(self.vault_url, ROOT_TOKEN)
        self.tokens = bootstrap(self.root)
        for name in FACTORIES:
            self.start_service(name)
        self.start_analytics()
        return self

    def start_service(self, name):
        module = __import__(FACTORIES[name], fromlist=["create_app"])
        app = module.create_app(self.settings(name))
        running = Running(app, self.ports[name])
        running.start()
        self.running[name] = running

    def stop_service(self, name):
        self.running.pop(name).stop()

    def start_analytics(self):
        cfg = self.settings("analytics")
        self.analytics = AnalyticsServer(cfg, host="127.0.0.1")
        self.analytics.start(self.ports["analytics"])

    def stop_analytics(self):
        if self.analytics:
            self.analytics.stop()
            self.analytics = None

    def stop(self):
        for name in list(self.running):
            self.stop_service(name)
        self.stop_analytics()
        self.vault.stop()
        self.root.close()
        logging.getLogger("mariachi").removeHandler(self.capture)

    def client(self, username=None, password=DEMO_PASSWORD):
        http = httpx.Client(base_url=self.urls["api-gateway"], timeout=15.0)
        if username:
            response = http.post("/auth/login", json={"username": username, "password": password})
            assert response.status_code == 200, response.text
        return http

    def internal(self, caller, callee, user=None):
        token = self.root.read(f"mariachi/edges/{callee}/{caller}")["token"]
        headers = {"X-Service-Caller": caller, "X-Service-Token": token}
        if user:
            headers.update(user.headers())
        return httpx.Client(base_url=self.urls[callee], headers=headers, timeout=15.0)
