import time

import httpx
from fastapi import HTTPException

from common.logs import log, request_id_var
from common.topology import edge_path
from common.vault import VaultError


class UpstreamUnavailable(Exception):
    def __init__(self, callee):
        super().__init__(f"Servicio {callee} no disponible")
        self.callee = callee


class UpstreamTimeout(Exception):
    def __init__(self, callee):
        super().__init__(f"Servicio {callee} no respondio a tiempo")
        self.callee = callee


class SecretsUnavailable(Exception):
    def __init__(self):
        super().__init__("Secretos no disponibles")


class ServiceClient:
    def __init__(self, cfg, secrets, callee, timeout=3.0):
        self.cfg = cfg
        self.secrets = secrets
        self.callee = callee
        self.timeout = timeout
        self.base = cfg.urls[callee].rstrip("/")
        self._client = None

    def _http(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base, timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def request(self, method, path, *, user=None, json=None, params=None, content=None, headers=None):
        try:
            edge = self.secrets.get(edge_path(self.callee, self.cfg.name))
        except VaultError:
            raise SecretsUnavailable()
        sent = {
            "X-Service-Caller": self.cfg.name,
            "X-Service-Token": edge["token"],
            "X-Request-Id": request_id_var.get(),
        }
        if user is not None:
            sent.update(user.headers())
        if headers:
            sent.update(headers)
        attempts = 2 if method == "GET" else 1
        started = time.perf_counter()
        for attempt in range(attempts):
            last = attempt == attempts - 1
            try:
                response = await self._http().request(
                    method, path, json=json, params=params, content=content, headers=sent
                )
                break
            except httpx.TimeoutException:
                if last:
                    log(self.cfg.name, "upstream_timeout", callee=self.callee, path=path)
                    raise UpstreamTimeout(self.callee)
            except httpx.TransportError:
                if last:
                    log(self.cfg.name, "upstream_down", callee=self.callee, path=path)
                    raise UpstreamUnavailable(self.callee)
        log(
            self.cfg.name,
            "upstream_call",
            callee=self.callee,
            method=method,
            path=path,
            status=response.status_code,
            ms=round((time.perf_counter() - started) * 1000, 1),
        )
        call_log = self.cfg.extra.get("call_log")
        if call_log is not None:
            call_log.append((self.callee, method, path))
        return response


def error_message(response, default="Error en servicio dependiente"):
    try:
        body = response.json()
        return body["error"]["message"]
    except Exception:
        return default


def raise_for_upstream(response):
    if response.status_code < 400:
        return
    if response.status_code < 500:
        raise HTTPException(response.status_code, error_message(response))
    status = 503 if response.status_code == 503 else 502
    raise HTTPException(status, "Servicio dependiente con error")
