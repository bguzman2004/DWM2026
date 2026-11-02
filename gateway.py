import os

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

app = FastAPI(
    title="El Mariachi - API Gateway",
    description="Valida sesión, autoriza, propaga identidad y enruta al backend"
)

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:8100")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:9000")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

if not VAULT_TOKEN:
    raise RuntimeError("VAULT_TOKEN no esta configurado")

COOKIE_NAME = "session_token"
RECURSOS = {"platillos", "categorias", "pedidos"}
METODOS_ESCRITURA = {"POST", "PUT", "PATCH", "DELETE"}


class LoginRequest(BaseModel):
    username: str
    password: str


def new_client(timeout: float = 5.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout)


async def get_gateway_secrets():
    try:
        async with new_client() as client:
            response = await client.get(
                f"{VAULT_ADDR}/v1/secret/data/gateway",
                headers={"X-Vault-Token": VAULT_TOKEN}
            )
        if response.status_code != 200:
            raise ValueError("respuesta inesperada de Vault")
        data = response.json()["data"]["data"]
        return {
            "backend_shared_secret": data["backend_shared_secret"],
            "auth_introspection_secret": data["auth_introspection_secret"]
        }
    except (httpx.RequestError, ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=500,
            detail="No fue posible acceder al gestor de secretos"
        )


async def call_auth(path: str, payload: dict, headers: dict | None = None):
    try:
        async with new_client() as client:
            return await client.post(
                f"{AUTH_SERVICE_URL}{path}",
                json=payload,
                headers=headers
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Servicio de autenticación no disponible"
        )


async def introspect(token: str, introspection_secret: str):
    response = await call_auth(
        "/introspect",
        {"token": token},
        {"X-Gateway-Auth-Secret": introspection_secret}
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=503,
            detail="Servicio de autenticación no disponible"
        )
    identity = response.json()
    if not identity.get("active", False):
        return None
    return identity


async def authenticate(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Sesión requerida"
        )
    gateway_secrets = await get_gateway_secrets()
    identity = await introspect(
        token,
        gateway_secrets["auth_introspection_secret"]
    )
    if identity is None:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o expirada"
        )
    return {
        "user_id": identity["user_id"],
        "username": identity["username"],
        "roles": identity["roles"],
        "backend_secret": gateway_secrets["backend_shared_secret"]
    }


@app.get("/health")
def health():
    return {
        "status": "OK",
        "service": "El Mariachi - API Gateway"
    }


@app.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    auth_response = await call_auth(
        "/login",
        {"username": body.username, "password": body.password}
    )
    if auth_response.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas"
        )
    if auth_response.status_code != 200:
        raise HTTPException(
            status_code=503,
            detail="Servicio de autenticación no disponible"
        )
    session = auth_response.json()
    gateway_secrets = await get_gateway_secrets()
    identity = await introspect(
        session["access_token"],
        gateway_secrets["auth_introspection_secret"]
    )
    if identity is None:
        raise HTTPException(
            status_code=503,
            detail="Servicio de autenticación no disponible"
        )
    response.set_cookie(
        key=COOKIE_NAME,
        value=session["access_token"],
        max_age=session["expires_in"],
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/"
    )
    return {
        "message": "Sesión iniciada",
        "username": identity["username"],
        "roles": identity["roles"],
        "expires_in": session["expires_in"]
    }


@app.get("/auth/me")
async def me(auth=Depends(authenticate)):
    return {
        "user_id": auth["user_id"],
        "username": auth["username"],
        "roles": auth["roles"]
    }


@app.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        gateway_secrets = await get_gateway_secrets()
        auth_response = await call_auth(
            "/logout",
            {"token": token},
            {"X-Gateway-Auth-Secret": gateway_secrets["auth_introspection_secret"]}
        )
        if auth_response.status_code != 200:
            raise HTTPException(
                status_code=503,
                detail="Servicio de autenticación no disponible"
            )
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Sesión finalizada"}


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def proxy(
    path: str,
    request: Request,
    auth=Depends(authenticate)
):
    segmentos = path.split("/")
    if "." in segmentos or ".." in segmentos:
        raise HTTPException(
            status_code=400,
            detail="Ruta inválida"
        )
    if request.method in METODOS_ESCRITURA and "admin" not in auth["roles"]:
        raise HTTPException(
            status_code=403,
            detail="No tiene permisos para esta operación"
        )
    if segmentos[0] not in RECURSOS:
        raise HTTPException(
            status_code=404,
            detail="Recurso no reconocido por el Gateway"
        )

    body = await request.body()
    gateway_headers = {
        "X-Gateway-Secret": auth["backend_secret"],
        "X-Authenticated-User": auth["user_id"],
        "X-Authenticated-Username": auth["username"],
        "X-Authenticated-Roles": ",".join(auth["roles"])
    }
    content_type = request.headers.get("content-type")
    if content_type:
        gateway_headers["content-type"] = content_type

    try:
        async with new_client(timeout=10.0) as client:
            upstream = await client.request(
                method=request.method,
                url=f"{BACKEND_URL}/{path}",
                params=request.query_params,
                content=body,
                headers=gateway_headers
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Backend no disponible"
        )

    response_headers = {}
    if "content-type" in upstream.headers:
        response_headers["content-type"] = upstream.headers["content-type"]

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers
    )
