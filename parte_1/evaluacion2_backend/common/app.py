import re
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.calls import SecretsUnavailable, UpstreamTimeout, UpstreamUnavailable
from common.logs import log, request_id_var, setup_logging
from common.topology import probe_path
from common.vault import VaultError

RID = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


def error_body(status, message, request_id, extra=None):
    body = {"status": status, "message": message, "request_id": request_id}
    if extra:
        body.update(extra)
    return {"error": body}


def create_service_app(cfg, secrets, db=None, docs=True, trust_request_id=True, secrets_status=503):
    setup_logging()
    closers = []

    @asynccontextmanager
    async def lifespan(_app):
        yield
        for closer in closers:
            await closer()

    app = FastAPI(
        lifespan=lifespan,
        title=f"El Mariachi - {cfg.name}",
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.state.cfg = cfg
    app.state.secrets = secrets
    app.state.db = db
    app.state.closers = closers

    def respond(status, message, extra=None):
        return JSONResponse(error_body(status, message, request_id_var.get(), extra), status_code=status)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "") if trust_request_id else ""
        rid = incoming if RID.match(incoming) else uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                log(cfg.name, "unhandled_error", level=40, error=type(exc).__name__)
                response = respond(500, "Error interno")
            response.headers["X-Request-Id"] = rid
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            user = request.headers.get("x-user-id", "-")
            log(
                cfg.name,
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=round((time.perf_counter() - started) * 1000, 1),
                user=user,
                caller=request.headers.get("x-service-caller", "-"),
            )
            return response
        finally:
            request_id_var.reset(token)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        detail = exc.detail
        if isinstance(detail, dict):
            extra = {k: v for k, v in detail.items() if k != "message"}
            return respond(exc.status_code, detail.get("message", "Error"), extra)
        return respond(exc.status_code, str(detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        details = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return respond(422, "Datos invalidos", {"details": details})

    @app.exception_handler(UpstreamUnavailable)
    async def upstream_down(request, exc):
        return respond(503, str(exc))

    @app.exception_handler(UpstreamTimeout)
    async def upstream_timeout(request, exc):
        return respond(504, str(exc))

    @app.exception_handler(SecretsUnavailable)
    async def secrets_down(request, exc):
        return respond(secrets_status, "Secretos no disponibles")

    @app.exception_handler(VaultError)
    async def vault_down(request, exc):
        return respond(secrets_status, "Secretos no disponibles")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": cfg.name}

    @app.get("/ready")
    def ready():
        checks = {}
        if db is not None:
            try:
                db.ping()
                checks["database"] = "ok"
            except Exception:
                checks["database"] = "fail"
        try:
            secrets.vault.read(probe_path(cfg.name))
            checks["vault"] = "ok"
        except VaultError:
            checks["vault"] = "fail"
        ok = all(v == "ok" for v in checks.values())
        return JSONResponse({"status": "ready" if ok else "not_ready", "checks": checks}, status_code=200 if ok else 503)

    return app
