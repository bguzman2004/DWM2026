import threading
import time

import httpx


class VaultError(Exception):
    pass


class VaultClient:
    def __init__(self, addr, token, transport=None, timeout=3.0):
        self._http = httpx.Client(
            base_url=addr.rstrip("/"),
            headers={"X-Vault-Token": token},
            transport=transport,
            timeout=timeout,
        )

    def _call(self, method, url, **kwargs):
        try:
            return self._http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise VaultError("Vault no disponible") from exc

    def read(self, path):
        response = self._call("GET", f"/v1/secret/data/{path}")
        if response.status_code != 200:
            raise VaultError(f"Vault respondio {response.status_code}")
        return response.json()["data"]["data"]

    def write(self, path, data):
        response = self._call("POST", f"/v1/secret/data/{path}", json={"data": data})
        if response.status_code not in (200, 204):
            raise VaultError(f"Vault respondio {response.status_code}")

    def exists(self, path):
        response = self._call("GET", f"/v1/secret/data/{path}")
        if response.status_code == 404:
            return False
        if response.status_code != 200:
            raise VaultError(f"Vault respondio {response.status_code}")
        return True

    def put_policy(self, name, hcl):
        response = self._call("PUT", f"/v1/sys/policies/acl/{name}", json={"policy": hcl})
        if response.status_code not in (200, 204):
            raise VaultError(f"Vault respondio {response.status_code}")

    def create_token(self, policies, ttl="720h"):
        response = self._call(
            "POST",
            "/v1/auth/token/create",
            json={"policies": policies, "no_default_policy": True, "ttl": ttl},
        )
        if response.status_code != 200:
            raise VaultError(f"Vault respondio {response.status_code}")
        return response.json()["auth"]["client_token"]

    def close(self):
        self._http.close()


class SecretProvider:
    def __init__(self, vault, ttl=30.0):
        self.vault = vault
        self.ttl = ttl
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, path):
        now = time.monotonic()
        with self._lock:
            hit = self._cache.get(path)
            if hit and now - hit[0] < self.ttl:
                return hit[1]
        data = self.vault.read(path)
        with self._lock:
            self._cache[path] = (time.monotonic(), data)
        return data

    def invalidate(self):
        with self._lock:
            self._cache.clear()


def make_secrets(cfg, transport=None):
    return SecretProvider(VaultClient(cfg.vault_addr, cfg.vault_token, transport=transport), cfg.secret_ttl)
