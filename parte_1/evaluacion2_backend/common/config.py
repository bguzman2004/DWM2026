import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    name: str
    vault_addr: str = "http://127.0.0.1:8200"
    vault_token: str = ""
    db_path: str = ""
    urls: dict = field(default_factory=dict)
    secret_ttl: float = 30.0
    seed: bool = False
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls, name):
        token = os.getenv("VAULT_TOKEN", "")
        token_file = os.getenv("VAULT_TOKEN_FILE")
        if token_file and os.path.exists(token_file):
            with open(token_file) as handle:
                token = handle.read().strip()
        urls = {
            key[4:].lower().replace("_", "-"): value
            for key, value in os.environ.items()
            if key.startswith("URL_")
        }
        return cls(
            name=name,
            vault_addr=os.getenv("VAULT_ADDR", "http://127.0.0.1:8200"),
            vault_token=token,
            db_path=os.getenv("DB_PATH", f"./data/{name}.db"),
            urls=urls,
            secret_ttl=float(os.getenv("SECRET_TTL", "30")),
            seed=os.getenv("SEED", "0") == "1",
            extra={
                "demo_password": os.getenv("DEMO_PASSWORD", ""),
                "cookie_secure": os.getenv("COOKIE_SECURE", "1") == "1",
                "introspection": os.getenv("GRAPHQL_INTROSPECTION", "0") == "1",
                "analytics_addr": os.getenv("ANALYTICS_ADDR", ""),
                "sync_interval": float(os.getenv("ANALYTICS_SYNC_INTERVAL", "0")),
                "grpc_port": int(os.getenv("GRPC_PORT", "50051")),
            },
        )
