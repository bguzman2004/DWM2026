import hmac
from dataclasses import dataclass

from fastapi import HTTPException, Request

from common.topology import edge_path
from common.vault import VaultError


@dataclass(frozen=True)
class Identity:
    user_id: str
    username: str
    roles: tuple
    client_id: str = ""

    def has(self, *roles):
        return any(role in self.roles for role in roles)

    def headers(self):
        return {
            "X-User-Id": self.user_id,
            "X-Username": self.username,
            "X-Roles": ",".join(self.roles),
            "X-Client-Id": self.client_id or "",
        }


@dataclass(frozen=True)
class Caller:
    name: str
    user: Identity | None


def identity_from_headers(headers):
    user_id = headers.get("x-user-id")
    if not user_id:
        return None
    roles = tuple(r for r in headers.get("x-roles", "").split(",") if r)
    return Identity(user_id, headers.get("x-username", ""), roles, headers.get("x-client-id", ""))


def tokens_match(received, candidates):
    ok = False
    for candidate in candidates:
        if candidate and hmac.compare_digest(candidate.encode(), received.encode()):
            ok = True
    return ok


def verify_edge(secrets, service, caller, token):
    try:
        data = secrets.get(edge_path(service, caller))
    except VaultError:
        raise HTTPException(503, "Secretos no disponibles")
    return tokens_match(token, [data.get("token"), data.get("previous")])


def make_guard(cfg, secrets):
    def guard(*callers):
        allowed = set(callers)

        def dependency(request: Request) -> Caller:
            caller = request.headers.get("x-service-caller", "")
            token = request.headers.get("x-service-token", "")
            if caller not in allowed or not token:
                raise HTTPException(403, "Llamador no autorizado")
            if not verify_edge(secrets, cfg.name, caller, token):
                raise HTTPException(403, "Llamador no autorizado")
            return Caller(caller, identity_from_headers(request.headers))

        return dependency

    return guard


def require_user(caller):
    if caller.user is None:
        raise HTTPException(401, "Identidad requerida")
    return caller.user


def require_roles(caller, *roles):
    user = require_user(caller)
    if not user.has(*roles):
        raise HTTPException(403, "Sin permisos para esta operacion")
    return user
