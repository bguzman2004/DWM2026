import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator

from common.app import create_service_app, error_body
from common.calls import ServiceClient, SecretsUnavailable, UpstreamTimeout, UpstreamUnavailable
from common.config import Settings
from common.logs import log, request_id_var
from common.security import Identity
from common.validators import clean_email, clean_name, clean_phone
from common.vault import make_secrets
from services.api_gateway.routes import match

COOKIE = "session_token"
MAX_BODY = 64 * 1024
UPSTREAMS = ("auth", "inventory", "clients", "orders", "payments", "graphql-gateway")
FORWARDED_REQUEST_HEADERS = ("content-type", "idempotency-key", "x-signature", "accept")
LIMITS = {"login": (10, 60), "register": (5, 60), "webhook": (120, 60), "graphql": (120, 60), "default": (300, 60)}


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(max_length=80)
    email: str = Field(max_length=120)
    phone: str | None = Field(None, max_length=20)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        return clean_name(value)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        return clean_email(value)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value):
        return clean_phone(value)


class RateLimiter:
    def __init__(self, limits):
        self.limits = limits
        self.hits = defaultdict(deque)

    def allow(self, bucket, key):
        limit, window = self.limits[bucket]
        now = time.monotonic()
        queue = self.hits[(bucket, key)]
        while queue and now - queue[0] > window:
            queue.popleft()
        if len(queue) >= limit:
            return False
        queue.append(now)
        return True


def create_app(cfg=None):
    cfg = cfg or Settings.from_env("api-gateway")
    secrets = make_secrets(cfg)
    app = create_service_app(cfg, secrets, None, docs=False, trust_request_id=False, secrets_status=500)
    clients = {name: ServiceClient(cfg, secrets, name) for name in UPSTREAMS}
    app.state.closers.extend(c.close for c in clients.values())
    limits = dict(LIMITS)
    limits.update(cfg.extra.get("limits", {}))
    limiter = RateLimiter(limits)
    secure_cookie = cfg.extra.get("cookie_secure", True)

    def fail(status, message):
        return JSONResponse(error_body(status, message, request_id_var.get()), status_code=status)

    def client_ip(request):
        return request.client.host if request.client else "-"

    async def authenticate(request):
        token = request.cookies.get(COOKIE)
        if not token:
            raise HTTPException(401, "Sesion requerida")
        response = await clients["auth"].request("POST", "/introspect", json={"token": token})
        if response.status_code != 200:
            raise UpstreamUnavailable("auth")
        data = response.json()
        if not data.get("active"):
            raise HTTPException(401, "Sesion invalida o expirada")
        return Identity(data["user_id"], data["username"], tuple(data["roles"]), data.get("client_id") or "")

    @app.exception_handler(UpstreamUnavailable)
    async def upstream_down(request, exc):
        status = 503 if exc.callee == "auth" else 502
        return fail(status, f"Servicio {exc.callee} no disponible")

    @app.exception_handler(UpstreamTimeout)
    async def upstream_timeout(request, exc):
        return fail(504, f"Servicio {exc.callee} no respondio a tiempo")

    @app.post("/auth/login")
    async def login(body: LoginIn, request: Request):
        if not limiter.allow("login", client_ip(request)):
            raise HTTPException(429, "Demasiados intentos, reintente mas tarde")
        response = await clients["auth"].request("POST", "/login", json=body.model_dump())
        if response.status_code != 200:
            status = response.status_code if response.status_code in (401, 429) else 503
            message = "Credenciales incorrectas" if status == 401 else "Servicio de autenticacion no disponible"
            if status == 429:
                message = "Demasiados intentos, reintente mas tarde"
            return fail(status, message)
        data = response.json()
        result = JSONResponse({"user": data["user"], "expires_in": data["expires_in"]})
        result.set_cookie(
            COOKIE, data["token"], httponly=True, samesite="lax", secure=secure_cookie,
            max_age=data["expires_in"], path="/",
        )
        return result

    @app.post("/auth/register")
    async def register(body: RegisterIn, request: Request):
        if not limiter.allow("register", client_ip(request)):
            raise HTTPException(429, "Demasiados intentos, reintente mas tarde")
        response = await clients["auth"].request("POST", "/register", json=body.model_dump())
        if response.status_code in (201, 409, 422):
            return Response(content=response.content, status_code=response.status_code, media_type="application/json")
        raise UpstreamUnavailable("auth")

    @app.get("/auth/me")
    async def me(request: Request):
        user = await authenticate(request)
        return {"user_id": user.user_id, "username": user.username, "roles": list(user.roles), "client_id": user.client_id or None}

    @app.post("/auth/logout")
    async def logout(request: Request):
        token = request.cookies.get(COOKIE)
        revoked = None
        error = None
        if token:
            try:
                response = await clients["auth"].request("POST", "/logout", json={"token": token})
                revoked = response.status_code == 200
            except UpstreamUnavailable:
                error = True
        result = JSONResponse({"revoked": bool(revoked)} if not error else error_body(503, "No se pudo revocar la sesion", request_id_var.get()), status_code=503 if error else 200)
        result.delete_cookie(COOKIE, path="/")
        return result

    @app.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def proxy(path: str, request: Request):
        route, params, path_exists = match(request.method, "/" + path)
        if route is None:
            return fail(405 if path_exists else 404, "Metodo no permitido" if path_exists else "Ruta no encontrada")
        if not limiter.allow(route.limit, client_ip(request)):
            return fail(429, "Demasiadas solicitudes")
        user = None
        if route.access == "optional" and request.cookies.get(COOKIE):
            try:
                user = await authenticate(request)
            except HTTPException:
                user = None
        if route.access == "session":
            user = await authenticate(request)
            if route.roles and not user.has(*route.roles):
                log(cfg.name, "forbidden", user=user.username, path=request.url.path)
                return fail(403, "Sin permisos para esta operacion")
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_BODY:
            return fail(413, "Cuerpo demasiado grande")
        body = await request.body()
        if len(body) > MAX_BODY:
            return fail(413, "Cuerpo demasiado grande")
        if body and "application/json" not in request.headers.get("content-type", ""):
            return fail(415, "Se requiere application/json")
        headers = {k: v for k, v in ((h, request.headers.get(h)) for h in FORWARDED_REQUEST_HEADERS) if v}
        upstream_path = route.path.format(**params)
        upstream = await clients[route.upstream].request(
            request.method, upstream_path, user=user, content=body or None,
            params=list(request.query_params.multi_items()), headers=headers,
        )
        if upstream.status_code >= 500:
            status = 503 if upstream.status_code == 503 else 502
            return fail(status, "Servicio dependiente con error")
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type"),
        )

    return app
