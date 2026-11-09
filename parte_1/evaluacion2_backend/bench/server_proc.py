from pathlib import Path

from bench.rest_baseline import create_rest_baseline
from common.config import Settings
from common.vault import VaultClient
from scripts.vault_bootstrap import bootstrap
from services.analytics.server import AnalyticsServer
from tests.support.stack import ROOT_TOKEN, Running
from tools.dev_vault import create_dev_vault


def serve(tmp, vault_port, grpc_port, rest_port, rows, pipe):
    from bench.load_test import seed_facts

    tmp = Path(tmp)
    vault = Running(create_dev_vault(ROOT_TOKEN), vault_port)
    vault.start()
    root = VaultClient(f"http://127.0.0.1:{vault_port}", ROOT_TOKEN)
    tokens = bootstrap(root)
    cfg = Settings(
        name="analytics",
        vault_addr=f"http://127.0.0.1:{vault_port}",
        vault_token=tokens["analytics"],
        db_path=str(tmp / "analytics.db"),
        urls={},
        secret_ttl=30.0,
    )
    server = AnalyticsServer(cfg, host="127.0.0.1")
    seed_facts(cfg.db_path, rows)
    server.start(grpc_port)
    rest = Running(create_rest_baseline(cfg.db_path), rest_port)
    rest.start()
    pipe.send(root.read("mariachi/edges/analytics/graphql-gateway")["token"])
    pipe.recv()
    rest.stop()
    server.stop()
    vault.stop()
